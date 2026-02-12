#!/usr/bin/env python3
"""
RefTown.com authentication for scripts that fetch or ingest reftown.com URLs.
Uses REFTOWN_USERNAME and REFTOWN_PASSWORD from the environment.
Also provides a shared fetch helper that follows redirects up to a limit.
"""

import re
import os
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


MAX_REDIRECTS = 3


def _meta_refresh_url(html: str, base_url: str) -> str | None:
    """Extract redirect URL from <meta http-equiv="refresh" content="...">, JavaScript, or a continue link."""
    if not (html or "").strip():
        return None
    soup = BeautifulSoup(html, "html.parser")
    metas = soup.find_all("meta", attrs={"http-equiv": re.compile(r"refresh", re.I)})
    for meta in metas:
        content = meta.get("content") or ""
        m = re.search(r"url\s*=\s*([^\s;]+)", content, re.I)
        if m:
            target = m.group(1).strip()
            return target if target.startswith(("http://", "https://")) else urljoin(base_url, target)

    raw = html or ""
    js_match = re.search(r"(?:location\.href|window\.location)\s*=\s*[\"']([^\"']+)[\"']", raw, re.I)
    if js_match:
        target = js_match.group(1).strip()
        return target if target.startswith(("http://", "https://")) else urljoin(base_url, target)
    raw_meta = re.search(r"content\s*=\s*[\"'][^\"']*url\s*=\s*([^\s\"';]+)", raw, re.I)
    if raw_meta:
        target = raw_meta.group(1).strip()
        return target if target.startswith(("http://", "https://")) else urljoin(base_url, target)
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href or href.startswith(("#", "javascript:")):
            continue
        target = href if href.startswith(("http://", "https://")) else urljoin(base_url, href)
        if urlparse(base_url).netloc == urlparse(target).netloc and "custom.asp" in target:
            return target
    return None


def get_with_limited_redirects(
    url: str,
    session: requests.Session | None = None,
    max_redirects: int = MAX_REDIRECTS,
    **kwargs,
) -> requests.Response:
    """
    GET a URL following up to max_redirects redirects (default 3).
    Uses session if provided, otherwise requests.get. Returns the final response.
    """
    client = session if session is not None else requests
    for _ in range(max_redirects + 1):
        resp = client.get(url, allow_redirects=False, **kwargs)
        status = resp.status_code
        location = resp.headers.get("Location") or resp.headers.get("location")
        if status in (301, 302, 303, 307, 308):
            if location:
                url = location if location.startswith(("http://", "https://")) else urljoin(resp.url, location)
                continue
        elif status == 200:
            # Only follow client-side redirect when request URL is a known intermediary (e.g. RefTown link.asp).
            meta_url = _meta_refresh_url(resp.text or "", resp.url) if "link.asp" in url else None
            if meta_url:
                url = meta_url
                continue
        return resp
    return resp


LOGIN_URL = "https://reftown.com/login.asp"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Module-level session cache so we only log in once per process
_session_cache: requests.Session | None = None


def is_reftown_url(url: str) -> bool:
    """Return True if the URL belongs to reftown.com."""
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "").lower()
    return domain == "reftown.com"


def get_reftown_session() -> requests.Session | None:
    """
    Log in to RefTown and return an authenticated requests.Session, or None
    if credentials are missing or login fails. Uses a cached session after
    the first successful login.
    """
    global _session_cache
    if _session_cache is not None:
        return _session_cache

    username = os.environ.get("REFTOWN_USERNAME")
    password = os.environ.get("REFTOWN_PASSWORD")
    if not username or not password:
        return None

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    try:
        # Fetch login page to get form and any cookies
        resp = session.get(LOGIN_URL, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find the login form (form that contains a password input)
        # Match type case-insensitively (e.g. "Password" in HTML)
        login_form = None
        forms = soup.find_all("form")
        for form in forms:
            if form.find("input", {"type": re.compile(r"password", re.I)}):
                login_form = form
                break

        if not login_form:
            return None

        # Form action (resolve relative to base)
        action = login_form.get("action") or "login.asp"
        post_url = urljoin(LOGIN_URL, action)
        method = (login_form.get("method") or "get").strip().upper()
        if method != "POST":
            post_url = LOGIN_URL  # fallback to login.asp with POST

        def _input_type(t: str | None) -> str:
            return (t or "").lower()

        data: dict[str, str] = {}
        for inp in login_form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            it = _input_type(inp.get("type"))
            if it == "password":
                data[name] = password
            elif it in ("text", "email", "") and _is_username_field(name):
                data[name] = username
            elif it in ("hidden", "submit", "image"):
                val = inp.get("value")
                if val is not None:
                    data[name] = val
            elif it in ("checkbox", "radio"):
                if inp.get("checked") is not None:
                    data[name] = inp.get("value", "on")
            else:
                val = inp.get("value")
                if val is not None:
                    data[name] = val

        for inp in login_form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            it = _input_type(inp.get("type"))
            if it == "password" and name not in data:
                data[name] = password
            if it in ("text", "email") and name not in data:
                if _is_username_field(name) or not any(_is_username_field(k) for k in data):
                    data[name] = username

        post_resp = session.post(post_url, data=data, timeout=30, allow_redirects=True)
        post_resp.raise_for_status()

        _session_cache = session
        return session

    except Exception:
        return None


def _is_username_field(name: str) -> bool:
    """Return True if the input name looks like a username/email field."""
    n = name.lower()
    return any(
        x in n
        for x in ("user", "email", "login", "account", "name", "uid", "member")
    ) and "pass" not in n
