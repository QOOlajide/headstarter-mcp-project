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
    department: str,
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

    page_content = {
        "parent": {"database_id": _meetings_db_id()},
        "properties": {
            "Meeting Name": {
                "title": [{"type": "text", "text": {"content": title}}]
            },
            "Department / Team": {"select": {"name": department}},
            "Slack Channel": {"rich_text": _rich_text(slack_channel)},
            "Slack Channel ID": {"rich_text": _rich_text(slack_channel_id)},
            "Date & Time": {"date": date_payload},
            "Google Meet URL": {"url": meet_link or None},
            "Status": {"select": {"name": status}},
        },
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
