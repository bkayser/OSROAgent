#!/usr/bin/env python3
"""
Ingest script for Oregon Soccer Referee Concierge.
This script handles document ingestion and vector store creation.
"""

import os
from pathlib import Path

# Load .env file if it exists (before importing modules that need env vars)
def load_dotenv():
    """Load environment variables from .env file in project root."""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    # Remove surrounding quotes if present
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key.strip(), value)

load_dotenv()

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
VECTOR_STORE_PATH = Path("./vector_store")
URLS_FILE = DATA_DIR / "_urls.txt"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.2 Safari/605.1.15"

# Files to exclude from ingestion (templates, placeholders)
EXCLUDE_MD_PATTERNS = ["**/_*",]


def _parse_markdown_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown if present. Returns (metadata_from_frontmatter, body)."""
    metadata = {}
    body = content
    if content.startswith("---"):
        rest = content[3:]
        idx = rest.find("\n---")
        if idx != -1:
            fm = rest[:idx].strip()
            body = rest[idx + 4:].lstrip("\n")
            for line in fm.split("\n"):
                line = line.strip()
                if ":" in line:
                    k, v = line.split(":", 1)
                    metadata[k.strip().lower()] = v.strip()
    return metadata, body


def _strip_markdown_frontmatter(doc: Document) -> Document:
    """Move frontmatter (title, source) into metadata and set page_content to body only."""
    meta, body = _parse_markdown_frontmatter(doc.page_content)
    new_meta = dict(doc.metadata)
    if meta.get("title"):
        new_meta["title"] = meta["title"]
    if meta.get("source"):
        new_meta["source"] = meta["source"]
    return Document(page_content=body, metadata=new_meta)


def _enrich_doc_metadata(doc: Document) -> Document:
    """Add doc_type, org, and title (from path) from file path. URL docs keep existing metadata."""
    source = (doc.metadata.get("source") or "").replace("\\", "/")
    new_meta = dict(doc.metadata)
    if source.startswith("http://") or source.startswith("https://"):
        if "theifab.com" in source:
            new_meta["doc_type"] = "laws"
        return Document(page_content=doc.page_content, metadata=new_meta)
    # File path
    path_lower = source.lower()
    if "/orgs/" in path_lower or "\\orgs\\" in path_lower:
        new_meta["doc_type"] = "org"
        parts = source.replace("\\", "/").split("/")
        try:
            i = parts.index("orgs")
            if i + 1 < len(parts):
                new_meta["org"] = parts[i + 1]
        except ValueError:
            pass
    elif "/text/" in path_lower or "\\text\\" in path_lower:
        if "faq" in path_lower or "faqs" in path_lower:
            new_meta["doc_type"] = "faq"
        elif "directory" in path_lower:
            new_meta["doc_type"] = "directory"
        elif "certification" in path_lower:
            new_meta["doc_type"] = "certification"
        else:
            new_meta["doc_type"] = "general"
    else:
        if "rules" in path_lower and (path_lower.endswith(".pdf") or path_lower.endswith(".md")):
            new_meta["doc_type"] = "league_rules"
        else:
            new_meta["doc_type"] = "general"
    if not new_meta.get("title") and (source.endswith(".md") or source.endswith(".txt") or source.endswith(".pdf")):
        try:
            name = Path(source).stem
            if name:
                new_meta["title"] = name.replace("_", " ").replace("-", " ")
        except Exception:
            pass
    return Document(page_content=doc.page_content, metadata=new_meta)


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
                title = ""
                if soup.title and soup.title.string:
                    title = soup.title.string.strip()
                if not title:
                    h1 = soup.find("h1")
                    if h1 and h1.get_text(strip=True):
                        title = h1.get_text(separator=" ", strip=True)
                text = soup.get_text(separator="\n", strip=True)
                meta = {"source": u, "doc_type": "web_page"}
                if title:
                    meta["title"] = title
                return Document(page_content=text, metadata=meta)
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
    """Load documents from data/ (recursive: all .txt, .md, .pdf) and URLs file."""
    documents = []
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data_root = str(DATA_DIR)

    # Load .txt from data/ and all subdirectories (exclude files starting with _)
    try:
        print(f"Loading text files from {DATA_DIR} (recursive)...")
        loader = DirectoryLoader(data_root, glob="**/*.txt", loader_cls=TextLoader, exclude=["**/_*"])
        txt_docs = loader.load()
        for source in sorted({doc.metadata.get("source", "unknown") for doc in txt_docs}):
            print(f"  Source: {source}")
        documents.extend(txt_docs)
        print(f"Loaded {len(txt_docs)} text files")
    except Exception as e:
        print(f"Error loading text files: {e}")

    # Load .md from data/ and all subdirectories (exclude templates and files starting with _)
    try:
        print(f"Loading markdown files from {DATA_DIR} (recursive)...")
        loader = DirectoryLoader(data_root, glob="**/*.md", loader_cls=TextLoader, exclude=EXCLUDE_MD_PATTERNS)
        md_docs = loader.load()
        # Exclude league-template if still present (e.g. if loader doesn't support exclude)
        md_docs = [d for d in md_docs if "league-template.md" not in (d.metadata.get("source") or "")]
        # Strip YAML frontmatter into metadata and use body only for embedding
        md_docs = [_strip_markdown_frontmatter(d) for d in md_docs]
        for source in sorted({doc.metadata.get("source", "unknown") for doc in md_docs}):
            print(f"  Source: {source}")
        documents.extend(md_docs)
        print(f"Loaded {len(md_docs)} markdown files")
    except Exception as e:
        print(f"Error loading markdown files: {e}")

    # Load .pdf from data/ and all subdirectories (exclude files starting with _)
    try:
        print(f"Loading PDFs from {DATA_DIR} (recursive)...")
        loader = DirectoryLoader(data_root, glob="**/*.pdf", loader_cls=PyPDFLoader, exclude=["**/_*"])
        pdf_docs = loader.load()
        for source in sorted({doc.metadata.get("source", "unknown") for doc in pdf_docs}):
            print(f"  Source: {source}")
        documents.extend(pdf_docs)
        print(f"Loaded {len(pdf_docs)} PDF pages")
    except Exception as e:
        print(f"Error loading PDF files: {e}")

    # Load from URLs file (in data/ root)
    documents.extend(load_urls(URLS_FILE))

    # Enrich metadata: doc_type, org, title from path (for file-based docs)
    documents = [_enrich_doc_metadata(d) for d in documents]

    print(f"Total loaded: {len(documents)} documents")
    return documents


def split_documents(documents: list) -> list:
    """Split documents into chunks for embedding. Uses markdown-aware separators and larger chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=250,
        length_function=len,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
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
