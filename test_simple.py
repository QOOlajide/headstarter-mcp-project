"""
Simple test script to manually test the MCP server
Run this to quickly verify the server is working
"""
import asyncio
import sys
from mcp_server import list_tools, call_tool


async def test_list_tools():
    """Test listing available tools"""
    print("Testing list_tools()...")
    try:
        tools = await list_tools()
        print(f"✓ Found {len(tools)} tool(s)")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:50]}...")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_call_tool_mock():
    """Test calling the tool with mocked dependencies"""
    print("\nTesting call_tool() with mocked dependencies...")
    
    # Mock the schedule_meeting_workflow
    from unittest.mock import AsyncMock, patch
    
    mock_result = {
        "status": "success",
        "scheduled_time": "2025-06-28T10:00:00",
        "meet_link": "https://meet.google.com/test-meeting",
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
    
    try:
        with patch('logic.meeting_orchestrator.schedule_meeting_workflow', new_callable=AsyncMock) as mock_workflow:
            mock_workflow.return_value = mock_result
            
            result = await call_tool("schedule_meeting", arguments)
            
            print(f"✓ Tool call successful")
            print(f"  Result: {result[0].text[:100]}...")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_unknown_tool():
    """Test error handling for unknown tool"""
    print("\nTesting unknown tool error handling...")
    try:
        await call_tool("unknown_tool", {})
        print("✗ Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"✓ Correctly raised ValueError: {e}")
        return True
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("MCP Server Simple Tests")
    print("=" * 60)
    
    results = []
    
    # Test 1: List tools
    results.append(await test_list_tools())
    
    # Test 2: Call tool with mock
    results.append(await test_call_tool_mock())
    
    # Test 3: Unknown tool
    results.append(await test_unknown_tool())
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Tests passed: {sum(results)}/{len(results)}")
    print("=" * 60)
    
    if all(results):
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

