"""
Notion API Integration
Meetings & Summaries + Actionable Directives (requirements §3.2 / §4.5)
"""
import os
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"


def get_notion_headers() -> Dict[str, str]:
    notion_token = os.getenv("NOTION_API_KEY")
    if not notion_token:
        raise ValueError("NOTION_API_KEY not found in environment variables")
    return {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _meetings_db_id() -> str:
    db_id = os.getenv("NOTION_MEETINGS_DATABASE_ID") or os.getenv("NOTION_DATABASE_ID")
    if not db_id:
        raise ValueError(
            "NOTION_MEETINGS_DATABASE_ID (or NOTION_DATABASE_ID) not set"
        )
    return db_id


def _directives_db_id() -> str:
    db_id = os.getenv("NOTION_DIRECTIVES_DATABASE_ID")
    if not db_id:
        raise ValueError("NOTION_DIRECTIVES_DATABASE_ID not set")
    return db_id


# Notion API 2025-09+ / 2026: query rows via data_sources, not databases.
_meetings_data_source_id_cache: Optional[str] = None


async def _meetings_data_source_id(client: Optional[httpx.AsyncClient] = None) -> str:
    """
    Resolve the Meetings table (data source) id.
    Prefer NOTION_MEETINGS_DATA_SOURCE_ID; otherwise GET the database container.
    """
    global _meetings_data_source_id_cache
    env_id = os.getenv("NOTION_MEETINGS_DATA_SOURCE_ID")
    if env_id:
        return env_id
    if _meetings_data_source_id_cache:
        return _meetings_data_source_id_cache

    headers = get_notion_headers()
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=20.0)
    assert client is not None
    try:
        response = await client.get(
            f"{NOTION_API_URL}/databases/{_meetings_db_id()}",
            headers=headers,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Notion retrieve meetings database failed: {response.text}"
            )
        sources = response.json().get("data_sources") or []
        if not sources or not sources[0].get("id"):
            raise RuntimeError(
                "Meetings database has no data_sources[0].id; "
                "set NOTION_MEETINGS_DATA_SOURCE_ID or re-run setup_notion_dbs.py"
            )
        _meetings_data_source_id_cache = sources[0]["id"]
        return _meetings_data_source_id_cache
    finally:
        if owns_client:
            await client.aclose()


async def _query_meetings_data_source(
    client: httpx.AsyncClient,
    body: Dict[str, Any],
) -> Dict[str, Any]:
    """POST /v1/data_sources/{id}/query (Notion-Version 2026-03-11)."""
    ds_id = await _meetings_data_source_id(client)
    response = await client.post(
        f"{NOTION_API_URL}/data_sources/{ds_id}/query",
        headers=get_notion_headers(),
        json=body,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Notion data source query failed: {response.text}")
    return response.json()


def _rich_text(content: str) -> List[Dict[str, Any]]:
    return [{"type": "text", "text": {"content": content[:2000]}}]


async def create_meeting_page(
    title: str,
    department: Optional[str],
    slack_channel: str,
    slack_channel_id: str,
    start_time: str,
    end_time: Optional[str],
    meet_link: str,
    status: str = "Scheduled",
) -> Dict[str, Any]:
    """Create a row in Meetings & Summaries with Status=Scheduled."""
    headers = get_notion_headers()
    date_payload: Dict[str, Any] = {"start": start_time}
    if end_time:
        date_payload["end"] = end_time

    properties: Dict[str, Any] = {
        "Meeting Name": {
            "title": [{"type": "text", "text": {"content": title}}]
        },
        "Slack Channel": {"rich_text": _rich_text(slack_channel)},
        "Slack Channel ID": {"rich_text": _rich_text(slack_channel_id)},
        "Date & Time": {"date": date_payload},
        "Google Meet URL": {"url": meet_link or None},
        "Status": {"select": {"name": status}},
    }
    # Ad-hoc meetings are people-only — leave Department / Team empty.
    if department:
        properties["Department / Team"] = {"select": {"name": department}}

    page_content = {
        "parent": {"database_id": _meetings_db_id()},
        "properties": properties,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{NOTION_API_URL}/pages",
            headers=headers,
            json=page_content,
        )
        if response.status_code >= 400 and response.status_code <= 500:
            raise RuntimeError(f"Notion create meeting failed: {response.text}")
        return response.json()


async def append_meeting_summary(
    meeting_page_id: str,
    summary_bullets: List[str],
) -> Dict[str, Any]:
    """Append Summary & Key Decisions blocks and mark Status=Completed."""
    headers = get_notion_headers()
    children: List[Dict[str, Any]] = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": _rich_text("Summary & Key Decisions")
            },
        }
    ]
    for bullet in summary_bullets:
        children.append(
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": _rich_text(bullet)},
            }
        )

    async with httpx.AsyncClient(timeout=20.0) as client:
        append_response = await client.patch(
            f"{NOTION_API_URL}/blocks/{meeting_page_id}/children",
            headers=headers,
            json={"children": children},
        )
        if append_response.status_code >= 400:
            raise RuntimeError(
                f"Notion append summary failed: {append_response.text}"
            )

        update_response = await client.patch(
            f"{NOTION_API_URL}/pages/{meeting_page_id}",
            headers=headers,
            json={"properties": {"Status": {"select": {"name": "Completed"}}}},
        )
        if update_response.status_code >= 400:
            raise RuntimeError(
                f"Notion status update failed: {update_response.text}"
            )
        return {
            "appended": append_response.json(),
            "page": update_response.json(),
        }


async def create_actionable_directive(
    meeting_page_id: str,
    task: str,
    assignee_email: str,
    priority: str,
    due_date: Optional[str],
) -> Dict[str, Any]:
    """Insert Actionable Directives row linked to Source Meeting."""
    headers = get_notion_headers()
    properties: Dict[str, Any] = {
        "Directive / Task": {
            "title": [{"type": "text", "text": {"content": task[:2000]}}]
        },
        "Assignee Email": {"rich_text": _rich_text(assignee_email or "")},
        "Priority": {"select": {"name": priority if priority in {"High", "Medium", "Low"} else "Medium"}},
        "Status": {"status": {"name": "To Do"}},
        "Source Meeting": {"relation": [{"id": meeting_page_id}]},
    }
    if due_date:
        properties["Due Date"] = {"date": {"start": due_date}}

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{NOTION_API_URL}/pages",
            headers=headers,
            json={
                "parent": {"database_id": _directives_db_id()},
                "properties": properties,
            },
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Notion create directive failed: {response.text}")
        return response.json()


async def sync_transcript_results(
    meeting_page_id: str,
    summary_bullets: List[str],
    action_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Full post-call Notion sync: summary + relational directives."""
    summary_result = await append_meeting_summary(meeting_page_id, summary_bullets)
    directives = []
    for item in action_items:
        directives.append(
            await create_actionable_directive(
                meeting_page_id=meeting_page_id,
                task=item.get("task", "Untitled task"),
                assignee_email=item.get("assignee_email", ""),
                priority=item.get("priority", "Medium"),
                due_date=item.get("due_date"),
            )
        )
    return {"summary": summary_result, "directives": directives}


def _normalize_meet_url(meet_url: str) -> str:
    return (meet_url or "").strip().rstrip("/")


async def find_meeting_page_by_meet_url(meet_url: str) -> Optional[Dict[str, Any]]:
    """
    Look up a Meetings & Summaries row by Google Meet URL.
    Used by the hosted webhook when local SQLite is unavailable.
    Returns {id, meeting_title} or None.
    """
    target = _normalize_meet_url(meet_url)
    if not target:
        return None

    # Try exact URL and trailing-slash variant (Notion stores what Calendar gave).
    candidates = [target, target + "/"]
    async with httpx.AsyncClient(timeout=20.0) as client:
        for candidate in candidates:
            payload = await _query_meetings_data_source(
                client,
                {
                    "filter": {
                        "property": "Google Meet URL",
                        "url": {"equals": candidate},
                    },
                    "page_size": 1,
                },
            )
            results = payload.get("results") or []
            if not results:
                continue
            page = results[0]
            return {
                "id": page["id"],
                "meeting_title": _page_title(page),
                "meet_url": candidate,
            }
    return None


def _page_meeting_status(page: Dict[str, Any]) -> Optional[str]:
    prop = page.get("properties", {}).get("Status", {})
    select = prop.get("select") or {}
    return select.get("name")


def _page_meeting_end(page: Dict[str, Any]) -> Optional[str]:
    date_prop = page.get("properties", {}).get("Date & Time", {}).get("date") or {}
    return date_prop.get("end") or date_prop.get("start")


def _page_meet_url(page: Dict[str, Any]) -> Optional[str]:
    return page.get("properties", {}).get("Google Meet URL", {}).get("url")


def _page_title(page: Dict[str, Any]) -> str:
    title_parts = page.get("properties", {}).get("Meeting Name", {}).get("title", [])
    return "".join(part.get("plain_text", "") for part in title_parts) or "Meeting"


async def list_overdue_scheduled_meetings(cutoff) -> List[Dict[str, Any]]:
    """
    Notion Meetings still Status=Scheduled whose Date & Time end (or start)
    is <= cutoff. Used by the hub auto-finalize loop.
    """
    from datetime import datetime

    overdue: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            body: Dict[str, Any] = {
                "filter": {
                    "property": "Status",
                    "select": {"equals": "Scheduled"},
                },
                "page_size": 50,
            }
            if cursor:
                body["start_cursor"] = cursor
            payload = await _query_meetings_data_source(client, body)
            for page in payload.get("results") or []:
                end_raw = _page_meeting_end(page)
                if not end_raw:
                    continue
                try:
                    ends = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if ends.tzinfo is None and getattr(cutoff, "tzinfo", None):
                    ends = ends.replace(tzinfo=cutoff.tzinfo)
                try:
                    if ends > cutoff:
                        continue
                except TypeError:
                    continue
                overdue.append(
                    {
                        "id": page["id"],
                        "meeting_title": _page_title(page),
                        "meet_url": _page_meet_url(page) or "",
                        "ends_at": end_raw,
                    }
                )
            if not payload.get("has_more"):
                break
            cursor = payload.get("next_cursor")
            if not cursor:
                break
    return overdue


async def get_meeting_page_status(meeting_page_id: str) -> Optional[str]:
    headers = get_notion_headers()
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            f"{NOTION_API_URL}/pages/{meeting_page_id}",
            headers=headers,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Notion page fetch failed: {response.text}")
        return _page_meeting_status(response.json())


async def finalize_meeting_without_transcript(meeting_page_id: str) -> Dict[str, Any]:
    """
    Mark Status=Completed and append a note that no transcript arrived.
    Does not invent a summary or action items. Idempotent if already Completed.
    """
    current = await get_meeting_page_status(meeting_page_id)
    if current == "Completed":
        return {"skipped": True, "reason": "already_completed", "page_id": meeting_page_id}

    headers = get_notion_headers()
    note = (
        "No transcript was received for this meeting. "
        "Status marked Completed without summary or action items."
    )
    children = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": _rich_text("Meeting closed")},
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": _rich_text(note)},
        },
    ]
    async with httpx.AsyncClient(timeout=20.0) as client:
        append_response = await client.patch(
            f"{NOTION_API_URL}/blocks/{meeting_page_id}/children",
            headers=headers,
            json={"children": children},
        )
        if append_response.status_code >= 400:
            raise RuntimeError(
                f"Notion finalize note failed: {append_response.text}"
            )
        update_response = await client.patch(
            f"{NOTION_API_URL}/pages/{meeting_page_id}",
            headers=headers,
            json={"properties": {"Status": {"select": {"name": "Completed"}}}},
        )
        if update_response.status_code >= 400:
            raise RuntimeError(
                f"Notion finalize status failed: {update_response.text}"
            )
        return {
            "appended": append_response.json(),
            "page": update_response.json(),
            "note": note,
        }
