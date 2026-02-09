"""
Service module for interacting with the USSF Learning Center Certification API.
"""

import json
import os
from pathlib import Path

import httpx

USSF_API_BASE_URL = "https://connect.learning.ussoccer.com/certifications"

# License reference data loaded at startup
_license_reference: dict = {}


def load_license_reference():
    """Load the license reference data from the JSON file at server start."""
    global _license_reference
    data_path = Path(__file__).parent / "license_data.json"
    with open(data_path) as f:
        _license_reference = json.load(f)


def get_license_reference() -> dict:
    """Return the license reference lookup table."""
    return _license_reference


async def _get_access_token(client: httpx.AsyncClient) -> str:
    """Authenticate with the USSF API and return an access token."""
    username = os.environ.get("USSF_API_USERNAME")
    password = os.environ.get("USSF_API_PASSWORD")
    if not username or not password:
        raise RuntimeError("USSF_API_USERNAME and USSF_API_PASSWORD environment variables must be set")

    resp = await client.post(
        f"{USSF_API_BASE_URL}/login",
        json={"username": username, "password": password},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"USSF API login failed with status {resp.status_code}")
    return resp.json()["access_token"]


async def lookup_ussf_id(email: str) -> str | None:
    """Look up the USSF ID for the given email address. Returns None if not found."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        token = await _get_access_token(client)
        resp = await client.get(
            f"{USSF_API_BASE_URL}/users",
            params={"email": email},
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise RuntimeError(f"USSF API user lookup failed with status {resp.status_code}")
        return resp.json().get("ussf_id")


async def fetch_active_licenses(ussf_id: str) -> list[dict]:
    """Fetch the list of active licenses for the given USSF ID."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        token = await _get_access_token(client)
        resp = await client.get(
            f"{USSF_API_BASE_URL}/licenses/{ussf_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"USSF API license fetch failed with status {resp.status_code}")
        data = resp.json()
        return [lic for lic in data.get("licenses", []) if lic.get("status") == "active"]


def enrich_and_group_licenses(raw_licenses: list[dict]) -> dict:
    """
    Enrich raw license records with reference data and group them by discipline.

    Each license is enriched with name, discipline, rank, and pathway from
    the reference table using the concatenated discipline + license_id key.
    Licenses within each group are ordered by rank (ascending = higher rank first).
    """
    ref = get_license_reference()
    grouped: dict[str, list[dict]] = {}

    for lic in raw_licenses:
        ref_key = f"{lic['discipline']}{lic['license_id']}"
        ref_entry = ref.get(ref_key)
        if ref_entry is None:
            continue

        enriched = {
            "name": ref_entry["name"],
            "discipline": ref_entry["discipline"],
            "rank": ref_entry["rank"],
            "issue_date": lic.get("issue_date", ""),
            "expiration_date": lic.get("expiration_date", ""),
            "issuer": lic.get("issuer", ""),
            "id_association": lic.get("id_association", ""),
        }

        discipline_name = ref_entry["discipline"]
        grouped.setdefault(discipline_name, []).append(enriched)

    # Sort each group by rank (ascending: rank 1 = highest)
    for discipline_name in grouped:
        grouped[discipline_name].sort(key=lambda x: x["rank"])

    return grouped
