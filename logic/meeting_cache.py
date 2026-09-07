"""
Local SQLite cache for Slack channels, users/emails, and active meetings.
"""
import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "meeting_cache.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS slack_channels (
                team_slug TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS slack_users (
                handle TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                email TEXT,
                display_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS active_meetings (
                meet_url TEXT PRIMARY KEY,
                notion_meeting_page_id TEXT NOT NULL,
                meeting_title TEXT NOT NULL,
                department TEXT NOT NULL,
                participant_emails TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        # Migrate older DBs missing participant_emails
        cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(active_meetings)").fetchall()
        }
        if "participant_emails" not in cols:
            conn.execute(
                "ALTER TABLE active_meetings ADD COLUMN participant_emails TEXT DEFAULT '[]'"
            )


def get_channel_id(team_slug: str) -> Optional[str]:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT channel_id FROM slack_channels WHERE team_slug = ?",
            (team_slug,),
        ).fetchone()
    return row["channel_id"] if row else None


def set_channel_id(team_slug: str, channel_id: str) -> None:
    init_db()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO slack_channels (team_slug, channel_id)
            VALUES (?, ?)
            ON CONFLICT(team_slug) DO UPDATE SET channel_id = excluded.channel_id
            """,
            (team_slug, channel_id),
        )


def get_slack_user(handle: str) -> Optional[dict]:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM slack_users WHERE handle = ?",
            (handle.lower().lstrip("@"),),
        ).fetchone()
    return dict(row) if row else None


def set_slack_user(
    handle: str,
    user_id: str,
    email: Optional[str] = None,
    display_name: Optional[str] = None,
) -> None:
    init_db()
    handle = handle.lower().lstrip("@")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO slack_users (handle, user_id, email, display_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(handle) DO UPDATE SET
                user_id = excluded.user_id,
                email = COALESCE(excluded.email, slack_users.email),
                display_name = COALESCE(excluded.display_name, slack_users.display_name)
            """,
            (handle, user_id, email, display_name),
        )


def store_active_meeting(
    meet_url: str,
    notion_meeting_page_id: str,
    meeting_title: str,
    department: str,
    participant_emails: Optional[list[str]] = None,
) -> None:
    init_db()
    emails_json = json.dumps(participant_emails or [])
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO active_meetings (
                meet_url, notion_meeting_page_id, meeting_title,
                department, participant_emails
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(meet_url) DO UPDATE SET
                notion_meeting_page_id = excluded.notion_meeting_page_id,
                meeting_title = excluded.meeting_title,
                department = excluded.department,
                participant_emails = excluded.participant_emails
            """,
            (meet_url, notion_meeting_page_id, meeting_title, department, emails_json),
        )


def get_active_meeting(meet_url: str) -> Optional[dict[str, Any]]:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM active_meetings WHERE meet_url = ?",
            (meet_url,),
        ).fetchone()
    if not row:
        return None
    data = dict(row)
    try:
        data["participant_emails"] = json.loads(data.get("participant_emails") or "[]")
    except json.JSONDecodeError:
        data["participant_emails"] = []
    return data


def delete_active_meeting(meet_url: str) -> None:
    init_db()
    with _connect() as conn:
        conn.execute("DELETE FROM active_meetings WHERE meet_url = ?", (meet_url,))
