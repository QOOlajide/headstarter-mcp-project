"""
Create Meetings & Summaries + Actionable Directives Notion databases
with the exact property names expected by logic/notion_client.py.

Usage:
  python scripts/setup_notion_dbs.py --parent-page-id <PAGE_UUID>

Requires NOTION_API_KEY in .env. Parent page must be shared with the integration.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def normalize_page_id(raw: str) -> str:
    """Accept dashed UUID or 32-hex id from a Notion URL."""
    cleaned = raw.strip()
    match = re.search(
        r"([0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
        cleaned,
        re.I,
    )
    if not match:
        raise ValueError(f"Could not parse Notion page id from: {raw}")
    value = match.group(1).replace("-", "").lower()
    return f"{value[:8]}-{value[8:12]}-{value[12:16]}-{value[16:20]}-{value[20:]}"


def create_database(client: httpx.Client, token: str, payload: dict) -> dict:
    response = client.post(
        f"{NOTION_API_URL}/databases",
        headers=_headers(token),
        json=payload,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Create database failed: {response.text}")
    return response.json()


def first_data_source_id(database: dict) -> str:
    """
    API 2026-03-11: database.id is the container. Columns and relations
    live on the child data source (database.data_sources[0].id).
    """
    sources = database.get("data_sources") or []
    if sources and sources[0].get("id"):
        return sources[0]["id"]
    raise RuntimeError(
        "Database response had no data_sources[0].id. "
        f"Top-level keys: {list(database.keys())}"
    )


def upsert_env_keys(env_path: Path, updates: dict[str, str]) -> None:
    existing = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    lines = existing.splitlines()
    keys_seen = set()
    new_lines: list[str] = []
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                keys_seen.add(key)
                continue
        new_lines.append(line)
    for key, value in updates.items():
        if key not in keys_seen:
            new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision Notion meeting databases")
    parser.add_argument(
        "--parent-page-id",
        required=True,
        help="Parent Notion page ID or URL (must be shared with your integration)",
    )
    parser.add_argument(
        "--write-env",
        action="store_true",
        help="Write NOTION_MEETINGS_DATABASE_ID and NOTION_DIRECTIVES_DATABASE_ID into .env",
    )
    args = parser.parse_args()

    token = os.getenv("NOTION_API_KEY")
    if not token:
        print("ERROR: NOTION_API_KEY missing from .env", file=sys.stderr)
        return 1

    parent_page_id = normalize_page_id(args.parent_page_id)

    # Meetings Status remains select per requirements §3.2 / ADR 004.
    meetings_properties = {
        "Meeting Name": {"title": {}},
        "Department / Team": {
            "select": {
                "options": [
                    {"name": "Engineering", "color": "blue"},
                    {"name": "Product", "color": "purple"},
                    {"name": "Sales", "color": "green"},
                    {"name": "Design", "color": "pink"},
                    {"name": "Cross-Functional", "color": "gray"},
                ]
            }
        },
        "Slack Channel": {"rich_text": {}},
        "Slack Channel ID": {"rich_text": {}},
        "Date & Time": {"date": {}},
        "Google Meet URL": {"url": {}},
        "Status": {
            "select": {
                "options": [
                    {"name": "Scheduled", "color": "yellow"},
                    {"name": "Completed", "color": "green"},
                    {"name": "Canceled", "color": "red"},
                ]
            }
        },
    }

    with httpx.Client(timeout=30.0) as client:
        print("Creating Meetings & Summaries database...")
        meetings_db = create_database(
            client,
            token,
            {
                "parent": {"type": "page_id", "page_id": parent_page_id},
                "title": [{"type": "text", "text": {"content": "Meetings & Summaries"}}],
                "initial_data_source": {"properties": meetings_properties},
            },
        )
        meetings_id = meetings_db["id"]
        meetings_data_source_id = first_data_source_id(meetings_db)
        print(f"  -> database {meetings_id}")
        print(f"  -> data source {meetings_data_source_id}")

        print("Creating Actionable Directives database...")
        # synced_property_name makes Notion create reverse "Action Items" on Meetings
        directives_db = create_database(
            client,
            token,
            {
                "parent": {"type": "page_id", "page_id": parent_page_id},
                "title": [{"type": "text", "text": {"content": "Actionable Directives"}}],
                "initial_data_source": {
                    "properties": {
                        "Directive / Task": {"title": {}},
                        "Assignee Email": {"rich_text": {}},
                        "Priority": {
                            "select": {
                                "options": [
                                    {"name": "High", "color": "red"},
                                    {"name": "Medium", "color": "yellow"},
                                    {"name": "Low", "color": "green"},
                                ]
                            }
                        },
                        "Due Date": {"date": {}},
                        "Status": {
                            "status": {
                                "options": [
                                    {"name": "To Do", "color": "default"},
                                    {"name": "In Progress", "color": "blue"},
                                    {"name": "Done", "color": "green"},
                                ]
                            }
                        },
                        "Source Meeting": {
                            "relation": {
                                "data_source_id": meetings_data_source_id,
                                "type": "dual_property",
                                "dual_property": {
                                    "synced_property_name": "Action Items",
                                },
                            }
                        },
                    },
                },
            },
        )
        directives_id = directives_db["id"]
        print(f"  -> {directives_id}")

    print("\nDone. Add these to your .env:\n")
    print(f"NOTION_MEETINGS_DATABASE_ID={meetings_id}")
    print(f"NOTION_DIRECTIVES_DATABASE_ID={directives_id}")

    if args.write_env:
        upsert_env_keys(
            ROOT / ".env",
            {
                "NOTION_MEETINGS_DATABASE_ID": meetings_id,
                "NOTION_DIRECTIVES_DATABASE_ID": directives_id,
            },
        )
        print(f"\nWrote IDs into {ROOT / '.env'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
