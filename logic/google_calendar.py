"""
Google Calendar API Integration
Handles calendar operations including free/busy queries and event creation with Meet links
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from auth.google_auth import get_google_credentials

def get_calendar_service():
    """Get authenticated Google Calendar service"""
    creds = get_google_credentials()
    if not creds:
        raise ValueError("Google Calendar credentials not available. Please authenticate first.")
    return build('calendar', 'v3', credentials=creds)

async def get_freebusy(attendees: List[str], time_min: str, time_max: str) -> Dict[str, List[Dict]]:
    """
    Query free/busy information for multiple attendees
    Returns a dictionary mapping email addresses to their busy time blocks
    """
    try:
        service = get_calendar_service()
        
        # Prepare freebusy query
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": email} for email in attendees]
        }
        
        freebusy = service.freebusy().query(body=body).execute()
        
        # Format the response
        result = {}
        calendars = freebusy.get('calendars', {})
        
        for email in attendees:
            calendar_data = calendars.get(email, {})
            busy_blocks = calendar_data.get('busy', [])
            result[email] = busy_blocks
        
        return result
    except HttpError as error:
        print(f"An error occurred: {error}")
        raise
    except Exception as e:
        print(f"Error querying freebusy: {e}")
        # Fallback to empty busy times if API call fails
        return {email: [] for email in attendees}

async def create_calendar_event(
    attendees: List[str],
    start_time: str,
    duration_minutes: int,
    title: str,
    description: str = "",
    send_updates: str = "none",
) -> Dict[str, Any]:
    """
    Create a Google Calendar event with Google Meet link.
    Slack-first flow uses attendees=[] and send_updates="none".
    """
    try:
        service = get_calendar_service()

        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "UTC",
            },
            # Clarification: empty attendees bypasses email invite maintenance
            "attendees": [{"email": email} for email in (attendees or [])],
            "conferenceData": {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 15},
                ],
            },
        }

        created_event = (
            service.events()
            .insert(
                calendarId="primary",
                body=event,
                conferenceDataVersion=1,
                sendUpdates=send_updates,
            )
            .execute()
        )

        return created_event
    except HttpError as error:
        print(f"An error occurred creating event: {error}")
        raise
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        raise

async def generate_meet_link(event_id: str) -> str:
    """
    Generate or retrieve Google Meet link for an existing event
    """
    try:
        service = get_calendar_service()
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        # Try to get Meet link from conference data
        conference_data = event.get('conferenceData', {})
        entry_points = conference_data.get('entryPoints', [])
        
        for entry_point in entry_points:
            if entry_point.get('entryPointType') == 'video':
                return entry_point.get('uri', '')
        
        # Fallback: check hangoutLink (legacy)
        hangout_link = event.get('hangoutLink')
        if hangout_link:
            return hangout_link
        
        return ""
    except HttpError as error:
        print(f"An error occurred retrieving event: {error}")
        raise
    except Exception as e:
        print(f"Error generating Meet link: {e}")
        raise

