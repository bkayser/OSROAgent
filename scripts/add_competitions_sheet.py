#!/usr/bin/env python3
"""
One-time script: create a "Competitions" worksheet in the organizations Google Sheet
and populate it with competition data derived from the Master sheet.

After running, populate Rules URL, Level, and Info by hand and tune Tokens and Type.
Future sync_orgs runs will read the Competitions sheet.

Usage:
  python scripts/add_competitions_sheet.py
  python scripts/add_competitions_sheet.py --sheet-id OTHER_SHEET_ID --gid 1234567890
"""

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
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


def _competition_slug(name: str) -> str:
    """Slugify competition/league name."""
    if not name or not name.strip():
        return ""
    s = name.strip().lower()
    s = s.replace(" ", "-").replace("/", "-")
    import re
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


def _competition_type(name: str, override_val: str) -> str:
    """Return 'tournament' or 'league'."""
    override = (override_val or "").strip().lower()
    if override in ("tournament", "league"):
        return override
    if name and name.strip().lower().endswith("cup"):
        return "tournament"
    return "league"


def _default_competition_tokens(slug: str) -> list[str]:
    """Compute default tokens for a competition slug."""
    tokens = [slug]
    spaced = slug.replace("-", " ")
    if spaced != slug:
        tokens.append(spaced)
    if "-" in slug:
        first = slug.split("-", 1)[0]
        if first and first not in tokens:
            tokens.append(first)
    return tokens


def main():
    parser = argparse.ArgumentParser(
        description="Create and populate 'Competitions' worksheet from Master sheet data"
    )
    parser.add_argument(
        "--sheet-id", default=DEFAULT_SHEET_ID,
        help=f"Google Sheet ID (default: {DEFAULT_SHEET_ID})",
    )
    parser.add_argument(
        "--gid", type=int, default=DEFAULT_GID,
        help=f"Master worksheet GID (default: {DEFAULT_GID})",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite Competitions worksheet if it already has data",
    )
    args = parser.parse_args()

    client = _get_sheet_client()
    spreadsheet = client.open_by_key(args.sheet_id)
    worksheet = spreadsheet.get_worksheet_by_id(args.gid)

    all_values = worksheet.get_all_values()
    if not all_values:
        raise SystemExit("Master sheet is empty")

    headers = [c.strip() for c in all_values[0]]
    col_indices = {h: i for i, h in enumerate(headers)}

    comp_name_to_slug = {}
    comp_name_to_type = {}
    for row_data in all_values[1:]:
        league_val = (row_data[col_indices.get("League", -1)] or "").strip() if "League" in col_indices else ""
        competitions_val = (row_data[col_indices.get("Competitions", -1)] or "").strip() if "Competitions" in col_indices else ""
        override_type = (row_data[col_indices.get("Competition Type", -1)] or "").strip() if "Competition Type" in col_indices else ""
        for comp_name in _competition_sublist(league_val, competitions_val):
            slug = _competition_slug(comp_name)
            if slug:
                comp_name_to_slug[comp_name] = slug
                comp_name_to_type[comp_name] = _competition_type(comp_name, override_type)

    competitions = []
    for comp_name, slug in sorted(comp_name_to_slug.items(), key=lambda x: x[1]):
        comp_type = comp_name_to_type.get(comp_name, "league")
        tokens = _default_competition_tokens(slug)
        competitions.append({
            "Competition ID": slug,
            "Full Name": comp_name,
            "Tokens": ", ".join(tokens),
            "Type": comp_type.capitalize(),
            "Level": "",
            "Rules URL": "",
            "Info": "",
        })

    try:
        from gspread.exceptions import WorksheetNotFound
        comp_worksheet = spreadsheet.worksheet("Competitions")
        existing = comp_worksheet.get_all_values()
        if existing and len(existing) > 1 and not args.force:
            print("Competitions worksheet already exists with data. Use --force to overwrite.")
            return
        print("Competitions worksheet exists but is empty. Populating...")
    except WorksheetNotFound:
        comp_worksheet = spreadsheet.add_worksheet(title="Competitions", rows=len(competitions) + 10, cols=len(COMPETITION_COLUMNS))
        print("Created Competitions worksheet.")

    comp_worksheet.clear()
    comp_worksheet.append_row(COMPETITION_COLUMNS, value_input_option="USER_ENTERED")
    for d in competitions:
        row = [d.get(col, "") for col in COMPETITION_COLUMNS]
        comp_worksheet.append_row(row, value_input_option="USER_ENTERED")

    print(f"Populated {len(competitions)} competitions.")
    for c in competitions[:10]:
        print(f"  {c['Competition ID']}: {c['Full Name']} ({c['Type']})")
    if len(competitions) > 10:
        print(f"  ... and {len(competitions) - 10} more")


if __name__ == "__main__":
    main()
