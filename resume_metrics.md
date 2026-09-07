# Resume Metrics — Meeting Automation Pipeline

Ideas for measuring and presenting impact from this project. Prefer numbers you can actually time or count; don’t invent scale you don’t have.

---

## Core metrics (easy to claim honestly)

| Metric | How to measure | Why it lands on a resume |
|---|---|---|
| **End-to-end time** | Phone timer: schedule → Slack notify → notes/action items in Notion | “Reduced X‑min manual workflow to ~Y sec/min” |
| **Steps eliminated** | Count clicks/apps: Calendar + Slack + Notion + copy-paste transcript | “Collapsed N tools / M manual steps into 1 MCP call” |
| **Post-meeting lag** | Time from leaving Meet → Notion summary + tasks appear | Shows async automation value, not just scheduling |

---

## Stronger impact angles

| Metric | How | Resume framing |
|---|---|---|
| **Human touch time** | Only time *you* spend (prompt + join Meet); exclude machine time | “~Z minutes of human effort per meeting” |
| **Error / rework rate** | Missed invites, wrong channel, forgotten action items (before vs after) | Reliability, not just speed |
| **Cost** | $0 bots/transcription (vs paid options like Recall.ai — see ADR 003) | “Zero marginal $ for captions/scheduling path” |
| **Assignee resolution** | % of action items with a real Slack-derived email in Notion | Data quality of the pipeline |
| **Cache hit rate** | Slack channel/user lookups served from SQLite vs API | Engineering depth (optional; more “systems” than product) |

---

## Fair comparison protocol

1. Do **one** meeting fully **manual** (timer on): create calendar event, Meet link, Slack ping, after-call notes + tasks in Notion.
2. Do the **same** meeting via **MCP + scraper + webhook** (timer: from tool call until Notion rows exist).
3. Report both, and explicitly note what you still do by hand (join Meet, turn on Live Captions).

### Suggested fill-in table

| Step | Manual (mm:ss) | Automated (mm:ss) |
|---|---|---|
| Create event + Meet link | | |
| Notify team in Slack | | |
| Capture / write summary | | |
| Create action items in Notion | | |
| **Total wall-clock** | | |
| **Human-only effort** | | |

---

## Resume-ready pattern (fill in your numbers)

> Built an MCP meeting automation pipeline (Calendar → Slack → Gemini → Notion) that cut scheduling + post-meeting documentation from **~A min manual** to **~B min**, with **$0** third-party transcription cost and structured action items written to Notion with Slack-mapped assignees.

Optional extras if true for your run:

- Collapsed **N** tools / **M** manual steps into a single MCP invocation.
- Post-meeting Notion sync in **~C sec** after leaving the call.
- **D%** of action items auto-assigned with Slack profile emails.

---

## Worth exploring later (if you instrument the code)

- p50 / p95 latency of `schedule_meeting` and `POST /webhook/transcript`
- Meetings processed per week during a pilot
- % of directives marked Done in Notion (adoption; harder to attribute)

---

## Priority for this project

Focus on these three first — they read as impact without needing a large user base:

1. **A vs B wall-clock** (manual vs pipeline)
2. **Steps / tools removed**
3. **$0 caption path** (vs paid bot transcription)

---

## Measured results (fill in after timing)

| Date | Scenario | Manual total | Automated total | Notes |
|---|---|---|---|---|
| | Department sync | | | |
| | Ad-hoc (@handles) | | | |
| | Full path incl. transcript → Notion | | | |
