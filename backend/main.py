"""
FastAPI backend for Oregon Soccer Referee Concierge.
"""

import json
import os
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Literal
from pydantic import BaseModel
from pathlib import Path
# genai/langchain/FAISS imported lazily in handlers for fast startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load license reference. Vector store is loaded lazily on first use. Shutdown: nothing."""
    from backend.license_service import load_license_reference
    load_license_reference()
    yield


app = FastAPI(
    title="Oregon Soccer Referee Concierge",
    description="AI-powered concierge for Oregon soccer referees",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for frontend (development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000"],  # 8000 = UI host port in docker
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory (for production Docker deployment)
STATIC_DIR = Path(__file__).parent.parent / "static"

# Configuration
VECTOR_STORE_PATH = Path(__file__).parent.parent / "vector_store"

# Global vector store instance and scope graph
vector_store = None
_scope_graph: dict | None = None


class Query(BaseModel):
    """Request model for chat queries."""
    question: str


class Response(BaseModel):
    """Response model for chat answers."""
    answer: str
    sources: list[str] = []
    log_id: str | None = None


class GradeSubmit(BaseModel):
    """Request model for chat response grading."""
    log_id: str
    grade: Literal["up", "down"]


class FeedbackSubmit(BaseModel):
    """Request model for feedback submission."""
    name: str | None = None
    description: str


def load_vector_store():
    """Load the FAISS vector store if it exists."""
    global vector_store
    from langchain_community.embeddings import FastEmbedEmbeddings
    from langchain_community.vectorstores import FAISS

    if VECTOR_STORE_PATH.exists():
        embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        vector_store = FAISS.load_local(
            str(VECTOR_STORE_PATH), 
            embeddings,
            allow_dangerous_deserialization=True
        )


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request (X-Forwarded-For when behind proxy, else client.host)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or ""
    return ""


def get_vector_store():
    """Return the vector store, loading it on first use (lazy load for fast Cloud Run startup)."""
    global vector_store
    if vector_store is None:
        load_vector_store()
    return vector_store


def _load_scope_graph() -> dict:
    """Load scope_graph.json (cached after first call). Fall back to org_slugs.json if scope_graph missing."""
    global _scope_graph
    if _scope_graph is not None:
        return _scope_graph
    graph_path = VECTOR_STORE_PATH / "scope_graph.json"
    if graph_path.exists():
        try:
            _scope_graph = json.loads(graph_path.read_text(encoding="utf-8"))
        except Exception:
            _scope_graph = {"orgs": [], "competitions": [], "org_to_comps": {}, "comp_to_orgs": {}}
    else:
        slugs_path = VECTOR_STORE_PATH / "org_slugs.json"
        if slugs_path.exists():
            try:
                org_slugs = json.loads(slugs_path.read_text(encoding="utf-8"))
                _scope_graph = {
                    "orgs": org_slugs,
                    "competitions": [],
                    "org_to_comps": {},
                    "comp_to_orgs": {},
                }
            except Exception:
                _scope_graph = {"orgs": [], "competitions": [], "org_to_comps": {}, "comp_to_orgs": {}}
        else:
            _scope_graph = {"orgs": [], "competitions": [], "org_to_comps": {}, "comp_to_orgs": {}}
    return _scope_graph


def _resolve_slug_to_canonical(slug: str, graph: dict, key: str) -> str | None:
    """Resolve URL param to canonical slug. Case-insensitive; hyphens/underscores interchangeable."""
    if not (slug or "").strip():
        return None
    s = slug.strip().lower()
    variants = [s, s.replace("_", "-"), s.replace("-", "_")]
    items = graph.get(key, [])
    for item in items:
        canonical = item.get("slug", "")
        if not canonical:
            continue
        c_lower = canonical.lower()
        c_hyphen = c_lower.replace("_", "-")
        c_underscore = c_lower.replace("-", "_")
        for v in variants:
            if v == c_lower or v == c_hyphen or v == c_underscore:
                return canonical
    return None


def _detect_and_expand(query_text: str) -> tuple[set[str], set[str]]:
    """Detect org and competition tokens, then expand via relationships.
    Returns (expanded_org_slugs, expanded_comp_slugs)."""
    graph = _load_scope_graph()
    detected_orgs = set()
    detected_comps = set()
    q_lower = query_text.lower()

    for org in graph.get("orgs", []):
        for token in org.get("tokens", []):
            pattern = r"(?<![a-zA-Z0-9])" + re.escape(token.lower()) + r"(?![a-zA-Z0-9])"
            if re.search(pattern, q_lower):
                detected_orgs.add(org["slug"])
                break

    for comp in graph.get("competitions", []):
        for token in comp.get("tokens", []):
            pattern = r"(?<![a-zA-Z0-9])" + re.escape(token.lower()) + r"(?![a-zA-Z0-9])"
            if re.search(pattern, q_lower):
                detected_comps.add(comp["slug"])
                break

    org_to_comps = graph.get("org_to_comps", {})
    comp_to_orgs = graph.get("comp_to_orgs", {})

    for org_slug in list(detected_orgs):
        detected_comps |= set(org_to_comps.get(org_slug, []))
    for comp_slug in list(detected_comps):
        detected_orgs |= set(comp_to_orgs.get(comp_slug, []))

    return detected_orgs, detected_comps


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Oregon Soccer Referee Concierge API"}


@app.get("/health")
async def health_check():
    """Detailed health check."""
    store = get_vector_store()
    return {
        "status": "healthy",
        "vector_store_loaded": store is not None
    }


@app.get("/chat", response_model=Response)
async def chat_get(
    request: Request,
    q: str = "",
    org: str | None = None,
    competition: str | None = None,
):
    """Chat via GET ?q= for Cloud Run (avoids 405 on POST). Optional org/competition scope from URL."""
    if not (q or "").strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty")
    graph = _load_scope_graph()
    resolved_org = None
    resolved_comp = None
    if org:
        resolved_org = _resolve_slug_to_canonical(org, graph, "orgs")
        if not resolved_org:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown organization or competition: {org}",
            )
    if competition:
        resolved_comp = _resolve_slug_to_canonical(competition, graph, "competitions")
        if not resolved_comp:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown organization or competition: {competition}",
            )
    return await chat(
        request,
        Query(question=q.strip()),
        url_org=resolved_org,
        url_competition=resolved_comp,
    )


@app.post("/chat", response_model=Response)
async def chat(
    request: Request,
    query: Query,
    url_org: str | None = None,
    url_competition: str | None = None,
):
    """
    Process a chat query and return an AI-generated response.
    Optional url_org/url_competition scope from URL path.
    """
    if not query.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    from backend.rate_limit import check_and_record
    from backend.chat_log import append_rate_limit_log, RATE_LIMIT_MSG

    client_ip = _get_client_ip(request)
    if not check_and_record(client_ip):
        env = "prod" if os.environ.get("K_SERVICE") else "dev"
        try:
            append_rate_limit_log(env, client_ip or None)
        except Exception:
            pass
        raise HTTPException(status_code=429, detail=RATE_LIMIT_MSG)

    try:
        context = ""
        sources = []
        detected_orgs, detected_comps = _detect_and_expand(query.question)
        if url_org:
            detected_orgs = detected_orgs | {url_org}
        if url_competition:
            detected_comps = detected_comps | {url_competition}

        scope_tokens = []
        if url_org:
            scope_tokens.append(url_org)
        if url_competition:
            scope_tokens.append(url_competition)

        store = get_vector_store()
        if store:
            # When URL scope is present, use two-phase retrieval so scoped docs are guaranteed
            # in context. Otherwise similarity ranking can exclude org-specific content.
            search_query = (" ".join(scope_tokens) + " " + query.question) if scope_tokens else query.question
            has_url_scope = bool(scope_tokens)

            if has_url_scope and (detected_orgs or detected_comps):
                org_filter = {"org": {"$in": list(detected_orgs)}} if detected_orgs else None
                comp_filter = {"competition": {"$in": list(detected_comps)}} if detected_comps else None
                scoped_filter = org_filter or comp_filter
                if org_filter and comp_filter:
                    scoped_filter = {"$or": [org_filter, comp_filter]}
                docs_scoped = store.similarity_search(
                    search_query, k=8, fetch_k=40, filter=scoped_filter,
                )
                docs_general = store.similarity_search(
                    search_query, k=2, fetch_k=10, filter={"scope": "general"},
                )
                seen = set()
                docs = []
                for d in docs_scoped + docs_general:
                    key = (d.metadata.get("source"), d.page_content[:150])
                    if key not in seen:
                        seen.add(key)
                        docs.append(d)
                    if len(docs) >= 7:
                        break
            elif detected_orgs or detected_comps:
                clauses = [{"scope": "general"}]
                if detected_orgs:
                    clauses.append({"org": {"$in": list(detected_orgs)}})
                if detected_comps:
                    clauses.append({"competition": {"$in": list(detected_comps)}})
                scope_filter = {"$or": clauses}
                docs = store.similarity_search(
                    search_query, k=7, fetch_k=20, filter=scope_filter,
                )
            else:
                docs = store.similarity_search(
                    search_query, k=7, fetch_k=20, filter={"scope": "general"},
                )
            context = "\n\n".join([doc.page_content for doc in docs])
            sources = [doc.metadata.get("title") or doc.metadata.get("source", "Unknown") for doc in docs]
        
        from google import genai
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GOOGLE_API_KEY or GEMINI_API_KEY must be set")
        client = genai.Client(api_key=api_key)

        org_instruction = ""
        if not detected_orgs and not detected_comps:
            org_instruction = "\nIf the response varies by organization and one was not specified, encourage the user to specify the organization in a follow-up question.\n"
        elif scope_tokens:
            scope_hint = " ".join(scope_tokens)
            org_instruction = f"\nThe user is asking about {scope_hint}. Prioritize information specific to that organization or competition when it appears in the context.\n"

        prompt = f"""I am a soccer referee in Oregon.  I am not an assignor or an administrator.  
You are a helpful assistant for Oregon soccer referees. 
Answer questions about soccer rules, referee procedures, Reftown, and Oregon-specific regulations.

Context from knowledge base:
{context if context else "No specific context available."}

Question: {query.question}

Provide a clear, accurate, and helpful response. For questions about rules refer to the 
latest version of the IFAB Laws of the Game including the FAQs on the LOTG pages, and the USSF Laws of the Game, citing relevant 
rules of competition if applicable.If you're unsure about something, 
say so rather than making up information.
{org_instruction}
Respond in the same language the user used. If the question is in Spanish, answer in Spanish; 
if in English, answer in English; and so on for other languages."""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )
        
        # Log to Google Sheet for review (best-effort; never fail the request)
        env = "prod" if os.environ.get("K_SERVICE") else "dev"
        client_ip = _get_client_ip(request)
        log_id = None
        try:
            from backend.chat_log import append_chat_log
            log_id = append_chat_log(
                env, query.question, response.text, list(set(sources)),
                client_ip=client_ip or None
            )
        except Exception:
            pass
        return Response(
            answer=response.text,
            sources=list(set(sources)),
            log_id=log_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/grade")
async def chat_grade(data: GradeSubmit):
    """
    Record a thumbs up or thumbs down grade for a chat response.
    Returns 404 if the log_id is not found.
    """
    from backend.chat_log import update_chat_log_grade

    ok = update_chat_log_grade(data.log_id, data.grade)
    if not ok:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return {"status": "ok"}


@app.get("/license-status")
async def license_status(request: Request, email: str = "", trigger_query: str = ""):
    """
    Look up the active USSF licenses for a referee by email address.
    Returns licenses grouped by discipline, ordered by rank within each group.
    When called (referee prompt triggered this API), we log the trigger query text,
    whether the email had no match, and the number of license records returned—not the actual result.
    """
    if not email.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'email' is required")

    from backend.license_service import lookup_ussf_id, fetch_active_licenses, enrich_and_group_licenses

    try:
        ussf_id, full_name = await lookup_ussf_id(email.strip())
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if ussf_id is None:
        env = "prod" if os.environ.get("K_SERVICE") else "dev"
        client_ip = _get_client_ip(request)
        try:
            from backend.chat_log import append_license_lookup_log
            append_license_lookup_log(
                env, (trigger_query or "").strip(), no_match=True, license_count=None,
                client_ip=client_ip or None,
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=404,
            detail="No USSF ID found associated with that e-mail address",
        )

    try:
        raw_licenses = await fetch_active_licenses(ussf_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    env = "prod" if os.environ.get("K_SERVICE") else "dev"
    client_ip = _get_client_ip(request)
    try:
        from backend.chat_log import append_license_lookup_log
        append_license_lookup_log(
            env, (trigger_query or "").strip(), no_match=False, license_count=len(raw_licenses),
            client_ip=client_ip or None,
        )
    except Exception:
        pass

    grouped_licenses = enrich_and_group_licenses(raw_licenses)

    return {
        "ussf_id": ussf_id,
        "full_name": full_name,
        "licenses": grouped_licenses
    }


@app.post("/feedback")
async def submit_feedback(body: FeedbackSubmit):
    """
    Submit user feedback (missing or incorrect information). Stored in the same
    Google Sheet as the chat log, under the Feedback tab.
    """
    if not (body.description or "").strip():
        raise HTTPException(status_code=400, detail="Feedback description is required")
    try:
        from backend.chat_log import append_feedback
        append_feedback(user=body.name or "", feedback=body.description.strip())
    except Exception:
        pass  # best-effort; don't fail the request
    return {"status": "ok"}


# Serve static frontend files in production
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        """Serve the frontend for all non-API routes."""
        # Don't serve frontend for API routes
        if full_path.startswith("api/") or full_path in ["health", "chat", "license-status", "feedback", "docs", "openapi.json", "redoc"]:
            raise HTTPException(status_code=404, detail="Not found")
        # Serve static files (e.g. .md) if they exist under STATIC_DIR
        if ".." not in full_path:
            static_file = STATIC_DIR / full_path
            if static_file.is_file():
                return FileResponse(static_file)
        # Serve index.html for SPA routing
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, workers=5)
