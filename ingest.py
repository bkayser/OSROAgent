#!/usr/bin/env python3
"""
Ingest script for Oregon Soccer Referee Concierge.
This script handles document ingestion and vector store creation.
"""

import os
from pathlib import Path

from bs4 import BeautifulSoup
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader, WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Configuration
DATA_DIR = Path("./data")
VECTOR_STORE_PATH = Path("./vector_store")
URLS_FILE = Path("./urls.txt")


def load_urls(url_file: Path) -> list:
    """Load and scrape documents from URLs listed in a file."""
    documents = []
    
    if not url_file.exists():
        print(f"URL file {url_file} not found, skipping URL ingestion")
        return documents
    
    # Read URLs from file (one per line, ignore comments and blank lines)
    urls = [
        line.strip() for line in url_file.read_text().split('\n')
        if line.strip() and not line.startswith('#')
    ]
    
    if not urls:
        print("No URLs found in URL file")
        return documents
    
    try:
        loader = WebBaseLoader(urls)
        documents = loader.load()
        print(f"Loaded {len(documents)} web pages")
    except Exception as e:
        print(f"Error loading URLs: {e}")
    
    return documents


def load_documents(data_dir: Path) -> list:
    """Load documents from the data directory."""
    documents = []
    
    if not data_dir.exists():
        print(f"Data directory {data_dir} does not exist. Creating it...")
        data_dir.mkdir(parents=True, exist_ok=True)
        return documents
    
    # Load text files
    try:
        loader = DirectoryLoader(
            str(data_dir),
            glob="**/*.txt",
            loader_cls=TextLoader
        )
        txt_docs = loader.load()
        documents.extend(txt_docs)
        print(f"Loaded {len(txt_docs)} text files")
    except Exception as e:
        print(f"Error loading text files: {e}")
    
    # Load PDF files
    try:
        loader = DirectoryLoader(
            str(data_dir),
            glob="**/*.pdf",
            loader_cls=PyPDFLoader
        )
        pdf_docs = loader.load()
        documents.extend(pdf_docs)
        print(f"Loaded {len(pdf_docs)} PDF pages")
    except Exception as e:
        print(f"Error loading PDF files: {e}")
    
    # Load from URLs file
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
    
    # Load documents
    documents = load_documents(DATA_DIR)
    
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
