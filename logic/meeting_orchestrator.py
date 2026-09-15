"""
Meeting Orchestrator — Slack roster, time resolution, Calendar hold, Notion row.

Time resolution (roster first):
1. start_time given → use it exactly
2. Team (department): preferred window start or next business-hours slot;
   never free/busy the channel
3. Ad-hoc: free/busy on named emails; fail if no shared slot
"""
import os
import re
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from logic.calendar_logic import find_shared_slot
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
    "Cloud",
    "Data Science",
    "Security",
}

# Backup if the model still emits informal slugs instead of the enum.
DEPARTMENT_ALIASES = {
    "engineering": "Engineering",
    "eng": "Engineering",
    "engineer": "Engineering",
    "engineers": "Engineering",
    "engineer team": "Engineering",
    "engineer-team": "Engineering",
    "eng team": "Engineering",
    "eng-team": "Engineering",
    "product": "Product",
    "prod": "Product",
    "product team": "Product",
    "product-team": "Product",
    "cloud": "Cloud",
    "cloud team": "Cloud",
    "cloud-team": "Cloud",
    "infra": "Cloud",
    "infrastructure": "Cloud",
    "data science": "Data Science",
    "data-science": "Data Science",
    "datascience": "Data Science",
    "data": "Data Science",
    "ds": "Data Science",
    "ml": "Data Science",
    "security": "Security",
    "sec": "Security",
    "infosec": "Security",
    "security team": "Security",
    "security-team": "Security",
}

# Default free/busy search window (used when the prompt has no time)
DEFAULT_TIMEZONE = "America/New_York"
BUSINESS_START_HOUR = 9
BUSINESS_END_HOUR = 17


def _scheduler_tz() -> ZoneInfo:
    return ZoneInfo(os.getenv("SCHEDULER_TIMEZONE", DEFAULT_TIMEZONE))


def _search_days() -> int:
    return int(os.getenv("SCHEDULER_SEARCH_DAYS", "3"))


def _parse_when(value: str) -> datetime:
    """ISO string -> aware datetime. Naive input assumes SCHEDULER_TIMEZONE."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_scheduler_tz())
    return dt


def _default_windows(duration_minutes: int) -> List[tuple[datetime, datetime]]:
    """
    Business-hour windows (9-17 local) for today + the next N days,
    starting no earlier than now. Weekends are skipped.
    """
    tz = _scheduler_tz()
    now = datetime.now(tz)
    windows: List[tuple[datetime, datetime]] = []
    day = now.date()
    days_checked = 0
    while days_checked <= _search_days():
        if day.weekday() < 5:  # Mon-Fri
            open_dt = datetime.combine(day, time(BUSINESS_START_HOUR), tzinfo=tz)
            close_dt = datetime.combine(day, time(BUSINESS_END_HOUR), tzinfo=tz)
            start = max(open_dt, now)
            if start + timedelta(minutes=duration_minutes) <= close_dt:
                windows.append((start, close_dt))
        day += timedelta(days=1)
        days_checked += 1
    return windows


async def _resolve_start_time(
    start_time: Optional[str],
    preferred_start: Optional[str],
    preferred_end: Optional[str],
    duration_minutes: int,
    emails: List[str],
    use_freebusy: bool,
) -> datetime:
    """
    Resolve meeting start.
    Exact start_time always wins.
    Team (use_freebusy=False): book preferred_start or next business-hours
    slot — never free/busy the channel roster.
    Ad-hoc (use_freebusy=True): free/busy named emails; fail if no slot.
    """
    duration = timedelta(minutes=duration_minutes)

    # 1. Exact time in the prompt wins.
    if start_time:
        return _parse_when(start_time)

    if preferred_start and preferred_end:
        window_start = _parse_when(preferred_start)
        window_end = _parse_when(preferred_end)
        windows = [(window_start, window_end)]
    elif preferred_start or preferred_end:
        raise ValueError(
            "Provide both preferred_start and preferred_end for a search "
            "window, or neither."
        )
    else:
        windows = _default_windows(duration_minutes)

    if not windows:
        raise ValueError(
            "No business-hours window available to book. "
            "Provide start_time or a preferred_start/preferred_end range."
        )

    # Team: pick the window start (must fit duration); no free/busy.
    if not use_freebusy:
        for window_start, window_end in windows:
            if window_start + duration <= window_end:
                return window_start
        raise ValueError(
            f"Preferred/default window is shorter than {duration_minutes} "
            "minutes. Widen the range or set an explicit start_time."
        )

    # Ad-hoc: free/busy on named people only.
    for window_start, window_end in windows:
        slot = await find_shared_slot(
            attendees=emails,
            duration_minutes=duration_minutes,
            start_str=window_start.isoformat(),
            end_str=window_end.isoformat(),
        )
        if slot:
            return datetime.fromisoformat(slot)

    raise ValueError(
        f"No shared {duration_minutes}-minute slot found for "
        f"{', '.join(emails) or 'the named participants'} in the requested "
        "window. Try a wider window or an explicit start_time."
    )


def _extract_meet_link(calendar_event: Dict[str, Any]) -> str:
    if calendar_event.get("hangoutLink"):
        return calendar_event["hangoutLink"]
    entry_points = calendar_event.get("conferenceData", {}).get("entryPoints", [])
    for entry_point in entry_points:
        if entry_point.get("entryPointType") == "video":
            return entry_point.get("uri", "")
    return ""


def _normalize_department(department: str) -> str:
    raw = str(department).strip()
    if raw in VALID_DEPARTMENTS:
        return raw
    key = re.sub(r"\s+", " ", raw.lower().lstrip("#@"))
    if key in DEPARTMENT_ALIASES:
        return DEPARTMENT_ALIASES[key]
    for option in VALID_DEPARTMENTS:
        if option.lower() == key:
            return option
    raise ValueError(
        f"Unknown department {department!r}. "
        f"Use one of: {', '.join(sorted(VALID_DEPARTMENTS))}"
    )


def _participant_emails(participants: List[dict]) -> List[str]:
    seen: set[str] = set()
    emails: List[str] = []
    for participant in participants:
        email = (participant.get("email") or "").strip().lower()
        if email and email not in seen:
            seen.add(email)
            emails.append(email)
    return emails


def _format_window(start_dt: datetime, end_dt: datetime) -> str:
    tz = _scheduler_tz()
    start_local = start_dt.astimezone(tz)
    end_local = end_dt.astimezone(tz)
    return (
        f"{start_local:%a %b %d, %I:%M %p} - {end_local:%I:%M %p} "
        f"{start_local:%Z}"
    )


async def schedule_meeting_workflow(
    meeting_title: str,
    start_time: Optional[str] = None,
    duration_minutes: int = 30,
    meeting_description: str = "",
    department: Optional[str] = None,
    team_name: Optional[str] = None,
    slack_handles: Optional[List[str]] = None,
    # Legacy no-op kept so old callers don't crash
    attendees: Optional[List[str]] = None,
    preferred_start: Optional[str] = None,
    preferred_end: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Slack-first scheduling:
    - Department sync: resolve #dept channel, notify with <!channel>
    - Ad-hoc: resolve @handles → emails + MPIM, post Meet link there
    Team meetings never free/busy the whole channel; ad-hoc does when no
    exact time is given. team_name is ignored.
    """
    del attendees  # roster comes from Slack, not a caller email list
    del team_name  # informal phrases must not become Slack slugs

    slack_handles = slack_handles or []
    is_adhoc = bool(slack_handles)

    # --- Roster first ---
    participants: List[dict] = []
    if is_adhoc:
        # People-only: ignore department. Notion Department / Team stays empty.
        notion_department: Optional[str] = None
        participants = await resolve_slack_users(slack_handles)
        channel_id = await open_group_dm([p["user_id"] for p in participants])
        channel_name = "mpim:" + ",".join(f"@{p['handle']}" for p in participants)
        notify_channel = False
    else:
        if not department or not str(department).strip():
            raise ValueError(
                "department is required for a department sync "
                "(or pass slack_handles for an ad-hoc meeting). "
                f"Valid: {', '.join(sorted(VALID_DEPARTMENTS))}"
            )
        notion_department = _normalize_department(department)
        channel_name, channel_id = await resolve_department_channel(
            department=notion_department, team_name=None
        )
        participants = await fetch_channel_member_emails(channel_id)
        notify_channel = True

    emails = _participant_emails(participants)

    # Team: next work slot / window start. Ad-hoc: free/busy named people.
    start_dt = await _resolve_start_time(
        start_time=start_time,
        preferred_start=preferred_start,
        preferred_end=preferred_end,
        duration_minutes=duration_minutes,
        emails=emails,
        use_freebusy=is_adhoc,
    )
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    calendar_event = await create_calendar_event(
        attendees=emails,
        start_time=start_dt.isoformat(),
        duration_minutes=duration_minutes,
        title=meeting_title,
        description=meeting_description,
        send_updates="all" if emails else "none",
    )
    meet_link = _extract_meet_link(calendar_event)

    when_text = _format_window(start_dt, end_dt)
    reminder = (
        f"Reminder: {meeting_title} — {when_text}. Join Meet: {meet_link}"
    )
    await send_slack_message(
        reminder, channel=channel_id, notify_channel=notify_channel
    )

    notion_page = await create_meeting_page(
        title=meeting_title,
        department=notion_department,
        slack_channel=channel_name,
        slack_channel_id=channel_id,
        start_time=start_dt.isoformat(),
        end_time=end_dt.isoformat(),
        meet_link=meet_link,
        status="Scheduled",
    )
    notion_page_id = notion_page.get("id", "")

    if meet_link and notion_page_id:
        store_active_meeting(
            meet_url=meet_link,
            notion_meeting_page_id=notion_page_id,
            meeting_title=meeting_title,
            department=notion_department or "",
            participant_emails=emails,
            ends_at=end_dt.isoformat(),
        )

    return {
        "status": "success",
        "mode": "adhoc" if is_adhoc else "department",
        "scheduled_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
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
