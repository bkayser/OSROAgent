#!/usr/bin/env python3
"""
Sync organization summary files from a Google Sheet to data/orgs/<org_slug>/<org_slug>.md.

Reads organization data via the Google Sheets API and generates <slug>.md files for each
row, using the structure defined in data/_league-template.md (the template is not read
at runtime—structure is hardcoded).

Expected sheet columns (in order):
  Org ID, Reftown Link, Reftown ID, NWSC Payor League, Org Name, Contact, Email,
  Phone, League, Rules URL, Pay URL, Homepage, City, State, General Playing Dates, Info

Requirements:
  - Service account credentials (backend/oregon-referees*.json)
  - The spreadsheet must be shared with the service account email

Usage:
  python scripts/sync_orgs.py
  python scripts/sync_orgs.py --sheet-id OTHER_SHEET_ID --gid 1234567890
"""

import argparse
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SHEET_ID = "1UfzRZQPEhV1mYemzhwSFbi66hJaEbFiMIP6tSEO4c_I"
DEFAULT_GID = 1877948281
ORGS_DIR = PROJECT_ROOT / "data" / "orgs"
BACKEND_DIR = PROJECT_ROOT / "backend"

COLUMNS = [
    "Org ID",
    "Reftown Link",
    "Reftown ID",
    "NWSC Payor League",
    "Org Name",
    "Contact",
    "Email",
    "Phone",
    "League",
    "Rules URL",
    "Pay URL",
    "Homepage",
    "City",
    "State",
    "General Playing Dates",
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
    v = (d.get(key) or "").strip()
    return v


def _slug(org_id):
    """Normalize Org ID to directory slug (spaces -> underscores)."""
    return _val({"k": org_id}, "k").replace(" ", "_")


def _signup_type(d):
    """Derive signup_type from row."""
    if _val(d, "NWSC Payor League"):
        return "nwsc_payor"
    if _val(d, "Reftown Link"):
        return "reftown_top"
    return "external_assigning"


def _location(city, state):
    """Format location: State always present; city may be blank. No orphan comma."""
    s = (state or "").strip()
    c = (city or "").strip()
    if c:
        return f"{c}, {s}"
    return s


def _build_frontmatter(d, signup_type_val):
    """Build YAML frontmatter dict with only non-blank keys."""
    org_id = _val(d, "Org ID")
    org_name = _val(d, "Org Name")
    fm = {}

    if org_name:
        fm["title"] = f"{org_name} - Referee Information"
    reftown = _val(d, "Reftown Link")
    if reftown:
        fm["source"] = reftown

    if org_id:
        fm["org_slug"] = _slug(org_id)
    if org_name:
        fm["org_name_full"] = org_name
    if reftown:
        fm["reftown_link"] = reftown
    nwsc = _val(d, "NWSC Payor League")
    if nwsc:
        fm["nwsc_payor_league"] = nwsc
    fm["signup_type"] = signup_type_val
    league = _val(d, "League")
    if league:
        fm["league"] = league
    city = _val(d, "City")
    if city:
        fm["city"] = city
    rules = _val(d, "Rules URL")
    if rules:
        fm["rules"] = rules
    pay = _val(d, "Pay URL")
    if pay:
        fm["pay"] = pay
    state = _val(d, "State")
    if state:
        fm["state"] = state
    dates = _val(d, "General Playing Dates")
    if dates:
        fm["general_playing_dates"] = dates

    return fm


def _yaml_escape(s):
    """Escape string for YAML double-quoted value."""
    s = str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return s


def _render_yaml(fm):
    """Emit YAML frontmatter string (only non-blank keys)."""
    lines = ["---"]
    for k, v in fm.items():
        if v is not None and str(v).strip():
            lines.append(f'{k}: "{_yaml_escape(v)}"')
    lines.append("---")
    return "\n".join(lines)


def _build_body(d, signup_type_val):
    """Build markdown body sections."""
    parts = []
    org_id = _val(d, "Org ID")
    org_name = _val(d, "Org Name")
    league = _val(d, "League")
    homepage = _val(d, "Homepage")
    city = _val(d, "City")
    state = _val(d, "State")
    dates = _val(d, "General Playing Dates")
    reftown = _val(d, "Reftown Link")
    nwsc = _val(d, "NWSC Payor League")
    contact = _val(d, "Contact")
    email = _val(d, "Email")
    phone = _val(d, "Phone")
    rules = _val(d, "Rules URL")
    pay = _val(d, "Pay URL")
    info = _val(d, "Info")

    # Identity and links
    has_identity = any([org_id, org_name, league, homepage, state, dates])
    if has_identity:
        id_lines = [f"# {org_name or org_id}: Referee Information", "", "## Identity and links", ""]
        if org_id:
            id_lines.append(f"- **Org (code):** {org_id}")
        if org_name:
            id_lines.append(f"- **Full name:** {org_name}")
        if league:
            id_lines.append(f"- **League(s):** {league}")
        if homepage:
            id_lines.append(f"- **Homepage:** {homepage}")
        if state:
            id_lines.append(f"- **Location:** {_location(city, state)}")
        if dates:
            id_lines.append(f"- **General playing dates:** {dates}")
        id_lines.append("")
        parts.append("\n".join(id_lines))

    # How to sign up
    signup_lines = ["## How to sign up for games", ""]
    if signup_type_val == "reftown_top":
        signup_lines.extend([
            "Join this organization in RefTown to get assignments and set availability.",
            "",
            f"- **RefTown link:** {reftown}",
            f"- **Steps:** Register or log in at RefTown, join \"{org_name or org_id}\" using the link above, set your availability, and accept assignments as offered.",
        ])
    elif signup_type_val == "nwsc_payor":
        signup_lines.extend([
            "Referees are assigned through NorthWest Soccer Central (NWSC). Registering for NWSC in RefTown covers all NWSC payor leagues.",
            "",
            "- **RefTown link:** Use the NWSC organization in RefTown (https://reftown.com/default.asp?Assoc=NWSC--555).",
            f"- **Steps:** Join NWSC in RefTown using this link: https://reftown.com/registration.asp?RegType=Official&AssocRID=555&Existing=-1, then from your profile request to join the payor league \"{nwsc}\". Set availability for assignments and look for games to request from the main page.",
        ])
    else:
        signup_lines.extend([
            "Referees for this organization are assigned through a separate assigning platform, not via RefTown or NWSC payor leagues.",
            "",
            "- **Steps:** Contact the assignor or organization (see below) for instructions on how to register and receive assignments.",
        ])
    signup_lines.append("")
    parts.append("\n".join(signup_lines))

    # Assignor and contact
    if contact or email or phone:
        ac_lines = ["## Assignor and contact", ""]
        if contact:
            ac_lines.append(f"- **Contact:** {contact}")
        if email:
            ac_lines.append(f"- **Email:** {email}")
        if phone:
            ac_lines.append(f"- **Phone:** {phone}")
        ac_lines.append("")
        parts.append("\n".join(ac_lines))

    # Game day section omitted (no referee hotline / game day hotline columns)

    # Pay table (only if Pay URL present)
    if pay:
        pay_lines = ["### Pay table", "", f"- **Pay:** {pay}", ""]
        parts.append("\n".join(pay_lines))

    # Rules of competition
    if rules:
        rules_lines = ["## Rules of competition", "", f"- **Rules:** {rules}", ""]
        parts.append("\n".join(rules_lines))

    # Additional info
    if info:
        info_lines = ["## Additional info", "", info, ""]
        parts.append("\n".join(info_lines))

    # Footer
    today = date.today().strftime("%Y-%m-%d")
    parts.append(f"---\n\n*Last updated: {today}*")

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Sync organization summaries from Google Sheet to data/orgs/<org_slug>/ORG.md"
    )
    parser.add_argument(
        "--sheet-id",
        default=DEFAULT_SHEET_ID,
        help=f"Google Sheet ID (default: {DEFAULT_SHEET_ID})",
    )
    parser.add_argument(
        "--gid",
        type=int,
        default=DEFAULT_GID,
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
    # Map expected column names to sheet indices (match by header)
    col_indices = {}
    for i, h in enumerate(headers):
        if h in COLUMNS:
            col_indices[h] = i
    # Fallback: if sheet order matches COLUMNS, use position
    for j, col in enumerate(COLUMNS):
        if col not in col_indices and j < len(headers):
            col_indices[col] = j

    count = 0
    for row_data in all_values[1:]:
        d = {}
        for col in COLUMNS:
            idx = col_indices.get(col, -1)
            if idx >= 0 and idx < len(row_data):
                d[col] = (row_data[idx] or "").strip()
            else:
                d[col] = ""

        org_id = _val(d, "Org ID")
        if not org_id:
            continue

        slug = _slug(org_id)
        signup_type_val = _signup_type(d)

        fm = _build_frontmatter(d, signup_type_val)
        body = _build_body(d, signup_type_val)

        out_path = ORGS_DIR / slug / f"{slug}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        content = _render_yaml(fm) + "\n\n" + body
        out_path.write_text(content, encoding="utf-8")
        count += 1

    print(f"Wrote {count} organization files to {ORGS_DIR}")


if __name__ == "__main__":
    main()
