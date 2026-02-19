"""
Append chat queries and responses to a Google Sheet for review and improvement.
"""

import logging
import uuid
from pathlib import Path

# Chat log columns: Env, IP, Grade, Query, Answer, Sources, Timestamp, Log ID
CHAT_LOG_HEADERS = ["Env", "IP", "Grade", "Query", "Answer", "Sources", "Timestamp", "Log ID"]

# Backend directory (same as this module); sheet_id and oregon-referees*.json live here
# so they are included when Docker copies backend/ into the image.
BACKEND_DIR = Path(__file__).resolve().parent

# Max characters per cell (Google Sheets limit)
MAX_CELL_CHARS = 50_000

_sheet_client = None
_sheet_id = None


def _get_sheet_id() -> str | None:
    """Read sheet ID from backend file 'sheet_id'."""
    global _sheet_id
    if _sheet_id is not None:
        return _sheet_id
    path = BACKEND_DIR / "sheet_id"
    if not path.exists():
        return None
    try:
        _sheet_id = path.read_text().strip()
        return _sheet_id if _sheet_id else None
    except Exception:
        return None


def _get_credentials_path() -> Path | None:
    """Find service account JSON file starting with 'oregon-referees' in backend dir."""
    for f in BACKEND_DIR.glob("oregon-referees*.json"):
        if f.is_file():
            return f
    return None


def _get_sheet_client():
    """Return gspread client, or None if credentials/sheet not configured."""
    global _sheet_client
    if _sheet_client is not None:
        return _sheet_client
    creds_path = _get_credentials_path()
    if not creds_path or not creds_path.exists():
        return None
    try:
        import gspread
        _sheet_client = gspread.service_account(filename=str(creds_path))
        return _sheet_client
    except Exception as e:
        logging.warning("Chat log: could not create Sheets client: %s", e)
        return None


def _ensure_header_row(sheet) -> None:
    """Ensure row 1 is the header. Insert header at top if row 1 is blank or contains data."""
    try:
        first_cell = sheet.cell(1, 1).value
        if (first_cell or "").strip() != "Env":
            sheet.insert_row(CHAT_LOG_HEADERS, index=1, value_input_option="USER_ENTERED")
    except Exception as e:
        logging.warning("Chat log: could not ensure header row: %s", e)


def append_chat_log(
    env: str,
    query: str,
    answer: str,
    sources: list[str],
    client_ip: str | None = None,
) -> str | None:
    """
    Insert one row at the top of the chat log sheet.
    Columns (in order): Env, IP, Grade, Query, Answer, Sources, Timestamp, Log ID.
    Returns the log_id (UUID) or None if sheet/credentials unavailable.
    Timestamp is Pacific time formatted as y/m/d HH:MM pm.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    sheet_id = _get_sheet_id()
    if not sheet_id:
        return None
    client = _get_sheet_client()
    if not client:
        return None
    try:
        sheet = client.open_by_key(sheet_id).sheet1
        _ensure_header_row(sheet)

        log_id = str(uuid.uuid4())
        dt = datetime.now(ZoneInfo("America/Los_Angeles"))
        ts = dt.strftime("%y/%m/%d %I:%M ") + dt.strftime("%p").lower()
        answer_trunc = (answer[:MAX_CELL_CHARS] + "...") if len(answer) > MAX_CELL_CHARS else answer
        sources_str = ", ".join(sources) if sources else ""
        ip_str = (client_ip or "").strip() or ""

        # Env, IP, Grade, Query, Answer, Sources, Timestamp, Log ID
        row = [env, ip_str, "", query, answer_trunc, sources_str, ts, log_id]
        sheet.insert_row(row, index=2, value_input_option="USER_ENTERED")
        return log_id
    except Exception as e:
        logging.exception("Chat log insert failed: %s", e)
        return None


RATE_LIMIT_MSG = "Excessive requests detected. Try again later."


def append_rate_limit_log(env: str, client_ip: str | None = None) -> None:
    """
    Append one row to the chat log sheet for a rate-limit event.
    Columns (same as chat log): Env, IP, Grade, Query, Answer, Sources, Timestamp, Log ID.
    Query = "[RATE LIMIT]", Answer = "Excessive requests detected. Try again later."
    Does nothing if sheet/credentials unavailable; logs and swallows errors.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    sheet_id = _get_sheet_id()
    if not sheet_id:
        return
    client = _get_sheet_client()
    if not client:
        return
    try:
        sheet = client.open_by_key(sheet_id).sheet1
        _ensure_header_row(sheet)

        log_id = str(uuid.uuid4())
        dt = datetime.now(ZoneInfo("America/Los_Angeles"))
        ts = dt.strftime("%y/%m/%d %I:%M ") + dt.strftime("%p").lower()
        ip_str = (client_ip or "").strip() or ""

        row = [env, ip_str, "", "[RATE LIMIT]", RATE_LIMIT_MSG, "", ts, log_id]
        sheet.insert_row(row, index=2, value_input_option="USER_ENTERED")
    except Exception as e:
        logging.exception("Rate limit log insert failed: %s", e)


def update_chat_log_grade(log_id: str, grade: str) -> bool:
    """
    Update the Grade column for the row with the given log_id.
    Returns True on success, False if not found or on error.
    """
    sheet_id = _get_sheet_id()
    if not sheet_id:
        return False
    client = _get_sheet_client()
    if not client:
        return False
    try:
        sheet = client.open_by_key(sheet_id).sheet1
        cell = sheet.find(log_id, in_column=8)
        sheet.update_cell(cell.row, 3, grade)
        return True
    except Exception as e:
        logging.warning("Chat log grade update failed: %s", e)
        return False


def append_license_lookup_log(
    env: str,
    trigger_query: str,
    no_match: bool,
    license_count: int | None,
    client_ip: str | None = None,
) -> None:
    """
    Append one row to the chat log sheet when the US Soccer profile (license) API is used.
    Does not log the actual result; logs only the triggering query text, whether the email
    had no match, and the number of license records returned.
    Columns (same as chat log): Env, IP, Grade, Query, Answer, Sources, Timestamp, Log ID.
    Query = trigger_query; Answer = "[License lookup] no_match=<bool>, license_count=<n>".
    Does nothing if sheet/credentials unavailable; logs and swallows errors.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    sheet_id = _get_sheet_id()
    if not sheet_id:
        return
    client = _get_sheet_client()
    if not client:
        return
    try:
        sheet = client.open_by_key(sheet_id).sheet1
        _ensure_header_row(sheet)

        log_id = str(uuid.uuid4())
        dt = datetime.now(ZoneInfo("America/Los_Angeles"))
        ts = dt.strftime("%y/%m/%d %I:%M ") + dt.strftime("%p").lower()
        ip_str = (client_ip or "").strip() or ""
        query_str = (trigger_query or "").strip() or "[License lookup from menu]"
        count_str = str(license_count) if license_count is not None else "—"
        answer_str = f"[License lookup] no_match={no_match}, license_count={count_str}"

        row = [env, ip_str, "", query_str, answer_str, "", ts, log_id]
        sheet.insert_row(row, index=2, value_input_option="USER_ENTERED")
    except Exception as e:
        logging.exception("License lookup log insert failed: %s", e)


def append_feedback(user: str, feedback: str) -> None:
    """
    Append one row to the Feedback sheet. Columns: Timestamp, User, Feedback.
    Uses the same Google Sheet as the chat log; worksheet title is "Feedback".
    Creates the worksheet with headers if it does not exist.
    Does nothing if sheet ID or credentials are missing; logs and swallows errors.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    sheet_id = _get_sheet_id()
    if not sheet_id:
        return
    client = _get_sheet_client()
    if not client:
        return
    try:
        import gspread
        from gspread.exceptions import WorksheetNotFound

        spreadsheet = client.open_by_key(sheet_id)
        try:
            sheet = spreadsheet.worksheet("Feedback")
        except WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title="Feedback", rows=1000, cols=3)
            sheet.append_row(["Timestamp", "User", "Feedback"], value_input_option="USER_ENTERED")

        dt = datetime.now(ZoneInfo("America/Los_Angeles"))
        ts = dt.strftime("%y/%m/%d %I:%M ") + dt.strftime("%p").lower()
        feedback_trunc = (feedback[:MAX_CELL_CHARS] + "...") if len(feedback) > MAX_CELL_CHARS else feedback
        user_str = (user or "").strip()
        sheet.append_row([ts, user_str, feedback_trunc], value_input_option="USER_ENTERED")
    except Exception as e:
        logging.exception("Feedback append failed: %s", e)
