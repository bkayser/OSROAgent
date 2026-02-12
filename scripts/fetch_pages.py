#!/usr/bin/env python3
"""
Fetch public webpages and convert them to markdown for curation.

Usage:
    ./scripts/fetch_pages.py <url1> [url2] [url3] ...
    
    # Or with a file containing URLs (one per line):
    ./scripts/fetch_pages.py --file urls.txt

Output files are saved to the data/ directory with filenames based on the URL.
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

# Allow importing reftown_auth when run as ./scripts/fetch_pages.py
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import reftown_auth


def url_to_filename(url: str) -> str:
    """
    Convert a URL to a safe filename.
    
    Examples:
        https://www.theifab.com/laws/latest/fouls-and-misconduct/
        -> theifab.com_laws_latest_fouls-and-misconduct.md
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
            response = requests.get(url, headers=headers, timeout=30)
        else:
            response = session.get(url, headers=headers, timeout=30)
    else:
        response = requests.get(url, headers=headers, timeout=30)
    
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract title
    title = soup.title.string if soup.title else url
    
    # Remove script, style, nav, footer, and other non-content elements
    for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 
                                   'aside', 'iframe', 'noscript']):
        element.decompose()
    
    # Try to find the main content area
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


def process_url(url: str) -> bool:
    """
    Process a single URL: fetch, convert, and save.
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        markdown, title = fetch_and_convert(url)
        
        filename = url_to_filename(url)
        output_path = DATA_DIR / filename
        
        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
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
        help="File containing URLs (one per line)"
    )
    
    args = parser.parse_args()
    
    urls = list(args.urls)
    
    # Load URLs from file if specified
    if args.file:
        if not args.file.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        
        with open(args.file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    urls.append(line)
    
    if not urls:
        parser.print_help()
        print("\nError: No URLs provided.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Processing {len(urls)} URL(s)...\n")
    
    success_count = 0
    for url in urls:
        if process_url(url):
            success_count += 1
        print()
    
    print(f"Done. {success_count}/{len(urls)} URLs processed successfully.")
    print(f"Output directory: {DATA_DIR.absolute()}")


if __name__ == "__main__":
    main()
