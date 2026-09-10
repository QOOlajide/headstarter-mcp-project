"""
MCP Meeting Scheduler Server
Main entry point for the Model Context Protocol server
"""
import asyncio
from typing import Any, Sequence

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from config import Config

load_dotenv()
Config.print_config_status()

server = Server("meeting-scheduler")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="schedule_meeting",
            description=(
                "Slack-first meeting scheduler. User wording is often informal or "
                "misspelled; map it to canonical tool arguments when the intent is "
                "unambiguous (e.g. 'engineer team' → Engineering, 'alx' → alex). "
                "Do not invent people or teams the user did not name. "
                "Department mode: set department enum, omit slack_handles, post Meet "
                "link to the department Slack channel with <!channel>. Team meetings "
                "do NOT free/busy the whole channel — exact start_time, else start of "
                "preferred window, else next business-hours slot; then invite channel. "
                "Ad-hoc mode: set slack_handles for named people, omit department, "
                "open a group DM. Free/busy those people when no exact time is given; "
                "if no shared slot, fail (create nothing). "
                "Time rules: exact time → start_time. Range → preferred_start + "
                "preferred_end. No time → omit all three. NEVER invent a clock time "
                "the user did not give for ad-hoc free/busy failures. Creates a "
                "Calendar event with Meet + Slack-profile emails as attendees. "
                "Omit team_name."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "meeting_title": {
                        "type": "string",
                        "description": "Title of the meeting",
                    },
                    "start_time": {
                        "type": "string",
                        "format": "date-time",
                        "description": (
                            "Exact meeting start (ISO 8601 with UTC offset). Set ONLY "
                            "when the user gave a specific time. If they gave a range "
                            "or no time, omit this."
                        ),
                    },
                    "preferred_start": {
                        "type": "string",
                        "format": "date-time",
                        "description": (
                            "Start of a window (ISO with offset). Team: book at this "
                            "time (must fit duration before preferred_end). Ad-hoc: "
                            "free/busy search window start. Requires preferred_end. "
                            "Omit start_time when using this."
                        ),
                    },
                    "preferred_end": {
                        "type": "string",
                        "format": "date-time",
                        "description": (
                            "End of the window (ISO with offset). "
                            "Pair with preferred_start."
                        ),
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration in minutes (default 30)",
                    },
                    "meeting_description": {
                        "type": "string",
                        "description": "Optional description/agenda",
                    },
                    "department": {
                        "type": "string",
                        "enum": [
                            "Engineering",
                            "Product",
                            "Cloud",
                            "Data Science",
                            "Security",
                        ],
                        "description": (
                            "Canonical department for Slack channel routing and Notion. "
                            "Map informal/misspelled team language when unambiguous: "
                            "'eng', 'engineer team' → Engineering; 'prod' → Product; "
                            "'infra' → Cloud; 'ds', 'ml' → Data Science; 'infosec' → "
                            "Security. Do not invent a department from the meeting "
                            "title alone. Required for department mode. Omit when "
                            "scheduling with named people via slack_handles."
                        ),
                    },
                    "team_name": {
                        "type": "string",
                        "description": (
                            "Ignored. Do not set. Informal team phrases are not "
                            "Slack slugs; use department instead."
                        ),
                    },
                    "slack_handles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Ad-hoc participants the user named. Emit canonical Slack "
                            "handles (no @). Unambiguous typos are ok: 'alx' → alex. "
                            "Do not pass prose like 'the frontend folks'. Non-empty "
                            "list selects ad-hoc mode (group DM) instead of the "
                            "department channel."
                        ),
                    },
                },
                "required": ["meeting_title"],
            },
        ),
        Tool(
            name="finalize_meeting",
            description=(
                "Mark a scheduled Notion meeting Completed when no transcript "
                "was captured. Appends a note that summary/action items were "
                "skipped. Pass meet_url (Google Meet link) and/or "
                "notion_page_id. Use after a call ends without the caption "
                "extension/webhook path."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "meet_url": {
                        "type": "string",
                        "description": "Google Meet URL from the scheduled event",
                    },
                    "notion_page_id": {
                        "type": "string",
                        "description": "Meetings & Summaries page id if known",
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> Sequence[TextContent]:
    """Handle tool calls"""
    arguments = arguments or {}
    if name == "schedule_meeting":
        try:
            from logic.meeting_orchestrator import schedule_meeting_workflow

            result = await schedule_meeting_workflow(
                meeting_title=arguments.get("meeting_title", "Meeting"),
                start_time=arguments.get("start_time"),
                preferred_start=arguments.get("preferred_start"),
                preferred_end=arguments.get("preferred_end"),
                duration_minutes=arguments.get("duration_minutes", 30),
                meeting_description=arguments.get("meeting_description", ""),
                department=arguments.get("department"),
                team_name=arguments.get("team_name"),
                slack_handles=arguments.get("slack_handles") or [],
            )
            return [
                TextContent(
                    type="text",
                    text=f"Meeting scheduled successfully!\n{result}",
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"Error scheduling meeting: {str(e)}",
                )
            ]
    if name == "finalize_meeting":
        try:
            from logic.meeting_cache import delete_active_meeting, get_active_meeting
            from logic.notion_client import (
                finalize_meeting_without_transcript,
                find_meeting_page_by_meet_url,
            )

            meet_url = arguments.get("meet_url")
            notion_page_id = arguments.get("notion_page_id")
            if not meet_url and not notion_page_id:
                raise ValueError("Provide meet_url or notion_page_id")

            meeting_title = "Meeting"
            if not notion_page_id and meet_url:
                cached = get_active_meeting(meet_url) or get_active_meeting(
                    meet_url.rstrip("/")
                )
                if cached:
                    notion_page_id = cached["notion_meeting_page_id"]
                    meeting_title = cached.get("meeting_title") or meeting_title
                    meet_url = cached.get("meet_url") or meet_url
                else:
                    page = await find_meeting_page_by_meet_url(meet_url)
                    if not page:
                        raise ValueError(f"No meeting found for meet_url={meet_url}")
                    notion_page_id = page["id"]
                    meeting_title = page["meeting_title"]

            result = await finalize_meeting_without_transcript(notion_page_id)
            if meet_url:
                delete_active_meeting(meet_url)
            return [
                TextContent(
                    type="text",
                    text=(
                        f"Meeting finalized without transcript.\n"
                        f"title={meeting_title} page={notion_page_id}\n{result}"
                    ),
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"Error finalizing meeting: {str(e)}",
                )
            ]
    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
