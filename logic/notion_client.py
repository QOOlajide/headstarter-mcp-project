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

    headers = get_notion_headers()
    # Try exact URL and trailing-slash variant (Notion stores what Calendar gave).
    candidates = [target, target + "/"]
    async with httpx.AsyncClient(timeout=20.0) as client:
        for candidate in candidates:
            response = await client.post(
                f"{NOTION_API_URL}/databases/{_meetings_db_id()}/query",
                headers=headers,
                json={
                    "filter": {
                        "property": "Google Meet URL",
                        "url": {"equals": candidate},
                    },
                    "page_size": 1,
                },
            )
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Notion meet URL lookup failed: {response.text}"
                )
            results = response.json().get("results") or []
            if not results:
                continue
            page = results[0]
            title_parts = (
                page.get("properties", {})
                .get("Meeting Name", {})
                .get("title", [])
            )
            title = "".join(
                part.get("plain_text", "") for part in title_parts
            ) or "Meeting"
            return {
                "id": page["id"],
                "meeting_title": title,
                "meet_url": candidate,
            }
    return None


async def finalize_meeting_without_transcript(meeting_page_id: str) -> Dict[str, Any]:
    """
    Mark Status=Completed and append a note that no transcript arrived.
    Does not invent a summary or action items.
    """
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
