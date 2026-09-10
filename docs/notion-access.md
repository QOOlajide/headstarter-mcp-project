# Notion access (not per-meeting invites)

## Decision

Do **not** invite meeting attendees to Notion per schedule call. Do **not** treat Calendar attendees or Slack emails as a way to grant Notion access.

Notion is the **system of record** (meeting row, summary, action items). Slack and Google Calendar are how people learn about and join the meeting.

## One-time setup (humans)

Share the parent page (or Meetings & Summaries + Actionable Directives) once with:

- “Everyone at [workspace]”, or
- a Team / group that covers the people who should see meeting notes

Anyone already in that Notion workspace then sees new rows automatically. No per-meeting share loop.

Workspace membership / guest invites for people outside Notion stay an **org onboarding** concern, not something the scheduler does on every call.

## What the product already does

| Surface | Role |
|---|---|
| Slack | Roster + Meet link (channel or group DM) |
| Google Calendar | Timed hold / invite for Slack-profile emails |
| Notion (API) | Integration writes the meeting row; later transcript → summary + directives |

Writing emails into a Notion property (or listing Calendar attendees) only **stores data**. It does not open page permissions.

Sharing the page with the **Notion integration** is for the bot token so code can write. That is separate from sharing with teammates.

## (MUST DO LATER) (not required for transcription tests)

- Put the Notion meeting page URL in the Slack reminder and/or Calendar description so people who already have access can click through.
- Surface action items back to Slack if attendees should not live in Notion.

## Explicit non-goals

- Auto-invite every Calendar attendee as a Notion guest on schedule
- Per-meeting “Share” clicks in the Notion UI
- Using free/busy or attendee lists as a substitute for workspace permissions

## Transcription testing

Run the caption scraper → `POST /webhook/transcript`. Watch the Meetings & Summaries row (and Actionable Directives) in Notion as someone who already has access to that database. Attendees do not need Notion to join the Meet.
