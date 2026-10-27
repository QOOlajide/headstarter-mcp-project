# MCP Meeting Scheduler

> Natural language meeting orchestration via Cursor MCP — combining Slack rosters, Google Calendar scheduling, and Notion meeting records with live Google Meet caption synthesis.

---

## Demo: End-to-End Execution Flow

[![MCP Meeting Scheduler Demo](assets/demo.gif)](assets/linkedin_demo_v2_proof_chain.mp4)

**What the demo demonstrates:**
1. **Cursor Dispatch:** Natural language prompt schedules a meeting via local MCP stdio.
2. **Slack Confirmation:** The MCP posts to the designated team channel (or group DM) with `<!channel>` and the Google Meet URL.
3. **Notion State:** A new meeting record is created in `Scheduled` status.
4. **Live Call Capture:** The Chrome MV3 extension intercepts native Google Meet Live Captions in real time.
5. **Synthesis on Call Exit:** Leaving the call beacons the transcript to the local FastAPI hub $\\rightarrow$ Gemini synthesizes directives $\\rightarrow$ updates the Notion record to `Completed` with Actionable Directives.

---

## Architecture

```text
Cursor Composer / Agent (Local MCP via stdio)
       │
       ├──> Slack API (Roster lookup & Channel Broadcast)
       ├──> Google Calendar API (Free/busy search & Meet invite)
       └──> Notion API (Creates initial "Scheduled" meeting row)

Google Meet Call
       │
       └──> Chrome MV3 Extension (Buffers Live Captions)
                 │ (beacon on call exit)
                 ▼
       FastAPI Hub (Docker Container / Local Port 8000)
                 │
                 ├──> Google Gemini API (Action Items & Meeting Summary)
                 └──> Notion API (Populates Directives & marks "Completed")

```

---

## How Meeting Slots are Selected

Roster first, then time. **Team and ad-hoc routing differ on free/busy lookups:**

| Scenario | Team (`department`) | Ad-hoc (`slack_handles`) |
| --- | --- | --- |
| **Exact `start_time**` | Book it immediately | Book it immediately |
| **`preferred_start` / `preferred_end**` | Book at window start (no channel free/busy) | Query free/busy for named attendees |
| **No time provided** | Next business-hours slot (9–17 in `SCHEDULER_TIMEZONE`) | Query free/busy over default business windows |
| **No shared free slot** | N/A (never requires entire channel to be free) | Fails gracefully — creates nothing |
| **Calendar Hold** | Channel member profile emails | Named attendee profile emails |

> **Scale Note:** Google Calendar free/busy only checks calendars readable by the authenticated OAuth user. Use ad-hoc lookups for targeted attendee sets rather than entire large channels.

---

## Routing & Channel Mapping

| Routing Mode | Trigger | Slack Target | Calendar Hold | Notion Department |
| --- | --- | --- | --- | --- |
| **Department** | `department` set, `slack_handles` empty | Public Channel + `<!channel>` | Channel members | Selected Enum |
| **Ad-hoc** | `slack_handles` provided (takes precedence) | Group DM | Named handles | Empty (People-only) |

### Supported Department Mappings

* `Engineering` $\rightarrow$ `#engineering`
* `Product` $\rightarrow$ `#product`
* `Cloud` $\rightarrow$ `#cloud`
* `Data Science` $\rightarrow$ `#data-science`
* `Security` $\rightarrow$ `#security`

*(Note: The Slack Bot must be a member of each target channel).*

---

## Local Setup & Installation

*Requires Python 3.10+ (Python 3.12 recommended).*

### 1. Create a Project-Local Virtual Environment

Do not reuse `venv/` across operating systems. Windows and macOS/Linux use different internal folder layouts.

| OS | Create Environment | Install Dependencies | Cursor MCP Command |
| --- | --- | --- | --- |
| **macOS / Linux** | `python3.12 -m venv venv` | `./venv/bin/python -m pip install -r requirements.txt` | `${workspaceFolder}/venv/bin/python` |
| **Windows** | `py -3.12 -m venv venv` | `.\\venv\\Scripts\\python.exe -m pip install -r requirements.txt` | `${workspaceFolder}/venv/Scripts/python.exe` |

> `requirements.txt` pins `mcp[cli]>=1.21.1,<2` to prevent pip from installing MCP SDK v2, ensuring stability with this project's `@server.list_tools()` decorator.

### 2. Configure Environment & Notion Databases

Create a `.env` file in the repository root:

```env
SLACK_BOT_TOKEN=xoxb-...
GEMINI_API_KEY=AIza...
NOTION_API_KEY=secret_...
NOTION_MEETINGS_DATABASE_ID=...
NOTION_DIRECTIVES_DATABASE_ID=...
SCHEDULER_TIMEZONE=America/New_York
SCHEDULER_SEARCH_DAYS=3

```

Place your Google Cloud OAuth credentials at `credentials.json`.

To automatically provision the Notion databases with the required schema:

```bash
# macOS / Linux
./venv/bin/python scripts/setup_notion_dbs.py --parent-page-id "<PARENT_PAGE_ID>" --write-env

# Windows
.\\venv\\Scripts\\python.exe scripts\\setup_notion_dbs.py --parent-page-id "<PARENT_PAGE_ID>" --write-env

```

### 3. Hook up Local MCP Server in Cursor

Cursor communicates with the MCP server locally over standard I/O (`stdio`).

1. In Cursor, open **Settings $\rightarrow$ Customize $\rightarrow$ MCP Servers** (or edit `.cursor/mcp.json` directly).
2. Configure the server pointing directly to your **local venv interpreter**:

```json
{
  "mcpServers": {
    "meeting-scheduler": {
      "command": "${workspaceFolder}/venv/bin/python",
      "args": ["${workspaceFolder}/mcp_server.py"],
      "envFile": "${workspaceFolder}/.env"
    }
  }
}

```

*(On Windows, set `"command"` to `"${workspaceFolder}/venv/Scripts/python.exe"`).*

3. Click **Refresh** in Cursor's MCP section. Verify `schedule_meeting` and `finalize_meeting` appear with active status indicators.

### 4. Run the Transcript Processing Hub (Dockerized)

The FastAPI hub is containerized to handle webhook ingestion, transcription processing, and Gemini summarization independently of host environments.

```bash
# Recommended: Run via Docker Compose
docker compose up --build -d

# Check live container logs
docker compose logs -f

```

The service binds to `http://127.0.0.1:8000`. The container automatically reads your `.env` variables and respects Chrome's private-network access headers.

```bash
# macOS / Linux
./venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Windows
.\\venv\\Scripts\\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

```

### 5. Install & Configure the Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`.
2. Enable **Developer mode** in the top-right corner.
3. Click **Load unpacked** and select the `extension/` directory from this repository.
4. Click the extension's **Options** page and verify the Webhook URL:
```text
[http://127.0.0.1:8000/webhook/transcript](http://127.0.0.1:8000/webhook/transcript)

```


5. **During the call:** Turn **Live Captions** (`cc`) on in Google Meet. When you leave or end the call, the extension automatically beacons the buffer to your FastAPI hub.

---

## MCP Tool Reference

* `schedule_meeting`:
* `meeting_title` *(string, required)*: Subject of the meeting.
* `department` *(string, optional)*: Target department channel (`Engineering`, `Product`, etc.).
* `slack_handles` *(string[], optional)*: List of attendee handles (e.g. `["@alice", "@bob"]`).
* `start_time` *(string, optional)*: Explicit ISO start time.
* `preferred_start` / `preferred_end` *(string, optional)*: Candidate search window.
* `duration_minutes` *(int, optional)*: Meeting length (default: `15`).


* `finalize_meeting`:
* Marks a meeting `Completed` in Notion if no transcript arrived or if manual closeout is required. Accepts `meet_url` or `notion_page_id`.



---

## Project Structure & Deep Dives

```text
├── mcp_server.py                 # MCP stdio interface (schedule_meeting, finalize_meeting)
├── main.py                       # FastAPI webhook hub & auto-finalization scheduler
├── Dockerfile                    # Container definition for transcript hub
├── docker-compose.yml            # Docker orchestration for port 8000 binding
├── extension/                    # Chrome MV3 extension (Google Meet captions -> webhook)
├── scripts/
│   ├── setup_notion_dbs.py       # Automated Notion DB provisioning
│   └── meet_caption_scraper.js   # Legacy manual console scraper
└── logic/
    ├── meeting_orchestrator.py   # Core routing and free/busy business logic
    ├── slack_notifier.py         # Slack API integration (channels, group DMs, roster lookup)
    ├── google_calendar.py        # Calendar API free/busy search & invite generation
    ├── notion_client.py          # Notion SDK database & directive records
    ├── gemini_synth.py           # Gemini API prompt parsing & directive extraction
    └── meeting_cache.py          # Local SQLite cache for channel IDs and user handles

```

For detailed architectural decisions and integration notes, consult:

* **[Architectural Decision Records (`adr.md`)](adr.md):** Detailed trade-offs regarding Slack-first routing, SQLite local caching strategies, and free/busy attendee scaling boundaries.
* **[Implementation Journal (`journal.md`)](journal.md):** Notion API 2026 data source updates, property mapping nuances, and debugging lessons.
* **[Test Suite Guide (`TESTING.md`)](TESTING.md):** Mocking Google Calendar and Slack responses for isolated local testing.

---

## Known Setup Errors & Solutions

* **`spawn .../venv/Scripts/python.exe EACCES` (macOS):** Occurs when `.cursor/mcp.json` points to the Windows executable path on a Unix environment. Ensure the macOS configuration points to `venv/bin/python`.
* **`Could not find a version that satisfies the requirement mcp`:** The `mcp` package requires Python $\ge$ 3.10. Re-create the virtual environment using Python 3.10 or 3.12.
* **`AttributeError: 'Server' object has no attribute 'list_tools'`:** Pip installed MCP SDK v2 while `mcp_server.py` uses the v1 API. Ensure `mcp[cli]>=1.21.1,<2` is pinned in `requirements.txt`.
* **`Transcript Webhook 404 / CORS error`:** The Google Meet URL in Notion must match the URL generated by Google Calendar, and Docker/Uvicorn must be running with port 8000 exposed to localhost.
"""
