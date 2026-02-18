"""
Meeting Orchestrator
Coordinates the end-to-end meeting scheduling workflow across all services
"""
from typing import Dict, Any
from logic.calendar_logic import find_shared_slot
from logic.google_calendar import create_calendar_event
from logic.slack_notifier import send_slack_message
from logic.notion_client import create_meeting_page

async def schedule_meeting_workflow(
    attendees: list[str],
    duration_minutes: int,
    preferred_start: str,
    preferred_end: str,
    meeting_title: str,
    meeting_description: str = ""
) -> Dict[str, Any]:
    """
    Orchestrate the complete meeting scheduling workflow:
    1. Find available time slot
    2. Create Google Calendar event with Meet link
    3. Send Slack notification
    4. Create Notion meeting page
    """
    # Step 1: Find available time slot
    slot = await find_shared_slot(
        attendees=attendees,
        duration_minutes=duration_minutes,
        start_str=preferred_start,
        end_str=preferred_end
    )
    
    if not slot:
        raise ValueError("No available time slot found for the specified attendees")
    
    # Step 2: Create Google Calendar event with Meet link
    calendar_event = await create_calendar_event(
        attendees=attendees,
        start_time=slot,
        duration_minutes=duration_minutes,
        title=meeting_title,
        description=meeting_description
    )
    
    # Extract Meet link from calendar event
    meet_link = ""
    if calendar_event.get("hangoutLink"):
        meet_link = calendar_event["hangoutLink"]
    elif calendar_event.get("conferenceData"):
        entry_points = calendar_event["conferenceData"].get("entryPoints", [])
        for entry_point in entry_points:
            if entry_point.get("entryPointType") == "video":
                meet_link = entry_point.get("uri", "")
                break
    
    # Step 3: Send Slack notification
    slack_message = (
        f"📅 New meeting scheduled!\n"
        f"**{meeting_title}**\n"
        f"👥 Attendees: {', '.join(attendees)}\n"
        f"🕒 Time: {slot}\n"
        f"⏱️ Duration: {duration_minutes} minutes\n"
        f"🔗 Join: {meet_link}"
    )
    await send_slack_message(slack_message)
    
    # Step 4: Create Notion meeting page
    notion_page = await create_meeting_page(
        title=meeting_title,
        attendees=attendees,
        scheduled_time=slot,
        duration_minutes=duration_minutes,
        meet_link=meet_link,
        description=meeting_description
    )
    
    return {
        "status": "success",
        "scheduled_time": slot,
        "meet_link": meet_link,
        "calendar_event_id": calendar_event.get("id"),
        "notion_page_id": notion_page.get("id"),
        "slack_message_sent": True
    }
