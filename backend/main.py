"""
FastAPI backend for Oregon Soccer Referee Concierge.
"""

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
# genai/langchain/FAISS imported lazily in handlers for fast startup

app = FastAPI(
    title="Oregon Soccer Referee Concierge",
    description="AI-powered concierge for Oregon soccer referees",
    version="1.0.0"
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

# Global vector store instance
vector_store = None


class Query(BaseModel):
    """Request model for chat queries."""
    question: str


class Response(BaseModel):
    """Response model for chat answers."""
    answer: str
    sources: list[str] = []


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


def get_vector_store():
    """Return the vector store, loading it on first use (lazy load for fast Cloud Run startup)."""
    global vector_store
    if vector_store is None:
        load_vector_store()
    return vector_store


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup. Vector store is loaded lazily on first use."""
    from backend.license_service import load_license_reference
    load_license_reference()


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
async def chat_get(q: str = ""):
    """Chat via GET ?q= for Cloud Run (avoids 405 on POST)."""
    if not (q or "").strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty")
    return await chat(Query(question=q.strip()))


@app.post("/chat", response_model=Response)
async def chat(query: Query):
    """
    Process a chat query and return an AI-generated response.
    """
    if not query.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        context = ""
        sources = []
        
        # Retrieve relevant context if vector store is available
        store = get_vector_store()
        if store:
            docs = store.similarity_search(query.question, k=3)
            context = "\n\n".join([doc.page_content for doc in docs])
            sources = [doc.metadata.get("source", "Unknown") for doc in docs]
        
        # Generate response using Gemini
        from google import genai
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GOOGLE_API_KEY or GEMINI_API_KEY must be set")
        client = genai.Client(api_key=api_key)

        prompt = f"""I am a soccer referee in Oregon.  I am not an assignor or an administrator.  
You are a helpful assistant for Oregon soccer referees. 
Answer questions about soccer rules, referee procedures, Reftown, and Oregon-specific regulations.

Context from knowledge base:
{context if context else "No specific context available."}

Question: {query.question}

Provide a clear, accurate, and helpful response. If you're unsure about something, 
say so rather than making up information."""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )
        
        return Response(
            answer=response.text,
            sources=list(set(sources))
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/license-status")
async def license_status(email: str = ""):
    """
    Look up the active USSF licenses for a referee by email address.
    Returns licenses grouped by discipline, ordered by rank within each group.
    """
    if not email.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'email' is required")

    from backend.license_service import lookup_ussf_id, fetch_active_licenses, enrich_and_group_licenses

    try:
        ussf_id = await lookup_ussf_id(email.strip())
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if ussf_id is None:
        raise HTTPException(
            status_code=404,
            detail="No USSF ID found associated with that e-mail address",
        )

    try:
        raw_licenses = await fetch_active_licenses(ussf_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return enrich_and_group_licenses(raw_licenses)


# Serve static frontend files in production
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        """Serve the frontend for all non-API routes."""
        # Don't serve frontend for API routes
        if full_path.startswith("api/") or full_path in ["health", "chat", "license-status", "docs", "openapi.json", "redoc"]:
            raise HTTPException(status_code=404, detail="Not found")
        
        # Serve index.html for SPA routing
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
