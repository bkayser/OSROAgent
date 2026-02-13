#!/usr/bin/env python3
"""
Ingest script for Oregon Soccer Referee Concierge.
This script handles document ingestion and vector store creation.
"""

import os
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain_core.documents import Document

import reftown_auth
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Configuration
DATA_DIR = Path("./data")
TEXT_DIR = DATA_DIR / "text"      # Markdown and text files
PDFS_DIR = DATA_DIR / "pdfs"      # PDF documents
VECTOR_STORE_PATH = Path("./vector_store")
URLS_FILE = DATA_DIR / "urls.txt"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.2 Safari/605.1.15"


def load_urls(url_file: Path) -> list:
    """Load and scrape documents from URLs listed in a file."""
    documents = []
    
    if not url_file.exists():
        print(f"URL file {url_file} not found, skipping URL ingestion")
        return documents
    
    # Read URLs from file (one per line, ignore comments and blank lines)
    urls = [
        line.strip() for line in url_file.read_text().split('\n')
        if (s := line.strip()) and not s.startswith('#')
    ]
    
    if not urls:
        print("No URLs found in URL file")
        return documents
    
    reftown_urls = [u for u in urls if reftown_auth.is_reftown_url(u)]
    other_urls = [u for u in urls if u not in reftown_urls]

    try:
        print("Loading URLs...")
        all_docs = []
        request_kwargs = {"headers": {"User-Agent": USER_AGENT}, "timeout": 30}

        def fetch_url_to_doc(u: str, sess: requests.Session | None) -> Document | None:
            try:
                resp = reftown_auth.get_with_limited_redirects(u, session=sess, max_redirects=3, **request_kwargs)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup.find_all(["script", "style"]):
                    tag.decompose()
                text = soup.get_text(separator="\n", strip=True)
                return Document(page_content=text, metadata={"source": u})
            except Exception as e:
                print(f"  Error loading {u}: {e}")
                return None

        if other_urls:
            for u in other_urls:
                doc = fetch_url_to_doc(u, None)
                if doc:
                    all_docs.append(doc)

        if reftown_urls:
            session = reftown_auth.get_reftown_session()
            if session is None:
                print("  RefTown credentials (REFTOWN_USERNAME, REFTOWN_PASSWORD) not set; skipping RefTown URLs.")
            else:
                for u in reftown_urls:
                    doc = fetch_url_to_doc(u, session)
                    if doc:
                        all_docs.append(doc)

        documents = all_docs
        for source in sorted({doc.metadata.get("source", "unknown") for doc in documents}):
            print(f"  Source: {source}")
        print(f"Loaded {len(documents)} web pages")
    except Exception as e:
        print(f"Error loading URLs: {e}")
    
    return documents


def load_documents() -> list:
    """Load documents from the data subdirectories and URLs file."""
    documents = []
    
    # Ensure directories exist
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    PDFS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load text files from data/text/
    try:
        print(f"Loading text files from {TEXT_DIR}...")
        loader = DirectoryLoader(
            str(TEXT_DIR),
            glob="**/*.txt",
            loader_cls=TextLoader
        )
        txt_docs = loader.load()
        for source in sorted({doc.metadata.get("source", "unknown") for doc in txt_docs}):
            print(f"  Source: {source}")
        documents.extend(txt_docs)
        print(f"Loaded {len(txt_docs)} text files")
    except Exception as e:
        print(f"Error loading text files: {e}")
    
    # Load markdown files from data/text/
    try:
        print(f"Loading markdown files from {TEXT_DIR}...")
        loader = DirectoryLoader(
            str(TEXT_DIR),
            glob="**/*.md",
            loader_cls=TextLoader
        )
        md_docs = loader.load()
        for source in sorted({doc.metadata.get("source", "unknown") for doc in md_docs}):
            print(f"  Source: {source}")
        documents.extend(md_docs)
        print(f"Loaded {len(md_docs)} markdown files")
    except Exception as e:
        print(f"Error loading markdown files: {e}")
    
    # Load PDF files from data/pdfs/
    try:
        print(f"Loading PDFs from {PDFS_DIR}...")
        loader = DirectoryLoader(
            str(PDFS_DIR),
            glob="**/*.pdf",
            loader_cls=PyPDFLoader
        )
        pdf_docs = loader.load()
        for source in sorted({doc.metadata.get("source", "unknown") for doc in pdf_docs}):
            print(f"  Source: {source}")
        documents.extend(pdf_docs)
        print(f"Loaded {len(pdf_docs)} PDF pages")
    except Exception as e:
        print(f"Error loading PDF files: {e}")
    
    # Load from URLs file (in data/ root)
    documents.extend(load_urls(URLS_FILE))
    
    print(f"Total loaded: {len(documents)} documents")
    return documents


def split_documents(documents: list) -> list:
    """Split documents into chunks for embedding."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    
    chunks = text_splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks")
    return chunks


def create_vector_store(chunks: list, store_path: Path) -> FAISS:
    """Create and save FAISS vector store from document chunks."""
    embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    
    vector_store = FAISS.from_documents(chunks, embeddings)
    
    store_path.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(store_path))
    print(f"Vector store saved to {store_path}")
    
    return vector_store


def main():
    """Main ingestion pipeline."""
    print("Starting document ingestion...")
    
    # Load documents from subdirectories
    documents = load_documents()
    
    if not documents:
        print("No documents found. Please add documents to the data directory.")
        return
    
    # Split documents into chunks
    chunks = split_documents(documents)
    
    # Create vector store
    create_vector_store(chunks, VECTOR_STORE_PATH)
    
    print("Ingestion complete!")


if __name__ == "__main__":
    main()
