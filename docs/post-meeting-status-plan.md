# Post-meeting status without transcript

## Status

Implemented.

- `logic/notion_client.py` → `finalize_meeting_without_transcript`
- REST `POST /finalize-meeting` in `main.py`
- MCP tool `finalize_meeting` in `mcp_server.py`

## Behavior

When the meeting is over **but** no transcript arrived:

1. Set Meetings & Summaries `Status` → `Completed`
2. Append a page note:

> No transcript was received for this meeting. Status marked Completed without summary or action items.

Do not invent a summary or action items.

When a transcript **does** arrive via `/webhook/transcript`, summary + directives run as usual and Status becomes `Completed`.

## How to trigger

- Explicit: MCP `finalize_meeting` or `POST /finalize-meeting` with `meet_url` or `notion_page_id`
- Lookup: SQLite active-meeting cache, else Notion filter on `Google Meet URL`

Auto-finalize on Calendar end time is still out of scope.

## Relation to MCP scope

Core MCP remains Slack + Calendar + Notion **scheduling**. Finalize and the caption extension + hosted hub are post-meeting hygiene / companion infra.
