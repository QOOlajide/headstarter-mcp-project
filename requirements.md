# System Specification: Cross-Functional Meeting & Directive Automation Server

## 1. Executive Summary & Product Goals

This system provides an end-to-end meeting automation toolchain exposed via a Python-based Model Context Protocol (MCP) server. It enables any user to schedule cross-functional team meetings, dispatch automated calendar invitations with Google Meet conferencing, broadcast plain-text reminders to dynamically resolved Slack channels, and ingest live-scraped meeting captions to synthesize discussion summaries and relational actionable directives in Notion.

The system is optimized for zero-cost testing, zero third-party bot fees, and compatibility with free personal @gmail.com accounts.

---

## 2. System Architecture & Component Interactions

AI Client (Cursor LLM): Initiates tool execution by sending structured commands to the local MCP server over standard MCP transport (stdio / SSE).

Python MCP Server (FastMCP Core):

Local SQLite Cache (meeting_cache.db): Maintains persistent mappings (team_slug ↔ channel_id, active meeting state) to perform sub-millisecond local lookups without hitting external rate limits.
CREATE TABLE IF NOT EXISTS slack_channels (
    team_slug TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS active_meetings (
    meet_url TEXT PRIMARY KEY,
    notion_meeting_page_id TEXT NOT NULL,
    meeting_title TEXT NOT NULL,
    department TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

Tool Pipeline & Webhook Hub: Coordinates external API dispatches for scheduling, notification routing, and exposes a local webhook receiver (POST /webhook/transcript) for transcript ingestion.

Google Calendar API v3: Handles scheduling (conferenceDataVersion=1, sendUpdates="all"), generates the Google Meet video conferencing URL, and dispatches calendar invitations directly to invitee email addresses.

Slack Web API (chat.postMessage): Receives plain-text reminder payloads and routes them to auto-resolved public team channels (#team-slug) via bot token scopes.

Google Meet Browser Client (DOM Scraper): Enables live closed captions during the call; a client-side MutationObserver script captures streaming speaker/text updates from the DOM and sends a beacon webhook payload upon call exit.

Google Gemini API (gemini-3.1-flash-lite): Receives the raw transcript string and returns structured JSON containing discussion bullet points and an array of actionable directives.

Notion REST API: Receives structured output from Gemini to update the Meetings & Summaries database (appends summary notes to page blocks and marks status as "Completed") and creates linked entries in the Actionable Directives database via two-way relations.

End-to-End Information Flow
Scheduling & Setup:

Cursor LLM → triggers tool on Python MCP Server.

MCP Server queries Local SQLite Cache → retrieves or stores channel mappings.

MCP Server calls Google Calendar API → creates meeting, generates Google Meet link, and notifies attendees via email.

MCP Server calls Slack Web API → delivers plain-text reminder string into the resolved team channel.

Call Capture & Ingestion:

During the active call on Google Meet, native Live Captions render into the DOM.

A client-side MutationObserver extracts speaker-labeled text lines.

On call departure (beforeunload), the scraper issues a POST /webhook/transcript beacon back to the MCP Webhook Hub.

Synthesis & Storage:

MCP Server passes raw transcript to Google Gemini API.

Gemini parses the dialogue into summary points and structured action items with assignees and due dates.

MCP Server executes requests to the Notion REST API:

Appends discussion notes and updates status in the Meetings & Summaries database.

Inserts individual task items into the Actionable Directives database with dual-property relations linked back to the parent meeting page.


## 3. Data Models & Database Schemas
3.1 Local SQLite Cache (meeting_cache.db)


CREATE TABLE IF NOT EXISTS slack_channels (
    team_slug TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS active_meetings (
    meet_url TEXT PRIMARY KEY,
    notion_meeting_page_id TEXT NOT NULL,
    meeting_title TEXT NOT NULL,
    department TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


## 3.2 Notion Central Databases
Both databases are nested under a single shared Default Teamspace / Parent Page.

Database A: Meetings & Summaries
Meeting Name (title): Name of the meeting.

Department / Team (select): Engineering, Product, Sales, Design, Cross-Functional.

Slack Channel (rich_text): e.g., #eng-team.

Slack Channel ID (rich_text): e.g., C0123456789 (used for audit tracking).

Date & Time (date): Scheduled meeting start/end ISO timestamp.

Google Meet URL (url): Direct conference join link.

Status (select): Scheduled, Completed, Canceled.

Action Items (relation): Two-way relation targeting the Actionable Directives database.

Database B: Actionable Directives
Directive / Task (title): Action item description.

Assignee Email (rich_text): Target participant email address.

Priority (select): High, Medium, Low.

Due Date (date): Target completion date.

Status (status): To Do, In Progress, Done.

Source Meeting (relation): Two-way relation linking back to the parent row in Meetings & Summaries.

## 4. Detailed Component Implementation Specs
## 4.1 Google Calendar Integration (1 Google API for Scheduling)
API: Google Calendar API v3 (calendar.events.insert).

Parameters:

calendarId: "primary"

conferenceDataVersion: 1 (forces generation of hangoutsMeet conference URI).

sendUpdates: "all" (delivers calendar invites and notifications to attendees' email addresses).

Payload Structure:

JSON
{
  "summary": "Meeting Title",
  "start": { "dateTime": "2026-09-01T14:00:00Z" },
  "end": { "dateTime": "2026-09-01T14:30:00Z" },
  "attendees": [{"email": "alice@gmail.com"}, {"email": "bob@gmail.com"}],
  "conferenceData": {
    "createRequest": {
      "requestId": "unique-uuid-v4",
      "conferenceSolutionKey": { "type": "hangoutsMeet" }
    }
  }
}



## 4.2 Slack Channel Resolution & Notifications
Scopes Required: chat:write, chat:write.public, channels:read, channels:manage.

Slug Sanitization: re.sub(r'[^a-zA-Z0-9\s-]', '', name).strip().lower().

Execution Flow:

Check local SQLite cache: SELECT channel_id FROM slack_channels WHERE team_slug = ?.

Cache Miss: Call GET https://slack.com/api/conversations.list?types=public_channel.

Channel Non-Existent: Call POST https://slack.com/api/conversations.create with {"name": slug, "is_private": false}.

Write resolved (team_slug, channel_id) to SQLite.

Post message using POST https://slack.com/api/chat.postMessage with plain text payload to bypass Block Kit schema parsing:

JSON
{
  "channel": "C0123456789",
  "text": "Reminder: Engineering Sync starts in 10 minutes! Join Meet: https://meet.google.com/xyz-abcd-jkl"
}


## 4.3 Transcript Collection: Client-Side DOM Caption Scraper (Option 1)
Mechanism: Injected Userscript/Extension observing Live Closed Captions (MutationObserver) in meet.google.com.

JavaScript Scraper Code:

JavaScript
(function() {
  let transcriptBuffer = [];
  let lastSpokenText = "";

  const observer = new MutationObserver((mutations) => {
    // Observe active caption containers in Google Meet DOM
    const captionContainer = document.querySelector('div[jscontroller="D1tHje"]') || document.querySelector('.a4cQT');
    if (!captionContainer) return;

    const speakerEl = captionContainer.querySelector('.zs7s8d') || captionContainer.querySelector('.jxFHg');
    const textEl = captionContainer.querySelector('.iTTPOb') || captionContainer.querySelector('.CNhiyc');

    const speaker = speakerEl ? speakerEl.innerText.trim() : "Unknown";
    const text = textEl ? textEl.innerText.trim() : "";

    if (text && text !== lastSpokenText) {
      lastSpokenText = text;
      transcriptBuffer.push({ speaker, text, timestamp: new Date().toISOString() });
    }
  });

  observer.observe(document.body, { childList: true, subtree: true, characterData: true });

  // Webhook dispatch on meeting departure
  window.addEventListener("beforeunload", () => {
    if (transcriptBuffer.length === 0) return;

    const payload = JSON.stringify({
      meet_url: window.location.origin + window.location.pathname,
      transcript: transcriptBuffer.map(e => `[${e.timestamp}] ${e.speaker}: ${e.text}`).join("\n")
    });

    navigator.sendBeacon("http://127.0.0.1:8000/webhook/transcript", payload);
  });
})();



## 4.4 Synthesis (Google Gemini API)
Model: gemini-3.1-flash-lite via google-generativeai (override with GEMINI_MODEL; fallback candidate: gemini-2.5-flash-lite).

Configuration: generation_config={"response_mime_type": "application/json"}.

Extraction Schema:

{
  "summary_bullets": ["string"],
  "action_items": [
    {
      "task": "string",
      "assignee_email": "string",
      "priority": "High | Medium | Low",
      "due_date": "YYYY-MM-DD"
    }
  ]
}


## 4.5 Notion Synchronization
Append Summary to Meeting Record:
PATCH [https://api.notion.com/v1/blocks/](https://api.notion.com/v1/blocks/){meeting_page_id}/children

Appends an h2 header ("Summary & Key Decisions") and individual bulleted_list_item blocks for each point in summary_bullets.

Updates Status property on the page to "Completed".

Insert Relational Actionable Directives:
POST [https://api.notion.com/v1/pages](https://api.notion.com/v1/pages)

Targets Actionable Directives database ID.

Links Source Meeting relation property directly to [{"id": meeting_page_id}].




## Clarification
Meeting Scheduling Flow: Slack-First & Zero-Email Maintenance
The user triggers a scheduling request via natural language in Cursor. The MCP server branches based on the request type:

Routing & Channel Resolution (Slack API + SQLite)

Department Sync (e.g., "Schedule Eng sync for 3 PM"):

Checks the local SQLite cache for #eng-team. If not cached, it resolves the channel ID via conversations.list and caches it.

Assumes core team channels are pre-existing in the Slack workspace, avoiding manual user roster tracking.

Ad-Hoc / Specific People (e.g., "Schedule sync with @alex, @sam"):

Resolves the mentioned user handles to Slack User IDs (U1, U2) via users.list (or cached mapping).

Calls conversations.open(users="U1,U2") to dynamically retrieve or open a private multi-person group DM (MPIM) without littering the workspace with temporary public channels.

Google Calendar Event Creation (Google Calendar API v3)

Calls calendar.events.insert with conferenceDataVersion=1.

Leaves attendees: [] empty to bypass email maintenance and calendar permissions.

Extracts the auto-generated [meet.google.com/xyz-abcd-jkl](https://meet.google.com/xyz-abcd-jkl) conference URL from the response.

Link Dispatch (Slack API)

Calls chat.postMessage to send a plain-text notification containing the Google Meet link.

If a department channel was targeted, appends <!channel> to notify all members.

If an ad-hoc sync was targeted, posts the message directly into the opened group DM thread.
