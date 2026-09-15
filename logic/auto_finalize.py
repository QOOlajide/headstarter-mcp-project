"""
Background auto-finalize for meetings that ended without a transcript.

While the FastAPI hub is running, periodically:
1. Finalize SQLite active meetings past ends_at + grace
2. Finalize Notion rows still Status=Scheduled past Date & Time end + grace

Transcript beacons win if they arrive first (they mark Completed and clear cache).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("auto_finalize")


def _grace_minutes() -> int:
    # Default 0: flip Status as soon as end time has passed.
    # Set AUTO_FINALIZE_GRACE_MINUTES=5 if you want a buffer for late transcripts.
    raw = os.getenv("AUTO_FINALIZE_GRACE_MINUTES", "0")
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def _poll_seconds() -> int:
    raw = os.getenv("AUTO_FINALIZE_POLL_SECONDS", "30")
    try:
        return max(10, int(raw))
    except ValueError:
        return 30


def _enabled() -> bool:
    return os.getenv("AUTO_FINALIZE_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


async def run_auto_finalize_once() -> dict[str, Any]:
    """Finalize overdue Scheduled meetings. Safe to call repeatedly."""
    from logic.meeting_cache import (
        delete_active_meeting,
        list_due_active_meetings,
    )
    from logic.notion_client import (
        finalize_meeting_without_transcript,
        list_overdue_scheduled_meetings,
    )

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=_grace_minutes())
    finalized: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_page_ids: set[str] = set()

    # Local cache first (fast path for meetings booked on this machine).
    for meeting in list_due_active_meetings(cutoff):
        page_id = meeting.get("notion_meeting_page_id")
        if not page_id or page_id in seen_page_ids:
            continue
        seen_page_ids.add(page_id)
        try:
            result = await finalize_meeting_without_transcript(page_id)
            if meeting.get("meet_url"):
                delete_active_meeting(meeting["meet_url"])
            finalized.append(
                {
                    "source": "sqlite",
                    "page_id": page_id,
                    "title": meeting.get("meeting_title"),
                    "result": result,
                }
            )
        except Exception as exc:  # noqa: BLE001 — keep loop alive
            errors.append(f"sqlite:{page_id}:{exc}")
            logger.exception("Auto-finalize failed for cached meeting %s", page_id)

    # Notion is source of truth (covers hosts without cache / missing ends_at).
    try:
        overdue = await list_overdue_scheduled_meetings(cutoff)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"notion_query:{exc}")
        logger.exception("Auto-finalize Notion query failed")
        overdue = []

    for meeting in overdue:
        page_id = meeting.get("id")
        if not page_id or page_id in seen_page_ids:
            continue
        seen_page_ids.add(page_id)
        try:
            result = await finalize_meeting_without_transcript(page_id)
            meet_url = meeting.get("meet_url") or ""
            if meet_url:
                delete_active_meeting(meet_url)
                delete_active_meeting(meet_url.rstrip("/"))
            finalized.append(
                {
                    "source": "notion",
                    "page_id": page_id,
                    "title": meeting.get("meeting_title"),
                    "result": result,
                }
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"notion:{page_id}:{exc}")
            logger.exception("Auto-finalize failed for Notion meeting %s", page_id)

    return {
        "cutoff": cutoff.isoformat(),
        "finalized_count": len(finalized),
        "finalized": finalized,
        "errors": errors,
    }


async def auto_finalize_loop(stop_event: asyncio.Event) -> None:
    if not _enabled():
        logger.info("Auto-finalize disabled (AUTO_FINALIZE_ENABLED)")
        return

    logger.info(
        "Auto-finalize started (grace=%sm poll=%ss)",
        _grace_minutes(),
        _poll_seconds(),
    )
    while not stop_event.is_set():
        try:
            summary = await run_auto_finalize_once()
            if summary["finalized_count"] or summary["errors"]:
                logger.info("Auto-finalize tick: %s", summary)
        except Exception:  # noqa: BLE001
            logger.exception("Auto-finalize tick crashed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=_poll_seconds())
        except asyncio.TimeoutError:
            continue
