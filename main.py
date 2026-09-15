"""
FastAPI webhook hub + optional REST scheduling endpoint.
Exposes POST /webhook/transcript for Meet caption scraper beacons
and POST /finalize-meeting when no transcript arrives.
"""
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from logic.meeting_orchestrator import schedule_meeting_workflow

load_dotenv()

app = FastAPI(title="Meeting Automation Hub")

# Meet pages and the extension post JSON here. Without CORS (and Chrome's
# private-network opt-in for a public page calling localhost) the browser
# blocks the preflight and the transcript never reaches this server.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(https://meet\.google\.com|chrome-extension://.*)$",
    allow_methods=["*"],
    allow_headers=["*"],
    allow_private_network=True,
)


class MeetingRequest(BaseModel):
    meeting_title: str
    start_time: Optional[str] = None  # exact ISO time; omit for team default / ad-hoc freebusy
    preferred_start: Optional[str] = None
    preferred_end: Optional[str] = None
    duration_minutes: int = Field(default=30, gt=0, le=480)
    meeting_description: str = ""
    department: Optional[str] = None  # required unless slack_handles is set
    team_name: Optional[str] = None
    slack_handles: List[str] = Field(
        default_factory=list,
        description="Ad-hoc participants as Slack handles, e.g. ['alex','sam']",
    )


class TranscriptPayload(BaseModel):
    meet_url: str
    transcript: str


class FinalizeMeetingRequest(BaseModel):
    meet_url: Optional[str] = None
    notion_page_id: Optional[str] = None


async def _resolve_meeting_context(meet_url: Optional[str] = None, notion_page_id: Optional[str] = None):
    """SQLite active meeting first, then Notion Google Meet URL lookup."""
    from logic.meeting_cache import get_active_meeting
    from logic.notion_client import find_meeting_page_by_meet_url

    if notion_page_id:
        return {
            "notion_meeting_page_id": notion_page_id,
            "meeting_title": "Meeting",
            "meet_url": meet_url or "",
            "participant_emails": [],
            "source": "notion_page_id",
        }

    if not meet_url:
        return None

    meeting = get_active_meeting(meet_url)
    if not meeting:
        meeting = get_active_meeting(meet_url.rstrip("/"))
    if meeting:
        return {**meeting, "source": "sqlite"}

    page = await find_meeting_page_by_meet_url(meet_url)
    if not page:
        return None
    return {
        "notion_meeting_page_id": page["id"],
        "meeting_title": page["meeting_title"],
        "meet_url": page["meet_url"],
        "participant_emails": [],
        "source": "notion",
    }


@app.post("/schedule-meeting")
async def schedule_meeting(request: MeetingRequest):
    try:
        return await schedule_meeting_workflow(
            meeting_title=request.meeting_title,
            start_time=request.start_time,
            preferred_start=request.preferred_start,
            preferred_end=request.preferred_end,
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
    Ingest Meet caption scraper / extension beacon.
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
    from logic.meeting_cache import delete_active_meeting, get_slack_user
    from logic.notion_client import sync_transcript_results
    from logic.slack_notifier import map_assignee_to_email

    meeting = await _resolve_meeting_context(meet_url=payload.meet_url)
    if not meeting:
        raise HTTPException(
            status_code=404,
            detail=f"No meeting found for meet_url={payload.meet_url}",
        )

    known_emails = meeting.get("participant_emails") or []
    participants = []
    for email in known_emails:
        participants.append(
            {"email": email, "handle": email.split("@")[0], "display_name": ""}
        )

    try:
        synthesized = synthesize_transcript(
            payload.transcript, known_emails=known_emails
        )
        action_items = []
        for item in synthesized.get("action_items", []):
            mapped = map_assignee_to_email(
                item.get("assignee_email", ""), participants
            )
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
        if meeting.get("meet_url"):
            delete_active_meeting(meeting["meet_url"])
        return {
            "status": "ok",
            "meeting_title": meeting["meeting_title"],
            "notion_page_id": meeting["notion_meeting_page_id"],
            "resolved_via": meeting.get("source"),
            "summary_count": len(synthesized.get("summary_bullets", [])),
            "action_item_count": len(action_items),
            "mapped_assignees": [a.get("assignee_email") for a in action_items],
            "notion": notion_result,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Transcript processing failed: {exc}"
        ) from exc


@app.post("/finalize-meeting")
async def finalize_meeting(request: FinalizeMeetingRequest):
    """Mark Completed with a no-transcript note when captions never arrived."""
    if not request.meet_url and not request.notion_page_id:
        raise HTTPException(
            status_code=400,
            detail="Provide meet_url or notion_page_id",
        )

    from logic.meeting_cache import delete_active_meeting
    from logic.notion_client import finalize_meeting_without_transcript

    meeting = await _resolve_meeting_context(
        meet_url=request.meet_url,
        notion_page_id=request.notion_page_id,
    )
    if not meeting:
        raise HTTPException(
            status_code=404,
            detail="No meeting found for the given meet_url / notion_page_id",
        )

    try:
        result = await finalize_meeting_without_transcript(
            meeting["notion_meeting_page_id"]
        )
        if meeting.get("meet_url"):
            delete_active_meeting(meeting["meet_url"])
        return {
            "status": "ok",
            "notion_page_id": meeting["notion_meeting_page_id"],
            "meeting_title": meeting.get("meeting_title"),
            "resolved_via": meeting.get("source"),
            "notion": result,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Finalize failed: {exc}"
        ) from exc


@app.get("/health")
async def health():
    return {"status": "ok"}
