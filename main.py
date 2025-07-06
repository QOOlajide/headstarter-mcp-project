from logic.calendar_logic import find_shared_slot
from logic.slack_notifier import send_slack_message
from fastapi import FastAPI, Request
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

# 👇 Debug print
print("🔍 SLACK_BOT_TOKEN:", os.getenv("SLACK_BOT_TOKEN"))
print("🔍 SLACK_CHANNEL:", os.getenv("SLACK_CHANNEL"))

app = FastAPI()

class MeetingRequest(BaseModel):
    attendees: list[str]
    duration_minutes: int
    preferred_start: str
    preferred_end: str

@app.post("/schedule-meeting")
async def schedule_meeting(request: MeetingRequest):
    slot = find_shared_slot(
        attendees=request.attendees,
        duration_minutes=request.duration_minutes,
        start_str=request.preferred_start,
        end_str=request.preferred_end
    )

    if slot:
        fake_link = "https://meet.google.com/fake-link-xyz"
        
        # ✅ Compose the message
        message = (
            f"📅 New meeting scheduled!\n"
            f"👥 Attendees: {', '.join(request.attendees)}\n"
            f"🕒 Time: {slot}\n"
            f"🔗 Join: {fake_link}"
        )

        # ✅ Send to Slack
        await send_slack_message(message)

        return {
            "status": "success",
            "scheduled_time": slot,
            "meet_link": fake_link
        }
    else:
        return {"status": "error", "message": "No available slot found"}
    
