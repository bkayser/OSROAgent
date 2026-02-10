"""
Service module for interacting with the USSF Learning Center Certification API.
Uses the public API endpoints which require no authentication.
"""

import json
from datetime import date
from pathlib import Path

import httpx

# Public API base URL (no authentication required)
USSF_API_BASE_URL = "https://connect.learning.ussoccer.com/certifications/public"

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


async def lookup_ussf_id(email: str) -> tuple[str | None, str | None]:
    """
    Look up the USSF ID for the given email address.
    Returns tuple of (ussf_id, full_name) or (None, None) if not found.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{USSF_API_BASE_URL}/users",
            params={"email": email},
        )
        if resp.status_code == 404:
            return None, None
        if resp.status_code != 200:
            raise RuntimeError(f"USSF API user lookup failed with status {resp.status_code}")
        
        users = resp.json()
        if not users or len(users) == 0:
            return None, None
        
        # Return the first matching user
        first_user = users[0]
        return first_user.get("ussf_id"), first_user.get("full_name")


async def fetch_active_licenses(ussf_id: str) -> list[dict]:
    """
    Fetch the list of licenses for the given USSF ID.
    Filters to only include non-expired licenses.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{USSF_API_BASE_URL}/users/{ussf_id}/user-licenses",
        )
        if resp.status_code != 200:
            raise RuntimeError(f"USSF API license fetch failed with status {resp.status_code}")
        
        licenses = resp.json()
        today = date.today().isoformat()
        
        # Filter out expired licenses
        active_licenses = []
        for lic in licenses:
            exp_date = lic.get("expiration_date")
            # Include if no expiration or expiration is in the future
            if exp_date is None or exp_date >= today:
                active_licenses.append(lic)
        
        return active_licenses


def _calculate_status(expiration_date: str | None) -> str:
    """
    Calculate the status of a license based on its expiration date.
    Returns: 'active', 'expiring_soon', 'critical', or 'expired'
    
    - expired: already expired
    - critical: expires within 2 weeks (14 days)
    - expiring_soon: expires within 3 months (90 days)
    - active: more than 3 months until expiration or no expiration
    """
    if expiration_date is None:
        return "active"
    
    from datetime import datetime, timedelta
    
    try:
        exp = datetime.strptime(expiration_date, "%Y-%m-%d").date()
        today = date.today()
        
        if exp < today:
            return "expired"
        elif exp <= today + timedelta(days=14):
            return "critical"
        elif exp <= today + timedelta(days=90):
            return "expiring_soon"
        else:
            return "active"
    except ValueError:
        return "active"


def enrich_and_group_licenses(raw_licenses: list[dict]) -> dict:
    """
    Enrich raw license records with reference data and group them by discipline.

    Each license is enriched with name, discipline, rank, status, and pathway from
    the reference table using the concatenated discipline + license_id key.
    Licenses within each group are ordered by rank (ascending = higher rank first).
    """
    ref = get_license_reference()
    grouped: dict[str, list[dict]] = {}

    for lic in raw_licenses:
        ref_key = f"{lic['discipline']}_{lic['license_id']}"
        ref_entry = ref.get(ref_key)
        if ref_entry is None:
            continue

        exp_date = lic.get("expiration_date")
        
        enriched = {
            "id": f"{lic['discipline']}_{lic['license_id']}",
            "name": ref_entry["name"],
            "discipline": ref_entry["discipline"],
            "rank": ref_entry["rank"],
            "issue_date": lic.get("issue_date", ""),
            "expiration_date": exp_date or "",
            "issuer": lic.get("issuer", ""),
            "status": _calculate_status(exp_date),
        }

        discipline_name = ref_entry["discipline"]
        grouped.setdefault(discipline_name, []).append(enriched)

    # Sort each group by rank (ascending: rank 1 = highest)
    for discipline_name in grouped:
        grouped[discipline_name].sort(key=lambda x: x["rank"])

    return grouped
