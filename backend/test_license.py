"""
Tests for the license-status API endpoint and license_service module.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.license_service import (
    enrich_and_group_licenses,
    get_license_reference,
    load_license_reference,
)
from backend.main import app

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# license_data.json loading
# ---------------------------------------------------------------------------

def test_license_data_file_exists():
    """The license_data.json file should exist in the backend directory."""
    path = Path(__file__).parent / "license_data.json"
    assert path.exists()


def test_load_license_reference():
    """load_license_reference should populate the global reference dict."""
    load_license_reference()
    ref = get_license_reference()
    assert isinstance(ref, dict)
    assert len(ref) > 0
    # Spot-check a few keys
    assert "referee_1" in ref
    assert ref["referee_1"]["name"] == "Grassroots Referee"
    assert ref["futsal_3"]["discipline"] == "Futsal"


# ---------------------------------------------------------------------------
# enrich_and_group_licenses
# ---------------------------------------------------------------------------

def test_enrich_and_group_empty():
    """An empty list of raw licenses should return an empty dict."""
    load_license_reference()
    assert enrich_and_group_licenses([]) == {}


def test_enrich_and_group_single_license():
    """A single license should come back in the correct group."""
    load_license_reference()
    raw = [
        {
            "license_id": "1",
            "discipline": "referee",
            "status": "active",
            "issue_date": "2024-01-15",
            "expiration_date": "2025-01-15",
            "issuer": "US Soccer",
            "id_association": "OSSR",
        }
    ]
    result = enrich_and_group_licenses(raw)
    assert "Referee" in result
    assert len(result["Referee"]) == 1
    lic = result["Referee"][0]
    assert lic["id"] == "referee_1"
    assert lic["name"] == "Grassroots Referee"
    assert lic["discipline"] == "Referee"
    assert lic["rank"] == 8
    assert lic["issue_date"] == "2024-01-15"
    assert lic["issuer"] == "US Soccer"


def test_enrich_and_group_multiple_sorted_by_rank():
    """Licenses within a group should be sorted by rank ascending (best first)."""
    load_license_reference()
    raw = [
        {"license_id": "1", "discipline": "referee", "status": "active",
         "issue_date": "2024-01-01", "expiration_date": "2025-01-01",
         "issuer": "US Soccer", "id_association": "OSSR"},
        {"license_id": "5", "discipline": "referee", "status": "active",
         "issue_date": "2024-06-01", "expiration_date": "2025-06-01",
         "issuer": "US Soccer", "id_association": "OSSR"},
    ]
    result = enrich_and_group_licenses(raw)
    ranks = [lic["rank"] for lic in result["Referee"]]
    assert ranks == sorted(ranks)


def test_enrich_and_group_multiple_disciplines():
    """Licenses from different disciplines should appear in separate groups."""
    load_license_reference()
    raw = [
        {"license_id": "1", "discipline": "referee", "status": "active",
         "issue_date": "2024-01-01", "expiration_date": "2025-01-01",
         "issuer": "US Soccer", "id_association": "OSSR"},
        {"license_id": "2", "discipline": "futsal", "status": "active",
         "issue_date": "2024-06-01", "expiration_date": "2025-06-01",
         "issuer": "US Soccer", "id_association": "OSSR"},
    ]
    result = enrich_and_group_licenses(raw)
    assert "Referee" in result
    assert "Futsal" in result


def test_enrich_and_group_unknown_key_skipped():
    """A license with an unknown discipline+license_id combo should be skipped."""
    load_license_reference()
    raw = [
        {"license_id": "99", "discipline": "unknown", "status": "active",
         "issue_date": "2024-01-01", "expiration_date": "2025-01-01",
         "issuer": "X", "id_association": "Y"},
    ]
    result = enrich_and_group_licenses(raw)
    assert result == {}


# ---------------------------------------------------------------------------
# /license-status endpoint
# ---------------------------------------------------------------------------

def test_license_status_missing_email():
    """Should return 400 when no email is provided."""
    resp = client.get("/license-status")
    assert resp.status_code == 400


def test_license_status_empty_email():
    """Should return 400 when email param is blank."""
    resp = client.get("/license-status", params={"email": "  "})
    assert resp.status_code == 400


@patch("backend.license_service.lookup_ussf_id", new_callable=AsyncMock, return_value=None)
def test_license_status_email_not_found(mock_lookup):
    """Should return 404 when no USSF ID is associated with the email."""
    resp = client.get("/license-status", params={"email": "nobody@example.com"})
    assert resp.status_code == 404
    assert "No USSF ID found" in resp.json()["detail"]


@patch("backend.license_service.lookup_ussf_id", new_callable=AsyncMock,
       side_effect=RuntimeError("USSF API login failed with status 401"))
def test_license_status_api_error_on_lookup(mock_lookup):
    """Should return 500 when the USSF API returns an error during lookup."""
    resp = client.get("/license-status", params={"email": "test@example.com"})
    assert resp.status_code == 500
    assert "USSF API" in resp.json()["detail"]


@patch("backend.license_service.fetch_active_licenses", new_callable=AsyncMock,
       side_effect=RuntimeError("USSF API license fetch failed with status 500"))
@patch("backend.license_service.lookup_ussf_id", new_callable=AsyncMock,
       return_value="1234567890123456")
def test_license_status_api_error_on_fetch(mock_lookup, mock_fetch):
    """Should return 500 when fetching licenses fails."""
    resp = client.get("/license-status", params={"email": "test@example.com"})
    assert resp.status_code == 500
    assert "USSF API" in resp.json()["detail"]


@patch("backend.license_service.fetch_active_licenses", new_callable=AsyncMock, return_value=[
    {"license_id": "1", "discipline": "referee", "status": "active",
     "issue_date": "2024-01-15", "expiration_date": "2025-01-15",
     "issuer": "US Soccer", "id_association": "OSSR"},
    {"license_id": "1", "discipline": "futsal", "status": "active",
     "issue_date": "2024-03-01", "expiration_date": "2025-03-01",
     "issuer": "US Soccer", "id_association": "OSSR"},
])
@patch("backend.license_service.lookup_ussf_id", new_callable=AsyncMock,
       return_value="1234567890123456")
def test_license_status_success(mock_lookup, mock_fetch):
    """Should return grouped licenses on success."""
    resp = client.get("/license-status", params={"email": "ref@example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Referee" in data
    assert "Futsal" in data
    ref_lic = data["Referee"][0]
    assert ref_lic["id"] == "referee_1"
    assert ref_lic["name"] == "Grassroots Referee"
    assert ref_lic["discipline"] == "Referee"
    assert ref_lic["rank"] == 8
