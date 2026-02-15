#!/usr/bin/env python3
"""
Fetch public webpages and convert them to markdown for curation.

Usage:
    ./scripts/fetch_pages.py <url1> [url2] [url3] ...
    
    # Or with a file containing URLs (one per line; empty lines and # comments are ignored):
    ./scripts/fetch_pages.py --file urls.txt

    # In the file, each line may be: URL  or  URL whitespace output-basename
    # If the basename is present it is used for the markdown file (e.g. my-page becomes data/my-page.md).
    # Otherwise the filename is derived from the URL path.

Output files are saved to the data/text/ directory for ingestion.
"""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md


# Project root is parent of scripts directory
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
DATA_DIR = ROOT_DIR / "data"
TEXT_DIR = DATA_DIR / "text"  # Output directory for fetched markdown files

# Load .env file if it exists (before importing reftown_auth)
def load_dotenv():
    """Load environment variables from .env file in project root."""
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        import os
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    # Remove surrounding quotes if present
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key.strip(), value)

load_dotenv()

# Allow importing reftown_auth when run as ./scripts/fetch_pages.py
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import reftown_auth


def url_to_filename(url: str) -> str:
    """
    Convert a URL to a safe filename.
    
    Examples:
        https://www.theifab.com/laws/latest/fouls-and-misconduct/
        -> ifab_latest_fouls-and-misconduct.md
    """
    parsed = urlparse(url)
    
    # Start with the domain (without www.)
    domain = parsed.netloc.replace("www.", "")
    
    # Add the path, replacing slashes with underscores
    path = parsed.path.strip("/").replace("/", "_")
    
    # Combine and clean up
    if path:
        filename = f"{domain}_{path}"
    else:
        filename = domain
    
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'_+', '_', filename)  # Collapse multiple underscores
    filename = filename.strip('_')
    
    # Ensure it ends with .md
    if not filename.endswith('.md'):
        filename += '.md'
    
    return filename


def fetch_and_convert(url: str) -> tuple[str, str]:
    """
    Fetch a webpage and convert it to markdown.
    
    Returns:
        Tuple of (markdown_content, title)
    """
    print(f"Fetching: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    if reftown_auth.is_reftown_url(url):
        session = reftown_auth.get_reftown_session()
        if session is None:
            print("  -> RefTown credentials (REFTOWN_USERNAME, REFTOWN_PASSWORD) not set; fetching without auth.", file=sys.stderr)
            response = reftown_auth.get_with_limited_redirects(url, session=None, headers=headers, timeout=30)
        else:
            response = reftown_auth.get_with_limited_redirects(url, session=session, headers=headers, timeout=30)
    else:
        response = reftown_auth.get_with_limited_redirects(url, session=None, headers=headers, timeout=30)

    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract title
    title = soup.title.string if soup.title else url
    
    # Remove script, style, nav, footer, and other non-content elements
    for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 
                                   'aside', 'iframe', 'noscript']):
        element.decompose()
    
    # Try to find the main content area
    main_content = None
    if reftown_auth.is_reftown_url(url):
        # RefTown uses div.rtcontent for page body; avoid matching mainmenu/main
        main_content = (
            soup.find('div', class_=re.compile(r'^rtcontent$', re.I)) or
            soup.find('div', class_=re.compile(r'customcontent-wrapper', re.I)) or
            soup.find('div', id=re.compile(r'rtcontent|customcontent', re.I))
        )
    if main_content is None:
        main_content = (
            soup.find('main') or
            soup.find('article') or
            soup.find('div', class_=re.compile(r'content|main|article', re.I)) or
            soup.find('body')
        )
    
    if main_content is None:
        main_content = soup
    
    # Convert to markdown
    markdown = md(
        str(main_content),
        heading_style="ATX",
        bullets="-",
        strip=['img', 'figure', 'figcaption'],  # Remove images for text-only
    )
    
    # Clean up the markdown
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)  # Max 2 newlines
    markdown = markdown.strip()
    
    # Add metadata header
    header = f"""---
source: {url}
title: {title}
---

# {title}

"""
    
    return header + markdown, title


def process_url(url: str, output_basename: str | None = None) -> bool:
    """
    Process a single URL: fetch, convert, and save.

    If output_basename is given (e.g. from a file line), use it as a path relative
    to the data/ directory. Can include subdirectories like "orgs/NWSC/assignors.md".
    If not given, defaults to data/text/{url-derived-name}.md.
    If the output file already exists, an error is printed and the file is not overwritten.
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        if output_basename:
            # Interpret as relative path from data/ directory
            rel_path = output_basename.strip()
            # Sanitize each path component (but preserve directory structure)
            parts = Path(rel_path).parts
            sanitized_parts = [re.sub(r'[<>:"|?*]', '_', p) for p in parts]
            rel_path = str(Path(*sanitized_parts))
            if not rel_path.endswith(".md"):
                rel_path = f"{rel_path}.md"
            output_path = DATA_DIR / rel_path
        else:
            filename = url_to_filename(url)
            output_path = TEXT_DIR / filename
        
        # Ensure parent directories exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.exists():
            print(f"  -> Error: {output_path} already exists; skipping (not overwriting).", file=sys.stderr)
            return False

        markdown, title = fetch_and_convert(url)
        output_path.write_text(markdown, encoding='utf-8')
        print(f"  -> Saved: {output_path} ({len(markdown)} chars)")
        return True

    except requests.RequestException as e:
        print(f"  -> Error fetching {url}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  -> Error processing {url}: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Fetch webpages and convert to markdown for curation."
    )
    parser.add_argument(
        'urls',
        nargs='*',
        help="URLs to fetch and convert"
    )
    parser.add_argument(
        '--file', '-f',
        type=Path,
        help="File containing URLs (one per line; optional whitespace and output basename)"
    )
    
    args = parser.parse_args()
    
    # List of (url, output_basename or None). CLI args have no basename.
    entries: list[tuple[str, str | None]] = [(u, None) for u in args.urls]
    
    if args.file:
        if not args.file.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        with open(args.file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(None, 1)
                url = parts[0].strip()
                basename = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
                entries.append((url, basename))
    
    if not entries:
        parser.print_help()
        print("\nError: No URLs provided.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Processing {len(entries)} URL(s)...\n")
    
    success_count = 0
    for url, basename in entries:
        if process_url(url, basename):
            success_count += 1
        print()
    
    print(f"Done. {success_count}/{len(entries)} URLs processed successfully.")
    print(f"Output directory: {TEXT_DIR.absolute()}")


if __name__ == "__main__":
    main()
