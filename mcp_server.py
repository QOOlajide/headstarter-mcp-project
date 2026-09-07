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
                "Slack-first meeting scheduler. Department sync posts a Meet link to "
                "#engineering (etc.) with <!channel>. Ad-hoc sync resolves Slack @handles, "
                "opens a group DM, extracts profile emails for Notion assignees, and "
                "creates a Calendar event with empty attendees (Meet link only)."
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
                        "description": "Meeting start time (ISO)",
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
                            "Sales",
                            "Design",
                            "Cross-Functional",
                        ],
                        "description": (
                            "Department sync mode: resolves existing #engineering style channel"
                        ),
                    },
                    "team_name": {
                        "type": "string",
                        "description": "Optional override for Slack channel slug source",
                    },
                    "slack_handles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Ad-hoc mode: Slack handles like 'alex', 'sam' "
                            "(opens MPIM and extracts emails for Notion)"
                        ),
                    },
                },
                "required": ["meeting_title", "start_time"],
            },
        )
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
