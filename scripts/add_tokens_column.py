#!/usr/bin/env python3
"""
One-time script: add a "Tokens" column to the organizations Google Sheet
and populate it with default token values derived from each org's slug.

After running, edit the Tokens column in the sheet to tune matching;
sync_orgs will read those values on future runs.

Usage:
  python scripts/add_tokens_column.py
  python scripts/add_tokens_column.py --sheet-id OTHER_SHEET_ID --gid 1234567890
"""

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
DEFAULT_SHEET_ID = "1UfzRZQPEhV1mYemzhwSFbi66hJaEbFiMIP6tSEO4c_I"
DEFAULT_GID = 1877948281

TOKENS_HEADER = "Tokens"


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


def _slug(org_id: str) -> str:
    return org_id.strip().replace(" ", "_")


def _default_tokens(slug: str) -> list[str]:
    """Compute default tokens: slug as-is, slug with _ replaced by space,
    and first segment before _ or - if present."""
    tokens = [slug]
    spaced = slug.replace("_", " ")
    if spaced != slug:
        tokens.append(spaced)
    for sep in ("_", "-"):
        if sep in slug:
            first = slug.split(sep, 1)[0]
            if first and first not in tokens:
                tokens.append(first)
            break
    return tokens


def main():
    parser = argparse.ArgumentParser(
        description="Add and populate 'Tokens' column in the organizations Google Sheet"
    )
    parser.add_argument(
        "--sheet-id", default=DEFAULT_SHEET_ID,
        help=f"Google Sheet ID (default: {DEFAULT_SHEET_ID})",
    )
    parser.add_argument(
        "--gid", type=int, default=DEFAULT_GID,
        help=f"Worksheet GID (default: {DEFAULT_GID})",
    )
    args = parser.parse_args()

    client = _get_sheet_client()
    spreadsheet = client.open_by_key(args.sheet_id)
    worksheet = spreadsheet.get_worksheet_by_id(args.gid)

    all_values = worksheet.get_all_values()
    if not all_values:
        raise SystemExit("Sheet is empty")

    headers = [c.strip() for c in all_values[0]]

    if TOKENS_HEADER in headers:
        tokens_col = headers.index(TOKENS_HEADER) + 1
        print(f"'{TOKENS_HEADER}' column already exists at column {tokens_col}")
    else:
        tokens_col = len(headers) + 1
        worksheet.update_cell(1, tokens_col, TOKENS_HEADER)
        print(f"Added '{TOKENS_HEADER}' header at column {tokens_col}")

    try:
        org_id_col = headers.index("Org ID") + 1
    except ValueError:
        raise SystemExit("'Org ID' column not found in the sheet")

    updated = 0
    for row_idx, row_data in enumerate(all_values[1:], start=2):
        org_id_val = (row_data[org_id_col - 1] if org_id_col - 1 < len(row_data) else "").strip()
        if not org_id_val:
            continue

        existing_tokens = ""
        if tokens_col - 1 < len(row_data):
            existing_tokens = (row_data[tokens_col - 1] or "").strip()

        if existing_tokens:
            continue

        slug = _slug(org_id_val)
        tokens = _default_tokens(slug)
        cell_value = ", ".join(tokens)
        worksheet.update_cell(row_idx, tokens_col, cell_value)
        updated += 1
        print(f"  Row {row_idx}: {org_id_val} -> {cell_value}")

    print(f"Done. Populated {updated} rows with default tokens.")


if __name__ == "__main__":
    main()
