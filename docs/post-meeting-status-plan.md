# Post-meeting status without transcript

## Status

Implemented (including auto-finalize while the FastAPI hub is running).

- `logic/notion_client.py` → `finalize_meeting_without_transcript`
- REST `POST /finalize-meeting` in `main.py`
- MCP tool `finalize_meeting` in `mcp_server.py`
- Background loop `logic/auto_finalize.py` started from FastAPI lifespan

## Behavior

When the meeting is over **but** no transcript arrived:

1. Set Meetings & Summaries `Status` → `Completed`
2. Append a page note:

> No transcript was received for this meeting. Status marked Completed without summary or action items.

Do not invent a summary or action items.

When a transcript **does** arrive via `/webhook/transcript`, summary + directives run as usual and Status becomes `Completed`.

## How to trigger

- **Automatic (preferred):** keep the hub running (`uvicorn`). After scheduled end time + grace (`AUTO_FINALIZE_GRACE_MINUTES`, default 5), overdue `Scheduled` Notion rows (and local SQLite active meetings) are finalized.
- Explicit: MCP `finalize_meeting` or `POST /finalize-meeting` with `meet_url` or `notion_page_id`
- Manual tick: `POST /auto-finalize/run`
- Lookup: SQLite active-meeting cache, else Notion filter on `Status=Scheduled` + past `Date & Time`

Env knobs: `AUTO_FINALIZE_ENABLED` (default true), `AUTO_FINALIZE_GRACE_MINUTES` (default 0 — flip as soon as end time passes), `AUTO_FINALIZE_POLL_SECONDS` (30).

Notion API 2026 queries use `/v1/data_sources/{id}/query` (resolved from the meetings database id, or `NOTION_MEETINGS_DATA_SOURCE_ID`).

## Relation to MCP scope

Core MCP remains Slack + Calendar + Notion **scheduling**. Finalize and the caption extension + hosted hub are post-meeting hygiene / companion infra.
