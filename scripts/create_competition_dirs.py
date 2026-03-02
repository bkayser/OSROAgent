#!/usr/bin/env python3
"""
One-time script: create data/competitions/<comp_id>/ for each competition
listed in the Competitions tab of the spreadsheet.

Uses Competition ID as the directory name. If the Competitions sheet does not
exist, derives competition IDs from the Master sheet (League/Competitions columns).

Usage:
  python scripts/create_competition_dirs.py
  python scripts/create_competition_dirs.py --sheet-id OTHER_SHEET_ID --gid 1234567890
"""

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
COMPETITIONS_DIR = PROJECT_ROOT / "data" / "competitions"
DEFAULT_SHEET_ID = "1UfzRZQPEhV1mYemzhwSFbi66hJaEbFiMIP6tSEO4c_I"
DEFAULT_GID = 1877948281

COMPETITION_COLUMNS = [
    "Competition ID",
    "Full Name",
    "Tokens",
    "Type",
    "Level",
    "Rules URL",
    "Info",
]


def _get_sheet_client():
    """Return gspread client using backend service account credentials."""
    creds_path = None
    for f in BACKEND_DIR.glob("oregon-referees*.json"):
        if f.is_file():
            creds_path = f
            break
    if not creds_path or not creds_path.exists():
        raise SystemExit("No service account credentials found in backend/ (oregon-referees*.json)")
    import gspread
    return gspread.service_account(filename=str(creds_path))


def _val(d, key):
    """Get trimmed non-empty value or empty string."""
    return (d.get(key) or "").strip()


def _competition_slug(name: str) -> str:
    """Slugify competition/league name."""
    if not name or not name.strip():
        return ""
    import re
    s = name.strip().lower()
    s = s.replace(" ", "-").replace("/", "-")
    s = re.sub(r"[^\w\-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "unnamed"


def _competition_sublist(league_val: str, competitions_val: str) -> list[str]:
    """Return list of competition names from League or Competitions column."""
    comp = (competitions_val or "").strip()
    if comp:
        return [p.strip() for p in comp.split(",") if p.strip()]
    league = (league_val or "").strip()
    if not league:
        return []
    return [p.strip() for p in league.split(",") if p.strip()]


def _get_competition_ids(spreadsheet, args) -> set[str]:
    """Return set of competition IDs from Competitions sheet or Master sheet."""
    comp_ids = set()

    try:
        from gspread.exceptions import WorksheetNotFound
        comp_worksheet = spreadsheet.worksheet("Competitions")
        comp_values = comp_worksheet.get_all_values()
        if comp_values:
            comp_headers = [c.strip() for c in comp_values[0]]
            comp_col_indices = {h: i for i, h in enumerate(comp_headers)}
            comp_id_idx = comp_col_indices.get("Competition ID", -1)
            if comp_id_idx >= 0:
                for row_data in comp_values[1:]:
                    if comp_id_idx < len(row_data):
                        comp_id = (row_data[comp_id_idx] or "").strip()
                        if comp_id:
                            slug = _competition_slug(comp_id) or comp_id
                            comp_ids.add(slug)
                if comp_ids:
                    return comp_ids
    except WorksheetNotFound:
        pass

    # Fallback: derive from Master sheet
    worksheet = spreadsheet.get_worksheet_by_id(args.gid)
    all_values = worksheet.get_all_values()
    if not all_values:
        return comp_ids

    headers = [c.strip() for c in all_values[0]]
    col_indices = {h: i for i, h in enumerate(headers)}
    league_idx = col_indices.get("League", -1)
    comp_idx = col_indices.get("Competitions", -1)

    for row_data in all_values[1:]:
        league_val = (row_data[league_idx] or "").strip() if league_idx >= 0 else ""
        comp_val = (row_data[comp_idx] or "").strip() if comp_idx >= 0 else ""
        for comp_name in _competition_sublist(league_val, comp_val):
            slug = _competition_slug(comp_name)
            if slug:
                comp_ids.add(slug)

    return comp_ids


def main():
    parser = argparse.ArgumentParser(
        description="Create data/competitions/<comp_id>/ for each competition in the spreadsheet"
    )
    parser.add_argument(
        "--sheet-id", default=DEFAULT_SHEET_ID,
        help=f"Google Sheet ID (default: {DEFAULT_SHEET_ID})",
    )
    parser.add_argument(
        "--gid", type=int, default=DEFAULT_GID,
        help=f"Master worksheet GID (default: {DEFAULT_GID})",
    )
    args = parser.parse_args()

    client = _get_sheet_client()
    spreadsheet = client.open_by_key(args.sheet_id)
    comp_ids = _get_competition_ids(spreadsheet, args)

    if not comp_ids:
        print("No competitions found.")
        return

    COMPETITIONS_DIR.mkdir(parents=True, exist_ok=True)
    created = []
    for comp_id in sorted(comp_ids):
        dir_path = COMPETITIONS_DIR / comp_id
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            created.append(comp_id)

    print(f"Competitions directory: {COMPETITIONS_DIR}")
    print(f"Total competitions: {len(comp_ids)}")
    if created:
        print(f"Created {len(created)} new directories:")
        for c in created:
            print(f"  {c}")
    else:
        print("All competition directories already exist.")


if __name__ == "__main__":
    main()
