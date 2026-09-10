# Roadmap: local MCP → “ChatGPT everywhere”

## Where we are (iteration 1 — done / in progress)

A **local stdio MCP** that Cursor runs on the builder’s machine:

- Tools: `schedule_meeting`, `finalize_meeting`
- Integrations: Slack roster + notify, Google Calendar hold + Meet, Notion row
- Companion (not MCP): Chrome extension → FastAPI hub (Docker-ready) for captions → Gemini → Notion
- Team meetings: no full-channel free/busy; ad-hoc: free/busy named people
- Secrets: per-machine `.env` / Google OAuth files
- Notion DBs: provisioned via `scripts/setup_notion_dbs.py`
- Slack channels: assumed pre-existing; bot must be invited

This is a valid agile vertical slice: chat → tool → real workspace side effects.

## What “ChatGPT everywhere” means

One **hosted** meeting-scheduler MCP that users attach from **any MCP client that supports remote servers** (ChatGPT connectors, Claude, Gemini CLI, Cursor, etc.), then fulfill requests in chat without cloning the repo or pasting bot tokens into a local `.env`.

Important transport split:

| Client style | How it reaches your server |
|---|---|
| Cursor / Claude Desktop / many IDEs | Local **stdio** *or* remote **HTTPS** |
| ChatGPT (and most web AIs) | **Remote HTTPS only** (Streamable HTTP / SSE) — will not start `python mcp_server.py` on the user’s laptop |

So “everywhere” requires a **public HTTPS MCP endpoint**, not only local stdio. See also typical ChatGPT connector setup (Developer mode → paste remote MCP URL).

Local stdio stays useful for development and Cursor demos. It is not the distribution end state.

## What does *not* change

Product logic already built should carry forward:

- Department vs ad-hoc routing and calendar holds
- Time rules (team skips channel free/busy; ad-hoc free/busy or fail)
- Notion as system of record; Slack as roster
- Caption extension + hub for post-meeting notes
- Finalize-without-transcript behavior

Remote MCP is a **new delivery layer** around the same workflows — not a rewrite of scheduling rules.

## What *does* change for distribution

| Today | Target |
|---|---|
| User runs MCP locally | You host MCP over HTTPS |
| `.env` with Slack/Notion/Google keys | **OAuth Connect** (or equivalent) per user/tenant |
| Manual Notion setup script | After Notion Connect, **auto-provision** Meetings + Directives DBs (same schema as setup script) |
| Manual Slack channels + invite bot | After Slack Connect: **auto-create** department channels and/or a settings UI to map “Engineering → #channel”; prefer creating as the bot so membership is solved |
| Transcript hub Docker = REST webhook only | Same host (or sibling service) also exposes **MCP HTTP transport**; webhook URL still used by the extension |
| “Only load the extension” for transcripts | Scheduling from ChatGPT also needs **Connect MCP** once; extension remains for captions |

Remote MCP removes local server grunt. It does **not** magically create Slack/Notion structure unless onboarding **provisioning jobs** do that after OAuth.

## Migration plan (iterative)

### Phase A — Keep shipping local (current)

- Cursor + `.env` demo path
- Extension + optional Docker hub for transcripts
- Document honestly: BYO credentials, pre-made channels / setup script

### Phase B — Host the HTTP surface

- Deploy FastAPI hub (already Dockerized) for `/webhook/transcript`, `/finalize-meeting`, health
- Add **MCP over Streamable HTTP/SSE** on the same (or adjacent) service, wrapping existing `schedule_meeting` / `finalize_meeting` logic
- Prove: Cursor *or* a tunnel can call the **remote** MCP URL (still single-tenant secrets OK for first deploy)

### Phase C — Multi-client “Connect”

- ChatGPT: Developer mode → Connectors → paste `https://…/mcp` ([remote MCP pattern](https://hjarni.com/blog/how-to-use-mcp-with-chatgpt))
- Claude / Gemini / others: same URL or `mcp-remote` bridge where the client is stdio-only
- Auth: start with a shared bearer token for demos; then **OAuth 2.1** per platform expectations

### Phase D — Real “Connect Slack / Notion / Google”

- OAuth for Slack (and later Google Calendar, Notion)
- Per-user token store; tool calls use **that** user’s tokens
- Post-Connect provisioning:
  - Notion: create parent page or use picker → create dual databases / data sources (API 2026-03-11)
  - Slack: create or map department channels; ensure bot membership
- Optional settings UI: channel map, timezone, hub URL for the extension

### Phase E — Polish

- Tenant isolation, token refresh/revoke, rate limits
- Chrome Web Store extension pointed at production webhook
- One-pager: “Connect MCP → Connect Slack/Notion/Google → chat”

## Onboarding story (target UX)

1. User adds your remote MCP URL in ChatGPT / Claude / Cursor / etc.  
2. Completes OAuth (“Connect Slack”, etc.).  
3. Your backend provisions Notion schema and Slack channel map (no hand-built tables required).  
4. User types: “Schedule an Engineering sync tomorrow at 3.”  
5. Optional: install extension once for captions → hosted webhook.

## Non-goals for early phases

- Pretending local stdio works inside ChatGPT  
- Requiring every end user to run uvicorn or edit `.env`  
- Full ChatGPT Apps Directory listing before a working remote URL + OAuth MVP  

## One-line summary

**Now:** great local MCP + real integrations.  
**Next:** host MCP on HTTPS.  
**Then:** OAuth + auto-provision so “everywhere” feels like Connect, not clone-and-configure.
