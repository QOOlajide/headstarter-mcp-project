"""
Meeting Orchestrator — Slack-first, zero-email calendar maintenance.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from logic.google_calendar import create_calendar_event
from logic.meeting_cache import store_active_meeting
from logic.notion_client import create_meeting_page
from logic.slack_notifier import (
    fetch_channel_member_emails,
    open_group_dm,
    resolve_department_channel,
    resolve_slack_users,
    send_slack_message,
)

VALID_DEPARTMENTS = {
    "Engineering",
    "Product",
    "Sales",
    "Design",
    "Cross-Functional",
}


def _extract_meet_link(calendar_event: Dict[str, Any]) -> str:
    if calendar_event.get("hangoutLink"):
        return calendar_event["hangoutLink"]
    entry_points = calendar_event.get("conferenceData", {}).get("entryPoints", [])
    for entry_point in entry_points:
        if entry_point.get("entryPointType") == "video":
            return entry_point.get("uri", "")
    return ""


def _normalize_department(department: Optional[str]) -> str:
    if not department:
        return "Cross-Functional"
    if department in VALID_DEPARTMENTS:
        return department
    for option in VALID_DEPARTMENTS:
        if option.lower() == department.lower():
            return option
    return "Cross-Functional"


def _participant_emails(participants: List[dict]) -> List[str]:
    return [p["email"] for p in participants if p.get("email")]


async def schedule_meeting_workflow(
    meeting_title: str,
    start_time: str,
    duration_minutes: int = 30,
    meeting_description: str = "",
    department: Optional[str] = None,
    team_name: Optional[str] = None,
    slack_handles: Optional[List[str]] = None,
    # Legacy no-ops kept so old callers don't crash
    attendees: Optional[List[str]] = None,
    preferred_start: Optional[str] = None,
    preferred_end: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Slack-first scheduling:
    - Department sync: resolve #dept channel, notify with <!channel>
    - Ad-hoc: resolve @handles → emails + MPIM, post Meet link there
    Calendar attendees stay empty; emails come from Slack profiles for Notion.
    """
    del attendees  # intentionally unused (zero-email calendar maintenance)

    # Prefer explicit start_time; fall back to legacy preferred_start
    slot = start_time or preferred_start
    if not slot:
        raise ValueError("start_time is required (ISO datetime)")

    slack_handles = slack_handles or []
    is_adhoc = bool(slack_handles)
    department = _normalize_department(department)

    participants: List[dict] = []
    if is_adhoc:
        participants = await resolve_slack_users(slack_handles)
        channel_id = await open_group_dm([p["user_id"] for p in participants])
        channel_name = "mpim:" + ",".join(f"@{p['handle']}" for p in participants)
        notify_channel = False
        notion_department = department
    else:
        channel_name, channel_id = await resolve_department_channel(
            department=department, team_name=team_name
        )
        participants = await fetch_channel_member_emails(channel_id)
        notify_channel = True
        notion_department = department

    calendar_event = await create_calendar_event(
        attendees=[],  # Clarification: leave empty
        start_time=slot,
        duration_minutes=duration_minutes,
        title=meeting_title,
        description=meeting_description,
        send_updates="none",
    )
    meet_link = _extract_meet_link(calendar_event)

    reminder = f"Reminder: {meeting_title} starts soon! Join Meet: {meet_link}"
    await send_slack_message(
        reminder, channel=channel_id, notify_channel=notify_channel
    )

    start_dt = datetime.fromisoformat(slot.replace("Z", "+00:00"))
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    notion_page = await create_meeting_page(
        title=meeting_title,
        department=notion_department,
        slack_channel=channel_name,
        slack_channel_id=channel_id,
        start_time=slot,
        end_time=end_dt.isoformat(),
        meet_link=meet_link,
        status="Scheduled",
    )
    notion_page_id = notion_page.get("id", "")
    emails = _participant_emails(participants)

    if meet_link and notion_page_id:
        store_active_meeting(
            meet_url=meet_link,
            notion_meeting_page_id=notion_page_id,
            meeting_title=meeting_title,
            department=notion_department,
            participant_emails=emails,
        )

    return {
        "status": "success",
        "mode": "adhoc" if is_adhoc else "department",
        "scheduled_time": slot,
        "meet_link": meet_link,
        "calendar_event_id": calendar_event.get("id"),
        "notion_page_id": notion_page_id,
        "slack_channel": channel_name,
        "slack_channel_id": channel_id,
        "department": notion_department,
        "participant_emails": emails,
        "participants": [
            {
                "handle": p.get("handle"),
                "display_name": p.get("display_name"),
                "email": p.get("email"),
            }
            for p in participants
        ],
        "slack_message_sent": True,
    }
