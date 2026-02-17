#!/usr/bin/env python3
"""
Sync organization summary files from a Google Sheet to data/orgs/<org_slug>/<org_slug>.md
and frontend/public/organizations.md.

Reads organization data via the Google Sheets API and:
- Generates <slug>.md files for each row (structure from data/_league-template.md, hardcoded)
- Generates frontend/public/organizations.md from data/_organizations.md template (Reftown table
  for orgs without Payor League, NWSC table for orgs with Payor League)

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
import json
import re
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SHEET_ID = "1UfzRZQPEhV1mYemzhwSFbi66hJaEbFiMIP6tSEO4c_I"
DEFAULT_GID = 1877948281
ORGS_DIR = PROJECT_ROOT / "data" / "orgs"
BACKEND_DIR = PROJECT_ROOT / "backend"
ORGANIZATIONS_TEMPLATE = PROJECT_ROOT / "data" / "_organizations.md"
ORGANIZATIONS_OUTPUT = PROJECT_ROOT / "frontend" / "public" / "organizations.md"
ORGANIZATIONS_GRAPH_OUTPUT = PROJECT_ROOT / "frontend" / "public" / "organizations-graph.json"

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
    "Competition Type",
    "Competitions",
    "Region",
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


def _normalize_url(url):
    """Return URL with https if missing scheme. Empty string if blank."""
    u = (url or "").strip()
    if not u:
        return ""
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u


def _format_homepage(url):
    """Format homepage URL as [domain](url). Returns empty string if blank."""
    u = _normalize_url(url)
    if not u:
        return ""
    try:
        p = urlparse(u)
        netloc = (p.netloc or "").replace("www.", "")
        if netloc:
            return f"[{netloc}]({u})"
    except Exception:
        pass
    return f"[{u}]({u})"


def _table_cell(s):
    """Sanitize string for markdown table cell (escape pipes)."""
    return (s or "").replace("|", " - ")


def _region_cell(city, state, playing_dates):
    """Build Region cell: 'City, State' with optional playing dates on new line (using <br>)."""
    loc = _location(city, state)
    dates = (playing_dates or "").strip()
    if not loc and not dates:
        return ""
    if not dates:
        return _table_cell(loc)
    if not loc:
        return _table_cell(dates)
    return _table_cell(f"{loc}<br>{dates}")


def _build_reftown_table(rows):
    """Build markdown table for Reftown orgs (no Payor League)."""
    if not rows:
        return "| Organization | In Reftown | League | Contact | Region | Info |\n| :--- | :--- | :--- | :--- | :--- | :--- |"
    lines = [
        "| Organization | In Reftown | League | Contact | Region | Info |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for d in rows:
        org_id = _table_cell(_val(d, "Org ID"))
        org_name_raw = _val(d, "Org Name")
        org_name = _table_cell(org_name_raw)
        league = _table_cell(_val(d, "League"))
        reftown = _val(d, "Reftown Link")
        reftown_org_cell = f"[{org_id}]({reftown})" if reftown else org_id
        homepage_url = _normalize_url(_val(d, "Homepage"))
        org_cell = f"[{org_name}]({homepage_url})" if homepage_url else org_name
        contact = _table_cell(_val(d, "Contact"))
        region = _region_cell(_val(d, "City"), _val(d, "State"), _val(d, "General Playing Dates"))
        info = _table_cell(_val(d, "Info"))
        lines.append(f"| {org_cell} | {reftown_org_cell} | {league} | {contact} | {region} | {info} |")
    return "\n".join(lines)


def _build_nwsc_table(rows):
    """Build markdown table for NWSC payor leagues."""
    if not rows:
        return "| Organization | In Reftown | League | Contact | Region | Info |\n| :--- | :--- | :--- | :--- | :--- | :--- |"
    lines = [
        "| Organization | In Reftown | League | Contact | Region | Info |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for d in rows:
        payor_league = _table_cell(_val(d, "NWSC Payor League"))
        league = _table_cell(_val(d, "League"))
        org_name_raw = _val(d, "Org Name")
        org_name = _table_cell(org_name_raw)
        reftown = _val(d, "Reftown Link")
        reftown_cell = f"[{payor_league}]({reftown})" if reftown else payor_league
        homepage_url = _normalize_url(_val(d, "Homepage"))
        org_cell = f"[{org_name}]({homepage_url})" if homepage_url else org_name
        contact = _table_cell(_val(d, "Contact"))
        region = _region_cell(_val(d, "City"), _val(d, "State"), _val(d, "General Playing Dates"))
        info = _table_cell(_val(d, "Info"))
        lines.append(f"| {org_cell} | {reftown_cell} | {league} | {contact} | {region} | {info} |")
    return "\n".join(lines)


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

    return "\n".join(parts)


def _competition_slug(name):
    """Slugify competition/league name for node id."""
    if not name or not name.strip():
        return ""
    s = name.strip().lower()
    s = s.replace(" ", "-").replace("/", "-")
    s = re.sub(r"[^\w\-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "unnamed"


def _competition_sublist(league_val, competitions_val):
    """Return list of competition names: Competitions column if present, else split League by comma."""
    comp = (competitions_val or "").strip()
    if comp:
        return [p.strip() for p in comp.split(",") if p.strip()]
    league = (league_val or "").strip()
    if not league:
        return []
    return [p.strip() for p in league.split(",") if p.strip()]


def _competition_type(name, override_val):
    """Return 'tournament' or 'league'. Use Competition Type column if present, else infer from Cup suffix."""
    override = (override_val or "").strip().lower()
    if override in ("tournament", "league"):
        return override
    if name and name.strip().lower().endswith("cup"):
        return "tournament"
    return "league"


def _build_graph_json(rows):
    """Build {nodes, edges} for organizations graph from parsed rows. Uses header-based keys only."""
    nodes = []
    edges = []
    node_ids = set()
    competition_nodes = {}  # slug -> node dict

    def add_competition(league_name, override_type=None):
        slug = _competition_slug(league_name)
        if not slug:
            return None
        if slug in competition_nodes:
            return slug
        sub = _competition_type(league_name, override_type)
        competition_nodes[slug] = {
            "id": slug,
            "label": slug,
            "type": "competition",
            "subtype": sub,
            "fullName": league_name.strip(),
        }
        return slug

    reftown_rows = [r for r in rows if not _val(r, "NWSC Payor League")]
    nwsc_rows = [r for r in rows if _val(r, "NWSC Payor League")]

    # Synthetic NWSC parent node
    if nwsc_rows:
        nwsc_node = {
            "id": "NWSC",
            "label": "NWSC",
            "type": "organization",
            "subtype": "nwsc_parent",
            "fullName": "NorthWest Soccer Central",
        }
        region = _val(nwsc_rows[0], "Region") or _location(_val(nwsc_rows[0], "City"), _val(nwsc_rows[0], "State"))
        contact = _val(nwsc_rows[0], "Contact")
        if region:
            nwsc_node["region"] = region
        if contact:
            nwsc_node["contact"] = contact
        nodes.append(nwsc_node)
        node_ids.add("NWSC")

    for d in reftown_rows:
        org_id = _val(d, "Org ID")
        if not org_id or _val(d, "NWSC Payor League"):
            continue
        nid = _slug(org_id)
        if nid in node_ids:
            continue
        node_ids.add(nid)
        full_name = _val(d, "Org Name")
        region = _val(d, "Region") or _location(_val(d, "City"), _val(d, "State"))
        contact = _val(d, "Contact")
        league_val = _val(d, "League")
        competitions_val = _val(d, "Competitions") if "Competitions" in COLUMNS else ""
        comp_list = _competition_sublist(league_val, d.get("Competitions", ""))
        node = {
            "id": nid,
            "label": org_id,
            "type": "organization",
            "subtype": "reftown_top",
            "fullName": full_name or org_id,
        }
        if region:
            node["region"] = region
        if contact:
            node["contact"] = contact
        if league_val:
            node["league"] = league_val
        nodes.append(node)
        override_type = d.get("Competition Type", "")
        for comp_name in comp_list:
            cslug = add_competition(comp_name, override_type)
            if cslug:
                edges.append({"source": nid, "target": cslug, "type": "serves"})

    for d in nwsc_rows:
        payor = _val(d, "NWSC Payor League")
        org_id = _val(d, "Org ID")
        nid = _slug(payor or org_id)
        if nid not in node_ids:
            node_ids.add(nid)
            full_name = _val(d, "Org Name")
            region = _val(d, "Region") or _location(_val(d, "City"), _val(d, "State"))
            contact = _val(d, "Contact")
            league_val = _val(d, "League")
            node = {
                "id": nid,
                "label": payor or org_id,
                "type": "organization",
                "subtype": "nwsc_payor",
                "fullName": full_name or payor or org_id,
            }
            if region:
                node["region"] = region
            if contact:
                node["contact"] = contact
            if league_val:
                node["league"] = league_val
            nodes.append(node)
            edges.append({"source": "NWSC", "target": nid, "type": "parent_of"})
        league_val = _val(d, "League")
        comp_list = _competition_sublist(league_val, d.get("Competitions", ""))
        override_type = d.get("Competition Type", "")
        for comp_name in comp_list:
            cslug = add_competition(comp_name, override_type)
            if cslug:
                edges.append({"source": nid, "target": cslug, "type": "serves"})

    nodes.extend(competition_nodes.values())
    return {"nodes": nodes, "edges": edges}


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
    col_indices = {h: i for i, h in enumerate(headers)}

    rows = []
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
        rows.append(d)

    reftown_rows = [r for r in rows if not _val(r, "NWSC Payor League")]
    nwsc_rows = [r for r in rows if _val(r, "NWSC Payor League")]

    count = 0
    for d in rows:
        org_id = _val(d, "Org ID")
        slug = _slug(org_id)
        signup_type_val = _signup_type(d)
        fm = _build_frontmatter(d, signup_type_val)
        body = _build_body(d, signup_type_val)
        out_path = ORGS_DIR / slug / f"{slug}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        content = _render_yaml(fm) + "\n\n" + body
        out_path.write_text(content, encoding="utf-8")
        count += 1

    template_text = ORGANIZATIONS_TEMPLATE.read_text(encoding="utf-8")
    reftown_table = _build_reftown_table(reftown_rows)
    nwsc_table = _build_nwsc_table(nwsc_rows)
    org_md = template_text.replace("{{REFTOWN_TABLE}}", reftown_table).replace("{{NWSC_TABLE}}", nwsc_table)
    ORGANIZATIONS_OUTPUT.write_text(org_md, encoding="utf-8")

    graph_data = _build_graph_json(rows)
    ORGANIZATIONS_GRAPH_OUTPUT.write_text(json.dumps(graph_data, indent=2), encoding="utf-8")

    print(f"Wrote {count} organization files to {ORGS_DIR}")
    print(f"Wrote {ORGANIZATIONS_OUTPUT}")
    print(f"Wrote {ORGANIZATIONS_GRAPH_OUTPUT}")


if __name__ == "__main__":
    main()
