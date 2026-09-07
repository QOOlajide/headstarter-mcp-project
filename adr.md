
# ADR 001: Storage Strategy for Slack Channel 

LookupsStatus: Accepted
Context: Channel IDs are required by Slack's chat.postMessage. Resolving IDs through API lists or querying Notion databases introduces network overhead and rate-limit consumption.

Decision: Implement a local SQLite key-value store.

Tradeoffs & Rationale:
- Pro: Cuts lookup latency to < 1 ms (eliminating 250–600 ms HTTP overhead per meeting action).
- Pro: Eliminates Notion API query rate-limit consumption (limited to ≈ 3 req/sec).
- Con: Cache state is local to the server host; requires initial API fallback on cache miss.

# ADR 002: Notification Formatting via Plain Strings vs. Block Kit

Status: Accepted

Context: Slack Block Kit formatting introduces schema complexity, JSON serialization overhead, and strict validation error states.

Decision: Restrict all chat.postMessage payloads to top-level plain/mrkdwn strings (text parameter).

Tradeoffs & Rationale:
- Pro: Eliminates payload validation crashes (invalid_blocks, msg_blocks_too_long).
- Pro: Minimizes token context consumption and payload size.
- Con: Loses advanced interactive UI elements (buttons, date pickers) directly in the Slack feed.

# ADR 003: Browser-Side Live Caption Scraping (Option 1) for Transcript Ingestion

Status: Accepted

Context: Automated Google Meet transcription via official APIs requires paid Google Workspace Enterprise tiers. Third-party bot APIs (Recall.ai) incur continuous per-minute operational costs.

Decision: Capture free real-time Closed Captions from the Google Meet browser DOM via a MutationObserver script that dispatches a Beacon webhook to the local server upon call exit.

Tradeoffs & Rationale:
- Pro: 100% zero financial cost. Works on personal @gmail.com accounts.
- Pro: No visible third-party bot enters the call room.
- Con (Technical Debt): Fragile. If Google alters frontend DOM obfuscation/class selectors, the scraper observer breaks and requires selector updates.
- Con: Captions must be toggled on during the meeting for DOM nodes to generate.

# ADR 004: Meetings & Summaries Status remains `select` (not `status`)

Status: Accepted

Context: Notion offers both select and status property types. Status has nicer workflow UX; Actionable Directives already uses status. It is reasonable to ask whether Meetings `Status` (Scheduled / Completed / Canceled) should match.

Why you might consider `status`:
- Native board/timeline “workflow” UI in Notion.
- Same mental model as Directives’ Status.
- Feels more like a lifecycle than a tag.

Decision: Keep Meetings `Status` as `select`, as specified in requirements.md §3.2.

Why remain with `select`:
- Spec already defines it as select with fixed labels — no ambiguity for provisioning or clients.
- Meeting states here are discrete outcomes/labels (Scheduled, Completed, Canceled), not a multi-stage task pipeline with In Progress groups.
- Select options are fully controllable and stable via the API; status option/group customization is more constrained.
- Avoids an unnecessary schema + payload change (`"select"` → `"status"`) across setup and `notion_client` for little functional gain.
- Keeps Meetings vs Directives intentionally different: meetings = categorical state; directives = work progress.

Tradeoffs:
- Con: UI is a flat select chip instead of Status boards.
- Pro: Spec fidelity, simpler API writes, fewer Notion edge cases.
