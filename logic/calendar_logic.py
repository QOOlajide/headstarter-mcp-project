"""
Calendar Logic
Finds shared available time slots using Google Calendar API
"""
from datetime import datetime, timedelta
from typing import Optional
import os
from logic.google_calendar import get_freebusy

def parse_iso_range(block):
    """Parse a busy time block from Google Calendar API"""
    return (datetime.fromisoformat(block["start"]), datetime.fromisoformat(block["end"]))

async def find_shared_slot(attendees, duration_minutes, start_str, end_str):
    """
    Find a shared available time slot for all attendees using Google Calendar API
    Falls back to mock data if API is unavailable
    """
    duration = timedelta(minutes=duration_minutes)
    start = datetime.fromisoformat(start_str)
    end = datetime.fromisoformat(end_str)
    
    # Try to get real freebusy data from Google Calendar API
    try:
        busy_times = await get_freebusy(
            attendees=attendees,
            time_min=start.isoformat(),
            time_max=end.isoformat()
        )
    except Exception as e:
        print(f"Warning: Could not fetch Google Calendar data: {e}")
        print("Falling back to mock data...")
        # Fallback to mock data if API unavailable
        import json
        try:
            with open("mock_freebusy.json", "r") as f:
                busy_times = json.load(f)
        except FileNotFoundError:
            busy_times = {}

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
