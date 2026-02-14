"""
Append chat queries and responses to a Google Sheet for review and improvement.
"""

import logging
from pathlib import Path

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


def append_chat_log(env: str, query: str, answer: str, sources: list[str]) -> None:
    """
    Append one row to the chat log sheet. Columns: Env, Timestamp, Query, Answer, Sources.
    Does nothing if sheet ID or credentials are missing; logs and swallows errors so chat still works.
    Timestamp is Pacific time formatted as y/m/d HH:MM pm.
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
        dt = datetime.now(ZoneInfo("America/Los_Angeles"))
        ts = dt.strftime("%y/%m/%d %I:%M ") + dt.strftime("%p").lower()
        answer_trunc = (answer[:MAX_CELL_CHARS] + "...") if len(answer) > MAX_CELL_CHARS else answer
        sources_str = ", ".join(sources) if sources else ""
        row = [env, ts, query, answer_trunc, sources_str]
        sheet.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        logging.exception("Chat log append failed: %s", e)


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
