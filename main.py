"""
FastAPI webhook hub + optional REST scheduling endpoint.
Exposes POST /webhook/transcript for Meet caption scraper beacons.
"""
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from logic.meeting_orchestrator import schedule_meeting_workflow

load_dotenv()

app = FastAPI(title="Meeting Automation Hub")


class MeetingRequest(BaseModel):
    meeting_title: str
    start_time: str
    duration_minutes: int = Field(default=30, gt=0, le=480)
    meeting_description: str = ""
    department: Optional[str] = "Cross-Functional"
    team_name: Optional[str] = None
    slack_handles: List[str] = Field(
        default_factory=list,
        description="Ad-hoc participants as Slack handles, e.g. ['alex','sam']",
    )


class TranscriptPayload(BaseModel):
    meet_url: str
    transcript: str


@app.post("/schedule-meeting")
async def schedule_meeting(request: MeetingRequest):
    try:
        return await schedule_meeting_workflow(
            meeting_title=request.meeting_title,
            start_time=request.start_time,
            duration_minutes=request.duration_minutes,
            meeting_description=request.meeting_description,
            department=request.department,
            team_name=request.team_name,
            slack_handles=request.slack_handles,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {exc}") from exc


@app.post("/webhook/transcript")
async def webhook_transcript(request: Request):
    """
    Ingest Meet caption scraper beacon.
    Maps Gemini assignees through Slack-extracted emails → Notion Assignee Email.
    """
    content_type = request.headers.get("content-type", "")
    try:
        if "application/json" in content_type:
            body = await request.json()
        else:
            raw = await request.body()
            import json

            body = json.loads(raw.decode("utf-8") if raw else "{}")
        payload = TranscriptPayload(**body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}") from exc

    if not payload.transcript.strip():
        return {"status": "ignored", "reason": "empty transcript"}

    from logic.gemini_synth import synthesize_transcript
    from logic.meeting_cache import delete_active_meeting, get_active_meeting, get_slack_user
    from logic.notion_client import sync_transcript_results
    from logic.slack_notifier import map_assignee_to_email

    meeting = get_active_meeting(payload.meet_url)
    if not meeting:
        meeting = get_active_meeting(payload.meet_url.rstrip("/"))
    if not meeting:
        raise HTTPException(
            status_code=404,
            detail=f"No active meeting cached for meet_url={payload.meet_url}",
        )

    known_emails = meeting.get("participant_emails") or []
    # Rebuild lightweight participant records from cached emails + slack_users
    participants = []
    for email in known_emails:
        participants.append({"email": email, "handle": email.split("@")[0], "display_name": ""})

    try:
        synthesized = synthesize_transcript(
            payload.transcript, known_emails=known_emails
        )
        action_items = []
        for item in synthesized.get("action_items", []):
            mapped = map_assignee_to_email(
                item.get("assignee_email", ""), participants
            )
            # If still not an email, try slack_users cache by handle
            if mapped and "@" not in mapped:
                cached = get_slack_user(mapped)
                if cached and cached.get("email"):
                    mapped = cached["email"]
            item = {**item, "assignee_email": mapped}
            action_items.append(item)

        notion_result = await sync_transcript_results(
            meeting_page_id=meeting["notion_meeting_page_id"],
            summary_bullets=synthesized.get("summary_bullets", []),
            action_items=action_items,
        )
        delete_active_meeting(meeting["meet_url"])
        return {
            "status": "ok",
            "meeting_title": meeting["meeting_title"],
            "notion_page_id": meeting["notion_meeting_page_id"],
            "summary_count": len(synthesized.get("summary_bullets", [])),
            "action_item_count": len(action_items),
            "mapped_assignees": [a.get("assignee_email") for a in action_items],
            "notion": notion_result,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Transcript processing failed: {exc}"
        ) from exc


@app.get("/health")
async def health():
    return {"status": "ok"}
