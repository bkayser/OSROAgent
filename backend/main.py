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

from google import genai
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings


app = FastAPI(
    title="Oregon Soccer Referee Concierge",
    description="AI-powered concierge for Oregon soccer referees",
    version="1.0.0"
)

# CORS configuration for frontend (development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000"],
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
    
    if VECTOR_STORE_PATH.exists():
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vector_store = FAISS.load_local(
            str(VECTOR_STORE_PATH), 
            embeddings,
            allow_dangerous_deserialization=True
        )
        print("Vector store loaded successfully")
    else:
        print("No vector store found. Run ingest.py first.")


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    load_vector_store()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Oregon Soccer Referee Concierge API"}


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "vector_store_loaded": vector_store is not None
    }


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
        if vector_store:
            docs = vector_store.similarity_search(query.question, k=3)
            context = "\n\n".join([doc.page_content for doc in docs])
            sources = [doc.metadata.get("source", "Unknown") for doc in docs]
        
        # Generate response using Gemini
        # Note: GOOGLE_API_KEY environment variable must be set
        client = genai.Client()
        
        prompt = f"""You are a helpful assistant for Oregon soccer referees. 
Answer questions about soccer rules, referee procedures, and Oregon-specific regulations.

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


# Serve static frontend files in production
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        """Serve the frontend for all non-API routes."""
        # Don't serve frontend for API routes
        if full_path.startswith("api/") or full_path in ["health", "chat", "docs", "openapi.json", "redoc"]:
            raise HTTPException(status_code=404, detail="Not found")
        
        # Serve index.html for SPA routing
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
