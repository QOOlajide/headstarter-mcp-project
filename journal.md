# Project Journal — Manual Setup Steps

A running log of what I had to do by hand to stand up the Meeting & Directive Automation stack. No secrets are recorded here — only variable *names* and actions.

---

## 1. Spec & decisions

- Defined the system in `requirements.md` (MCP scheduling, Slack-first routing, Meet captions → Gemini → Notion).
- Recorded architecture tradeoffs in `adr.md` (SQLite channel cache, plain-text Slack, DOM caption scraping, Meetings `Status` kept as **select**).
- Clarified Slack-first flow: Calendar creates the Meet link with empty attendees; Slack distributes the link (department channel or ad-hoc group DM); emails for Notion assignees come from Slack profiles.

---

## 2. Environment file (`.env`)

Created / maintained `.env` with these keys (values omitted):

| Variable | Purpose |
|---|---|
| `SLACK_BOT_TOKEN` | Bot token for channel resolve + messaging |
| `SLACK_CHANNEL` | Legacy fallback channel (optional with Slack-first routing) |
| `NOTION_API_KEY` | Internal integration secret |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth client (informational; runtime uses `credentials.json`) |
| `GEMINI_API_KEY` | Transcript → summary/action-items synthesis |
| `NOTION_MEETINGS_DATABASE_ID` | Filled by setup script |
| `NOTION_DIRECTIVES_DATABASE_ID` | Filled by setup script |

`.env` is gitignored and must never be committed.

---

## 3. Slack

- Created / used a Slack app with a bot token.
- Installed the app to the workspace.
- Needed scopes for this design (verify in Slack app settings):
  - Messaging / channels: `chat:write`, `chat:write.public`, `channels:read`, `channels:manage`
  - Users / emails: `users:read`, `users:read.email`
  - Ad-hoc DMs: scopes that allow `conversations.open` (e.g. `im:write` / `mpim:write` as required by Slack)
- Department sync assumes public channels already exist (not auto-created). This workspace uses `#engineering` (mapped in `DEPT_CHANNEL_SLUGS`); the original spec slug `#eng-team` was wrong here.

---

## 4. Google Calendar / Meet

- Enabled Google Calendar API on a Google Cloud project.
- Created **Desktop** OAuth client credentials.
- Downloaded the client secret JSON and saved it in the project root as `credentials.json` (gitignored).
- Matched `.env` Google client id/secret to that same OAuth client.
- First successful Calendar API call opens a browser OAuth consent flow and writes `token.json` (also gitignored). Until then, Meet link creation can’t complete.

---

## 5. Gemini

- Obtained a Gemini API key and set `GEMINI_API_KEY` in `.env`.
- Used for post-meeting JSON extraction (`summary_bullets` + `action_items`) before Notion writes.

---

## 6. Notion (manual + scripted)

### Manual

1. Created an Internal Integration in Notion (e.g. “Quamdeen's meeting connection”) and copied the API key into `NOTION_API_KEY`.
2. Created an empty parent page in the workspace, e.g. **Meeting Automation**.
3. Opened the page → `•••` → **Connections** → connected the integration to that page.
   - Without this step, the API returns `404 object_not_found` even with a valid page URL.
4. Copied the page URL (or page id) for the setup script.

Example page URL shape (id redacted in spirit — use your own):

`https://app.notion.com/p/Meeting-Automation-<page-id>`

### Scripted database provisioning

Use the project venv interpreter so `httpx` / dotenv match this repo (not system Python):

```powershell
.\venv\Scripts\python.exe scripts\setup_notion_dbs.py --parent-page-id "https://app.notion.com/p/Meeting-Automation-<YOUR_PAGE_ID>" --write-env
```

What this did:

- Created **Meetings & Summaries** and **Actionable Directives** under the parent page.
- Wired the two-way relation (`Source Meeting` ↔ `Action Items`).
- With `--write-env`, wrote `NOTION_MEETINGS_DATABASE_ID` and `NOTION_DIRECTIVES_DATABASE_ID` into `.env`.

Notes:

- Omit `--write-env` if you only want the IDs printed so you can paste them yourself.
- First attempt failed with 404 until the parent page was shared with the integration; after connecting, the same command succeeded.
- The script **creates new databases**; it does not patch existing empty tables. Delete leftover blank DBs in Notion after a successful run.
- Restart the Cursor MCP server after `.env` IDs change so scheduling picks them up.

---

## 7. Local code pieces that support the run

- `logic/meeting_cache.py` — SQLite: Slack channels, Slack users/emails, active Meet URL → Notion page.
- `logic/slack_notifier.py` — channel/user resolve, plain-text posts, email → Notion assignee mapping.
- `logic/google_calendar.py` — event + Meet link (`attendees` empty in Slack-first mode).
- `logic/notion_client.py` — schedule row + post-call summary/directives.
- `logic/gemini_synth.py` — transcript → structured JSON.
- `main.py` — FastAPI hub including `POST /webhook/transcript`.
- `mcp_server.py` — Cursor MCP `schedule_meeting` tool.
- `scripts/meet_caption_scraper.js` — Meet Live Captions → beacon to local webhook.
- `scripts/setup_notion_dbs.py` — one-time Notion schema provisioning.

---

## 8. How to run (after the above)

1. **Webhook hub** (needed for transcript ingestion):

   ```powershell
   uvicorn main:app --host 127.0.0.1 --port 8000
   ```

2. **MCP server** — already configured via `.cursor/mcp.json` pointing at `mcp_server.py` + `.env`.

3. **Caption scraper** — inject/load `scripts/meet_caption_scraper.js` on `meet.google.com` with **Live Captions** enabled; on leave it beacons to `http://127.0.0.1:8000/webhook/transcript`.

4. Schedule via MCP / Cursor natural language, e.g.:
   - Department: Eng sync at a start time → posts Meet link to `#engineering` with `<!channel>`.
   - Ad-hoc: sync with `@alex`, `@sam` → opens group DM, extracts Slack emails for later Notion assignees.

---

## 9. End-to-end mental model (for explaining later)

1. Cursor → MCP `schedule_meeting`.
2. Slack resolves target (channel or MPIM) and caches channel/user/email data.
3. Google Calendar creates event + Meet URL (no email invite list).
4. Slack posts the Meet link.
5. Notion gets a Scheduled meeting row (metadata + Meet URL).
6. Meet URL is cached → Notion page id (+ participant emails).
7. During call: DOM scraper buffers captions.
8. On leave: webhook receives transcript → Gemini structures it → Notion summary + Actionable Directives (`Assignee Email` from Slack-mapped emails).

---

## 10. Still worth verifying manually

- [ ] First Google OAuth browser login → `token.json` created.
- [ ] Slack scopes include user email read + DM open.
- [ ] Department channels (e.g. `#engineering`) exist in the workspace; bot is in the channel.
- [ ] Uvicorn listening on `127.0.0.1:8000` before ending a Meet with the scraper.
- [ ] Live Captions on during the call for the scraper host browser.
- [ ] Notion Meetings DB in the UI actually shows columns (`Meeting Name`, `Department / Team`, …), not an empty table.
- [ ] MCP reloaded after the last `--write-env` so it is not still using old database IDs.

---

## 11. Notion API `2026-03-11` — database vs data source

`scripts/setup_notion_dbs.py` and `logic/notion_client.py` send `Notion-Version: 2026-03-11`. As of the [2025-09-03 upgrade](https://developers.notion.com/reference/database), a **database** is a container on the parent page; **columns and rows live on a child data source**.

### Empty databases (properties never applied)

First successful creates showed two DBs on **Meeting Automation** with **no columns**. Cause: the create payload put the schema at the old root key `"properties"`. This version ignores that field and still returns 200 + a database id.

Fix: nest the schema under `initial_data_source`:

```json
{
  "parent": { "type": "page_id", "page_id": "..." },
  "title": [{ "type": "text", "text": { "content": "Meetings & Summaries" } }],
  "initial_data_source": { "properties": { "...": {} } }
}
```

`create_meeting_page` only **inserts a row**. It does not add columns. If the target DB has no schema, Notion returns `validation_error` listing every property as missing (`Meeting Name`, `Department / Team`, `Slack Channel`, …). That is a schema/ID mismatch, not a bad insert payload.

Scheduling is pointed at Notion only via `.env` (`NOTION_MEETINGS_DATABASE_ID` / `NOTION_DIRECTIVES_DATABASE_ID`) loaded by `.cursor/mcp.json` `envFile`. There is no extra “link this database” step in Cursor.

### Relation create failed: `data_source_id` undefined

Meetings create succeeded; Actionable Directives failed with:

`body.initial_data_source.properties.Source Meeting.relation.data_source_id should be defined, instead was undefined`

The script stored `meetings_db["id"]` (the **database** container) and passed it as `relation.database_id` (old API). Relations now must point at the **table**: `relation.data_source_id`.

That data source id is already in the create-database **response** — a second create call is not required:

```json
{
  "id": "<database id>",
  "data_sources": [{ "id": "<data source id>", "name": "..." }]
}
```

`first_data_source_id()` reads `data_sources[0].id`. `.env` still stores the database ids; the data source id is only needed when creating the `Source Meeting` relation (`type: dual_property`, reverse name `Action Items`).

Mental model: database = the Notion page titled Meetings & Summaries; data source = the actual table (columns + rows). A relation is “link to a row in **that table**.”
