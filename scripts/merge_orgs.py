#!/usr/bin/env python3
"""Merge OSRO Orgs.csv with directory.md to create combined organizations CSV."""

import csv
import re
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OSRO_ORGS = PROJECT_ROOT / "data" / "OSRO Orgs.csv"
DIRECTORY_MD = PROJECT_ROOT / "data" / "directory.md"
OUTPUT_CSV = PROJECT_ROOT / "data" / "organizations_combined.csv"


def clean_md_cell(text):
    """Extract URL from [text](url) or return text as-is."""
    text = (text or "").strip()
    match = re.search(r'\[([^\]]*)\]\((https?://[^\)]+)\)', text)
    if match:
        return match.group(2)
    match = re.search(r'\]\((https?://[^\)]+)\)', text)
    if match:
        return match.group(1)
    return text


def extract_reftown_id(link):
    """Extract numeric ID from Reftown link."""
    if not link:
        return ""
    match = re.search(r'Assoc=(?:[^=]*--)?(\d+)', link)
    if match:
        return match.group(1)
    return ""


def parse_md_table_row(line):
    """Parse a markdown table row, handling pipes and brackets."""
    cells = []
    current = []
    in_bracket = 0
    for char in line:
        if char == '[':
            in_bracket += 1
            current.append(char)
        elif char == ']':
            in_bracket -= 1
            current.append(char)
        elif char == '|' and in_bracket == 0:
            cells.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        cells.append(''.join(current).strip())
    return cells


def parse_directory_md():
    """Parse directory.md and extract both tables."""
    content = DIRECTORY_MD.read_text(encoding="utf-8")
    lines = content.split("\n")

    reftown_orgs = {}
    nwsc_leagues = {}

    i = 0
    while i < len(lines):
        line = lines[i]
        if "| Reftown Org Name | Full Name |" in line:
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = parse_md_table_row(lines[i])
                if len(row) >= 12:
                    short_name = row[1].replace("**", "").strip()
                    if short_name:
                        reftown_orgs[short_name] = {
                            "full_name": row[2].replace("**", "").strip(),
                            "league": row[3].strip(),
                            "reftown_link": clean_md_cell(row[4]),
                            "homepage": clean_md_cell(row[5]),
                            "contact": row[6].strip(),
                            "phone": row[7].strip(),
                            "city": row[8].strip(),
                            "state": row[9].strip(),
                            "playing_dates": row[10].strip(),
                            "info": row[11].strip() if len(row) > 11 else "",
                        }
                i += 1
            continue

        if "| NWSC Org | Payor League |" in line:
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = parse_md_table_row(lines[i])
                if len(row) >= 13:
                    short_name = row[1].replace("**", "").strip()
                    if short_name:
                        nwsc_leagues[short_name] = {
                            "payor_league": row[2].replace("**", "").strip(),
                            "full_name": row[4].replace("**", "").strip(),
                            "league": row[5].strip() if len(row) > 5 else "",
                            "reftown_link": clean_md_cell(row[6]),
                            "homepage": clean_md_cell(row[7]),
                            "contact": row[8].strip(),
                            "phone": row[9].strip(),
                            "city": row[10].strip(),
                            "state": row[11].strip(),
                            "playing_dates": row[12].strip() if len(row) > 12 else "",
                            "info": row[13].strip() if len(row) > 13 else "",
                        }
                i += 1
            continue

        i += 1

    return reftown_orgs, nwsc_leagues


def load_osro_orgs():
    """Load OSRO Orgs.csv."""
    rows = []
    with open(OSRO_ORGS, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            if len(row) >= 10:
                rows.append({
                    "Org Name": row[0],
                    "Full Name": row[3],
                    "Assignor": row[5],
                    "Email": row[6],
                    "Phone": row[7],
                    "League": row[8],
                    "Homepage": row[9] if len(row) > 9 else "",
                })
    return rows


def main():
    reftown_orgs, nwsc_leagues = parse_directory_md()
    osro_rows = load_osro_orgs()

    nwsc_to_canonical = {"OYSA Leagues": "OYSA"}

    all_short_names = set()
    osro_by_name = {}
    for row in osro_rows:
        short = (row.get("Org Name") or "").strip()
        if short:
            all_short_names.add(short)
            osro_by_name[short] = row

    for short in reftown_orgs:
        all_short_names.add(short)
    for short in nwsc_leagues:
        canon = nwsc_to_canonical.get(short, short)
        all_short_names.add(canon)

    output_rows = []
    for short_name in sorted(all_short_names):
        osro = osro_by_name.get(short_name)
        dir_data = reftown_orgs.get(short_name)
        nwsc = nwsc_leagues.get(short_name)
        if not nwsc:
            for nwsc_name, canon in nwsc_to_canonical.items():
                if canon == short_name:
                    nwsc = nwsc_leagues.get(nwsc_name)
                    break

        reftown_link = (dir_data or {}).get("reftown_link", "") or (nwsc or {}).get("reftown_link", "")
        reftown_id = extract_reftown_id(reftown_link)
        nwsc_payor = (nwsc or {}).get("payor_league", "")

        full_name = (dir_data or {}).get("full_name", "") or (osro or {}).get("Full Name", "")
        contact = (osro or {}).get("Assignor", "") or (dir_data or {}).get("contact", "") or (nwsc or {}).get("contact", "")
        email = (osro or {}).get("Email", "")
        phone = (osro or {}).get("Phone", "") or (dir_data or {}).get("phone", "") or (nwsc or {}).get("phone", "")
        league = (osro or {}).get("League", "") or (dir_data or {}).get("league", "") or (nwsc or {}).get("league", "")
        homepage = (osro or {}).get("Homepage", "") or (dir_data or {}).get("homepage", "") or (nwsc or {}).get("homepage", "")
        city = (dir_data or {}).get("city", "") or (nwsc or {}).get("city", "")
        state = (dir_data or {}).get("state", "") or (nwsc or {}).get("state", "") or "OR"
        playing_dates = (dir_data or {}).get("playing_dates", "") or (nwsc or {}).get("playing_dates", "")
        info = (dir_data or {}).get("info", "") or (nwsc or {}).get("info", "")

        output_rows.append({
            "Org Name": short_name,
            "Reftown Link": reftown_link,
            "Reftown ID": reftown_id,
            "NWSC Payor League": nwsc_payor,
            "Full Name": full_name,
            "Contact": contact,
            "Email": email,
            "Phone": phone,
            "League": league,
            "Homepage": homepage,
            "City": city,
            "State": state,
            "General Playing Dates": playing_dates,
            "Info": info,
        })

    headers = [
        "Org Name", "Reftown Link", "Reftown ID", "NWSC Payor League",
        "Org Name", "Contact", "Email", "Phone", "League", "Homepage",
        "City", "State", "General Playing Dates", "Info"
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in output_rows:
            writer.writerow([
                row["Org Name"], row["Reftown Link"], row["Reftown ID"],
                row["NWSC Payor League"], row["Full Name"], row["Contact"],
                row["Email"], row["Phone"], row["League"], row["Homepage"],
                row["City"], row["State"], row["General Playing Dates"], row["Info"]
            ])

    print(f"Wrote {len(output_rows)} organizations to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
