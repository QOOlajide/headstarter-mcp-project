from datetime import datetime, timedelta
import json

def load_mock_data():
    with open("mock_freebusy.json", "r") as f:
        return json.load(f)

def parse_iso_range(block):
    return (datetime.fromisoformat(block["start"]), datetime.fromisoformat(block["end"]))

def find_shared_slot(attendees, duration_minutes, start_str, end_str):
    busy_times = load_mock_data()
    duration = timedelta(minutes=duration_minutes)
    start = datetime.fromisoformat(start_str)
    end = datetime.fromisoformat(end_str)

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
