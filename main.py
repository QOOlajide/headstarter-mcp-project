from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from logic.meeting_orchestrator import schedule_meeting_workflow

load_dotenv()

app = FastAPI()

class MeetingRequest(BaseModel):
    attendees: list[str]
    duration_minutes: int = Field(gt=0, le=480)
    preferred_start: str
    preferred_end: str
    meeting_title: str
    meeting_description: str = ""

@app.post("/schedule-meeting")
async def schedule_meeting(request: MeetingRequest):
    try:
        return await schedule_meeting_workflow(
            attendees=request.attendees,
            duration_minutes=request.duration_minutes,
            preferred_start=request.preferred_start,
            preferred_end=request.preferred_end,
            meeting_title=request.meeting_title,
            meeting_description=request.meeting_description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {exc}") from exc


@app.get("/health")
async def health():
    return {"status": "ok"}