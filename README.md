# MCP Meeting Scheduler

Cursor MCP server that schedules meetings from natural language: Slack is the roster, Google Calendar holds the time and Meet link, Notion stores the row. A companion Chrome extension + FastAPI hub (optionally Docker) turn Meet captions into Notion summaries.

## What it does

1. **MCP `schedule_meeting`** — maps messy wording onto `department` and/or `slack_handles`.
2. **Slack** — department → team channel + `<!channel>`; ad-hoc → group DM. Emails from Slack profiles.
3. **Google Calendar** — Meet link + calendar hold for those emails (`sendUpdates=all`).
4. **Notion** — Scheduled row in Meetings & Summaries.
5. **After the call (companion)** — Chrome extension buffers Live Captions; on leave beacons to the FastAPI hub → Gemini → summary + Actionable Directives. Or MCP/REST `finalize_meeting` marks Completed with a no-transcript note.

## How the meeting time is chosen

Roster first, then time. **Team and ad-hoc differ on free/busy.**

| | Team (department) | Ad-hoc (`slack_handles`) |
|---|---|---|
| Exact `start_time` | Book it | Book it |
| `preferred_start` / `preferred_end` | Book at window start (no channel free/busy) | Free/busy those people in the window |
| No time | Next business-hours slot (9–17 in `SCHEDULER_TIMEZONE`) | Free/busy over default business windows |
| No shared free slot | N/A (never requires whole channel free) | Fail — create nothing |
| Calendar hold | Channel member emails | Named people emails |

Busy invitees can decline; that does not cancel a created team meeting. Env defaults: `SCHEDULER_TIMEZONE=America/New_York`, `SCHEDULER_SEARCH_DAYS=3`.

**Scale caveat:** free/busy only sees calendars the OAuth Google user can read. Use it for small guest lists, not whole channels.

## Two routing modes

| | Department | Ad-hoc |
|---|---|---|
| Trigger | `department` set, `slack_handles` empty | `slack_handles` non-empty (wins) |
| Slack | Existing public channel, `<!channel>` | Group DM |
| Calendar hold | Channel members with profile emails | Named people with profile emails |
| Notion `Department / Team` | The enum | Empty (people-only) |

### Department → Slack channel

| Department enum | Slack channel |
|---|---|
| Engineering | `#engineering` |
| Product | `#product` |
| Cloud | `#cloud` |
| Data Science | `#data-science` |
| Security | `#security` |

Bot must be **in** each channel.

## Setup

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

`.env`: `SLACK_BOT_TOKEN`, `NOTION_API_KEY`, `NOTION_MEETINGS_DATABASE_ID`, `NOTION_DIRECTIVES_DATABASE_ID`, `GEMINI_API_KEY`; optional `SCHEDULER_TIMEZONE`, `SCHEDULER_SEARCH_DAYS`. Google: `credentials.json` / `token.json`.

```powershell
.\venv\Scripts\python.exe scripts\setup_notion_dbs.py --parent-page-id "YOUR_PARENT_PAGE_URL" --write-env
```

MCP: `.cursor/mcp.json` (`envFile` → `.env`). Restart MCP after `.env` changes.

### Transcript hub (FastAPI)

Local debug:

```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Docker (same hub, portable; pass secrets via env — do not bake `.env` into the image):

```powershell
docker compose up --build
# or: docker build -t meeting-hub . && docker run --env-file .env -p 8000:8000 meeting-hub
```

Deploy the image to Render/Railway/Fly and set the same env vars. The hub resolves meetings by **Notion `Google Meet URL`** (SQLite is optional local cache only).

### Chrome extension

1. Chrome → Extensions → Load unpacked → select `extension/`
2. Options: set webhook URL (`http://127.0.0.1:8000/webhook/transcript` or your hosted URL)
3. Join Meet with **Live Captions** on; leave the call to beacon

Legacy one-off: paste `scripts/meet_caption_scraper.js` in the Meet console (same beacon contract).

### Finalize without transcript

- REST: `POST /finalize-meeting` with `{"meet_url":"..."}` or `{"notion_page_id":"..."}`
- MCP: `finalize_meeting` with the same fields  
Marks Status=Completed and appends a note that no transcript was received.

## MCP tools

**`schedule_meeting`** — `meeting_title` (required), optional `start_time`, `preferred_start`/`preferred_end`, `duration_minutes`, `department`, `slack_handles`. Omit `team_name`.

**`finalize_meeting`** — `meet_url` and/or `notion_page_id`.

## Layout

```
mcp_server.py                 MCP stdio + schedule_meeting + finalize_meeting
main.py                       FastAPI hub (schedule, transcript webhook, finalize)
Dockerfile / docker-compose.yml   Transcript hub container
extension/                    Chrome MV3 caption → webhook
scripts/meet_caption_scraper.js   Legacy console scraper
logic/meeting_orchestrator.py
logic/slack_notifier.py
logic/google_calendar.py
logic/notion_client.py
logic/gemini_synth.py
logic/meeting_cache.py
```

## Troubleshooting

- Slack `channel_not_found`: bot not in channel, or stale `meeting_cache.db`.
- Notion property errors: wrong DB IDs / schema (see `journal.md` for Notion 2026).
- Transcript 404: Meet URL must match Notion `Google Meet URL`; hub must be reachable from the browser.
- Pip `resolution-too-deep`: use lower bounds in `requirements.txt`.
