"""
MCP Meeting Scheduler Server
Main entry point for the Model Context Protocol server
"""
import asyncio
from typing import Any, Sequence
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv
from config import Config

# Load environment variables
load_dotenv()

# Print configuration status on startup
Config.print_config_status()

# Initialize MCP server
server = Server("meeting-scheduler")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="schedule_meeting",
            description="Schedule a meeting by finding available time slots, creating a calendar event with Google Meet link, sending Slack notification, and creating Notion meeting notes page",
            inputSchema={
                "type": "object",
                "properties": {
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of attendee email addresses"
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration of the meeting in minutes"
                    },
                    "preferred_start": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Preferred start time in ISO format (e.g., 2025-06-28T09:00:00)"
                    },
                    "preferred_end": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Preferred end time in ISO format (e.g., 2025-06-28T17:00:00)"
                    },
                    "meeting_title": {
                        "type": "string",
                        "description": "Title of the meeting"
                    },
                    "meeting_description": {
                        "type": "string",
                        "description": "Optional description/agenda for the meeting"
                    }
                },
                "required": ["attendees", "duration_minutes", "preferred_start", "preferred_end", "meeting_title"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> Sequence[TextContent]:
    """Handle tool calls"""
    if name == "schedule_meeting":
        try:
            # Import here to avoid circular dependencies
            from logic.meeting_orchestrator import schedule_meeting_workflow
            
            result = await schedule_meeting_workflow(
                attendees=arguments.get("attendees", []),
                duration_minutes=arguments.get("duration_minutes", 30),
                preferred_start=arguments.get("preferred_start"),
                preferred_end=arguments.get("preferred_end"),
                meeting_title=arguments.get("meeting_title", "Meeting"),
                meeting_description=arguments.get("meeting_description", "")
            )
            
            return [
                TextContent(
                    type="text",
                    text=f"Meeting scheduled successfully!\n{result}"
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"Error scheduling meeting: {str(e)}"
                )
            ]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Main entry point for the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())

