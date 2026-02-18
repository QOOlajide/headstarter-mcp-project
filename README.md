# MCP Meeting Scheduler Server

An MCP (Model Context Protocol) server that automates end-to-end meeting scheduling by integrating Slack, Google Calendar, and Notion. This server allows AI assistants to schedule meetings, find available time slots, create calendar events with Google Meet links, send Slack notifications, and automatically create meeting notes pages in Notion.

## Features

- **Google Calendar Integration**: Finds available time slots and creates calendar events with Google Meet links
- **Slack Notifications**: Sends formatted meeting notifications to Slack channels
- **Notion Documentation**: Automatically creates meeting notes pages with agenda and action items
- **OAuth2 Authentication**: Secure authentication for all integrated services
- **MCP Protocol**: Compatible with AI assistants that support the Model Context Protocol

## Architecture

The server orchestrates a complete workflow:

1. **Find Available Slot**: Queries Google Calendar API to find shared available time slots
2. **Create Calendar Event**: Creates a Google Calendar event with Google Meet link
3. **Send Slack Notification**: Sends a formatted message to the configured Slack channel
4. **Create Notion Page**: Creates a meeting notes page in Notion with all meeting details

## Prerequisites

- Python 3.8 or higher
- Google Cloud Project with Calendar API enabled
- Slack workspace with a bot app installed
- Notion workspace with an integration created
- `uv` package manager (recommended) or `pip`

## Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd Headstarter-MCR-Project
   ```

2. **Install dependencies**:
   ```bash
   # Using uv (recommended)
   uv add "mcp[cli]"
   uv add fastapi uvicorn httpx python-dotenv
   uv add google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
   uv add notion-client
   
   # Or using pip
   pip install -r requirements.txt
   ```

3. **Set up Google Calendar API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Calendar API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download the credentials file and save it as `credentials.json` in the project root
   - Required scopes:
     - `https://www.googleapis.com/auth/calendar`
     - `https://www.googleapis.com/auth/calendar.events`

4. **Set up Slack Bot**:
   - Go to [Slack API](https://api.slack.com/apps)
   - Create a new app or use an existing one
   - Install the app to your workspace
   - Copy the Bot User OAuth Token (starts with `xoxb-`)
   - Required scopes: `chat:write`, `channels:read`

5. **Set up Notion Integration**:
   - Go to [Notion Integrations](https://www.notion.so/my-integrations)
   - Create a new integration
   - Copy the Internal Integration Token
   - Create a Notion database for meetings (or use an existing one)
   - Share the database with your integration
   - Copy the database ID from the database URL

6. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

## Configuration

Create a `.env` file in the project root with the following variables:

```env
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_CHANNEL=#general
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json
NOTION_API_KEY=secret_your-key-here
NOTION_DATABASE_ID=your-database-id-here
```

### Notion Database Schema

Your Notion database should have the following properties:
- **Title** (title): Meeting title
- **Date** (date): Scheduled meeting time
- **Duration** (rich_text): Meeting duration

The integration will automatically add content blocks for attendees, meeting link, agenda, action items, and notes.

## Usage

### Running the MCP Server

```bash
python mcp_server.py
```

The server communicates via stdio and follows the MCP protocol. It can be connected to MCP-compatible clients.

### Using with MCP Clients

The server exposes a single tool: `schedule_meeting`

**Tool Parameters**:
- `attendees` (array of strings): List of attendee email addresses
- `duration_minutes` (integer): Duration of the meeting in minutes
- `preferred_start` (string): Preferred start time in ISO format (e.g., "2025-06-28T09:00:00")
- `preferred_end` (string): Preferred end time in ISO format (e.g., "2025-06-28T17:00:00")
- `meeting_title` (string): Title of the meeting
- `meeting_description` (string, optional): Description/agenda for the meeting

**Example Tool Call**:
```json
{
  "name": "schedule_meeting",
  "arguments": {
    "attendees": ["alice@example.com", "bob@example.com"],
    "duration_minutes": 30,
    "preferred_start": "2025-06-28T09:00:00",
    "preferred_end": "2025-06-28T17:00:00",
    "meeting_title": "Project Planning Meeting",
    "meeting_description": "Discuss Q3 roadmap and priorities"
  }
}
```

### Testing Configuration

You can validate your configuration by running:

```python
from config import Config
Config.print_config_status()
```

## Project Structure

```
.
├── mcp_server.py              # Main MCP server entry point
├── main.py                    # FastAPI REST API entry point (/schedule-meeting)
├── config.py                  # Configuration management
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variable template
├── credentials.json          # Google OAuth credentials (not in repo)
├── token.json                # Google OAuth token (generated, not in repo)
├── auth/                     # Authentication modules
│   ├── __init__.py
│   ├── google_auth.py        # Google OAuth handler
│   ├── slack_auth.py         # Slack token validation
│   └── notion_auth.py        # Notion API key validation
└── logic/                    # Business logic modules
    ├── calendar_logic.py     # Calendar slot finding logic
    ├── google_calendar.py    # Google Calendar API client
    ├── slack_notifier.py     # Slack message sender
    ├── notion_client.py      # Notion API client
    └── meeting_orchestrator.py  # Workflow orchestrator
```

## Authentication Flow

### Google Calendar
1. First run: OAuth flow opens browser for authentication
2. Token is saved to `token.json`
3. Token is automatically refreshed when expired

### Slack
- Uses bot token from environment variables
- Token is validated on each API call

### Notion
- Uses API key from environment variables
- API key is validated on each API call

## Error Handling

The server includes comprehensive error handling:
- Falls back to mock calendar data if Google Calendar API is unavailable
- Validates all credentials before making API calls
- Provides clear error messages for missing configuration
- Handles API rate limits and timeouts gracefully

## Development

### Running Tests

```bash
# Validate configuration
python -c "from config import Config; Config.print_config_status()"

# Test individual modules
python -c "from logic.slack_notifier import validate_slack_config; validate_slack_config()"
```

### Adding New Features

1. Add new MCP tools in `mcp_server.py`
2. Implement business logic in `logic/` modules
3. Add authentication if needed in `auth/` modules
4. Update configuration in `config.py` if new env vars are needed

## Troubleshooting

### Google Calendar Authentication Issues
- Ensure `credentials.json` is in the project root
- Check that OAuth scopes include calendar permissions
- Delete `token.json` and re-authenticate if token is corrupted

### Slack Notifications Not Sending
- Verify `SLACK_BOT_TOKEN` is correct and starts with `xoxb-`
- Check that the bot is installed in your workspace
- Verify `SLACK_CHANNEL` exists and bot has access

### Notion Pages Not Creating
- Verify `NOTION_API_KEY` is correct
- Check that `NOTION_DATABASE_ID` is correct
- Ensure the integration has access to the database
- Verify database has required properties (Title, Date, Duration)

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

