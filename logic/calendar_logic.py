"""
Calendar Logic
Finds shared available time slots using Google Calendar free/busy.
No mock fallback: if Google errors, the caller gets the exception —
we never invent a meeting time.
"""
from datetime import datetime, timedelta

from logic.google_calendar import get_freebusy


def parse_iso_range(block):
    """Parse a busy time block from Google Calendar API (offset-aware)."""
    return (
        datetime.fromisoformat(block["start"].replace("Z", "+00:00")),
        datetime.fromisoformat(block["end"].replace("Z", "+00:00")),
    )


async def find_shared_slot(attendees, duration_minutes, start_str, end_str):
    """
    First slot of duration_minutes inside [start_str, end_str] where every
    attendee is free per Google free/busy. Inputs must be offset-aware ISO.
    Returns ISO start string, or None if the window has no fit.
    """
    duration = timedelta(minutes=duration_minutes)
    start = datetime.fromisoformat(start_str)
    end = datetime.fromisoformat(end_str)

    busy_times = await get_freebusy(
        attendees=attendees,
        time_min=start.isoformat(),
        time_max=end.isoformat(),
    )

    # Collect all busy time ranges from attendees
    all_busy = []
    for email in attendees:
        for block in busy_times.get(email, []):
            all_busy.append(parse_iso_range(block))

    # Sort by start time
    all_busy.sort()

    # Find first available slot
    pointer = start
    for busy_start, busy_end in all_busy:
        if pointer + duration <= busy_start:
            return pointer.isoformat()
        pointer = max(pointer, busy_end)

    if pointer + duration <= end:
        return pointer.isoformat()

    return None
