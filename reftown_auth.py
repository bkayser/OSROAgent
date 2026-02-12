#!/usr/bin/env python3
"""
RefTown.com authentication for scripts that fetch or ingest reftown.com URLs.
Uses REFTOWN_USERNAME and REFTOWN_PASSWORD from the environment.
"""

import os
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


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
        login_form = None
        for form in soup.find_all("form"):
            if form.find("input", {"type": "password"}):
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

        # Build POST data: collect all inputs, then override username/password
        data: dict[str, str] = {}
        for inp in login_form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            if inp.get("type") == "password":
                data[name] = password
            elif inp.get("type") in ("text", "email", None) and _is_username_field(name):
                data[name] = username
            elif inp.get("type") in ("hidden", "submit", "image"):
                val = inp.get("value")
                if val is not None:
                    data[name] = val
            elif inp.get("type") in ("checkbox", "radio"):
                if inp.get("checked") is not None:
                    data[name] = inp.get("value", "on")
            else:
                val = inp.get("value")
                if val is not None:
                    data[name] = val

        # If we didn't find username/password by name heuristic, set by type
        for inp in login_form.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            if inp.get("type") == "password" and name not in data:
                data[name] = password
            if inp.get("type") in ("text", "email") and name not in data:
                if _is_username_field(name) or not any(_is_username_field(k) for k in data):
                    data[name] = username

        post_resp = session.post(post_url, data=data, timeout=30, allow_redirects=True)
        post_resp.raise_for_status()

        # Consider login successful; cache for reuse
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
