# Testing Guide for MCP Server

This guide explains how to test the MCP Meeting Scheduler Server.

## Prerequisites

Install the test dependencies:

```bash
pip install -r requirements.txt
```

This will install `pytest` and `pytest-asyncio` needed for running the tests.

## Running Tests

### Quick Start (Windows)

**Important**: Make sure to activate your virtual environment first!

**PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
python test_simple.py
```

**Or use the helper script:**
```powershell
.\run_tests.ps1
```

**Command Prompt:**
```cmd
venv\Scripts\activate.bat
python test_simple.py
```

**Or use the helper script:**
```cmd
run_tests.bat
```

### Option 1: Simple Test Script (Quick Check)

Run the simple test script to quickly verify basic functionality:

**Make sure virtual environment is activated first:**
```bash
# Activate venv (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate venv (Windows CMD)
venv\Scripts\activate.bat

# Activate venv (Linux/Mac)
source venv/bin/activate

# Then run tests
python test_simple.py
```

This script:
- Tests that `list_tools()` returns the correct tool
- Tests `call_tool()` with mocked dependencies
- Tests error handling for unknown tools

### Option 2: Full Test Suite with pytest

Run the comprehensive test suite:

```bash
pytest test_mcp_server.py -v
```

Or run with more detailed output:

```bash
pytest test_mcp_server.py -v --tb=short
```

### Option 3: Run Specific Tests

Run a specific test class:

```bash
pytest test_mcp_server.py::TestListTools -v
```

Run a specific test:

```bash
pytest test_mcp_server.py::TestCallTool::test_call_tool_schedule_meeting_success -v
```

## Test Coverage

The test suite covers:

1. **Tool Listing** (`TestListTools`)
   - Verifies `schedule_meeting` tool is returned
   - Validates tool schema structure

2. **Tool Execution** (`TestCallTool`)
   - Successful meeting scheduling
   - Default parameter handling
   - Error handling when scheduling fails
   - Unknown tool error handling

## Manual Testing

### Testing with MCP Client

To test the server with an actual MCP client:

1. Start the server:
   ```bash
   python mcp_server.py
   ```

2. The server communicates via stdio, so it needs to be connected to an MCP-compatible client.

### Testing Tool Call Directly

You can also test the tool functions directly in Python:

```python
import asyncio
from mcp_server import list_tools, call_tool

async def test():
    # List available tools
    tools = await list_tools()
    print(f"Available tools: {[t.name for t in tools]}")
    
    # Call the tool (requires mocked dependencies or real API keys)
    result = await call_tool("schedule_meeting", {
        "attendees": ["test@example.com"],
        "duration_minutes": 30,
        "preferred_start": "2025-06-28T09:00:00",
        "preferred_end": "2025-06-28T17:00:00",
        "meeting_title": "Test Meeting"
    })
    print(result)

asyncio.run(test())
```

## Mocking Dependencies

The tests use `unittest.mock` to mock external dependencies:
- Google Calendar API calls
- Slack API calls
- Notion API calls
- Meeting orchestrator workflow

This allows testing without requiring actual API credentials or making real API calls.

## Continuous Integration

To integrate tests into CI/CD:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest test_mcp_server.py -v
```

## Troubleshooting

### Import Errors

If you see import errors, make sure you're running from the project root directory and that all dependencies are installed.

### Async Test Errors

Make sure `pytest-asyncio` is installed. Tests are marked with `@pytest.mark.asyncio` to handle async functions.

### Mock Errors

If mocks aren't working, verify the import path matches where the function is actually imported from. The `schedule_meeting_workflow` is imported inside `call_tool()`, so we patch `logic.meeting_orchestrator.schedule_meeting_workflow`.

