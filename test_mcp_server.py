"""
Test suite for MCP Meeting Scheduler Server
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from mcp.types import Tool, TextContent
from mcp_server import list_tools, call_tool, server


class TestListTools:
    """Test the list_tools function"""
    
    @pytest.mark.asyncio
    async def test_list_tools_returns_schedule_meeting_tool(self):
        """Test that list_tools returns the schedule_meeting tool"""
        tools = await list_tools()
        
        assert len(tools) == 1
        assert isinstance(tools[0], Tool)
        assert tools[0].name == "schedule_meeting"
        assert "Schedule a meeting" in tools[0].description
        
        # Check input schema
        schema = tools[0].inputSchema
        assert schema["type"] == "object"
        assert "attendees" in schema["properties"]
        assert "duration_minutes" in schema["properties"]
        assert "preferred_start" in schema["properties"]
        assert "preferred_end" in schema["properties"]
        assert "meeting_title" in schema["properties"]
        assert "meeting_description" in schema["properties"]


class TestCallTool:
    """Test the call_tool function"""
    
    @pytest.mark.asyncio
    async def test_call_tool_schedule_meeting_success(self):
        """Test successful meeting scheduling"""
        mock_result = {
            "status": "success",
            "scheduled_time": "2025-06-28T10:00:00",
            "meet_link": "https://meet.google.com/abc-defg-hij",
            "calendar_event_id": "event123",
            "notion_page_id": "page456",
            "slack_message_sent": True
        }
        
        arguments = {
            "attendees": ["alice@example.com", "bob@example.com"],
            "duration_minutes": 30,
            "preferred_start": "2025-06-28T09:00:00",
            "preferred_end": "2025-06-28T17:00:00",
            "meeting_title": "Test Meeting",
            "meeting_description": "Test description"
        }
        
        with patch('logic.meeting_orchestrator.schedule_meeting_workflow', new_callable=AsyncMock) as mock_workflow:
            mock_workflow.return_value = mock_result
            
            result = await call_tool("schedule_meeting", arguments)
            
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert result[0].type == "text"
            assert "Meeting scheduled successfully" in result[0].text
            assert "success" in result[0].text
            
            # Verify workflow was called with correct arguments
            mock_workflow.assert_called_once_with(
                attendees=["alice@example.com", "bob@example.com"],
                duration_minutes=30,
                preferred_start="2025-06-28T09:00:00",
                preferred_end="2025-06-28T17:00:00",
                meeting_title="Test Meeting",
                meeting_description="Test description"
            )
    
    @pytest.mark.asyncio
    async def test_call_tool_schedule_meeting_with_defaults(self):
        """Test meeting scheduling with default values"""
        mock_result = {
            "status": "success",
            "scheduled_time": "2025-06-28T10:00:00",
            "meet_link": "https://meet.google.com/abc-defg-hij"
        }
        
        arguments = {
            "attendees": ["alice@example.com"],
            "duration_minutes": 30,
            "preferred_start": "2025-06-28T09:00:00",
            "preferred_end": "2025-06-28T17:00:00",
            "meeting_title": "Test Meeting"
            # meeting_description not provided
        }
        
        with patch('logic.meeting_orchestrator.schedule_meeting_workflow', new_callable=AsyncMock) as mock_workflow:
            mock_workflow.return_value = mock_result
            
            result = await call_tool("schedule_meeting", arguments)
            
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            
            # Verify default values were used
            mock_workflow.assert_called_once_with(
                attendees=["alice@example.com"],
                duration_minutes=30,
                preferred_start="2025-06-28T09:00:00",
                preferred_end="2025-06-28T17:00:00",
                meeting_title="Test Meeting",
                meeting_description=""  # Default empty string
            )
    
    @pytest.mark.asyncio
    async def test_call_tool_schedule_meeting_error_handling(self):
        """Test error handling when scheduling fails"""
        arguments = {
            "attendees": ["alice@example.com"],
            "duration_minutes": 30,
            "preferred_start": "2025-06-28T09:00:00",
            "preferred_end": "2025-06-28T17:00:00",
            "meeting_title": "Test Meeting"
        }
        
        with patch('logic.meeting_orchestrator.schedule_meeting_workflow', new_callable=AsyncMock) as mock_workflow:
            mock_workflow.side_effect = ValueError("No available time slot found")
            
            result = await call_tool("schedule_meeting", arguments)
            
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert result[0].type == "text"
            assert "Error scheduling meeting" in result[0].text
            assert "No available time slot found" in result[0].text
    
    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self):
        """Test error handling for unknown tool"""
        with pytest.raises(ValueError, match="Unknown tool"):
            await call_tool("unknown_tool", {})
    


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])

