"""
Slack Integration
Sends meeting notifications to Slack workspace channels with rich formatting
"""
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import httpx

load_dotenv()

SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")

def validate_slack_config() -> bool:
    """Validate that Slack configuration is present"""
    if not SLACK_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN not found in environment variables")
    if not SLACK_CHANNEL:
        raise ValueError("SLACK_CHANNEL not found in environment variables")
    return True

async def send_slack_message(
    text: str,
    channel: Optional[str] = None,
    use_blocks: bool = True
) -> Dict[str, Any]:
    """
    Send a message to Slack channel
    Supports both plain text and rich block formatting
    """
    validate_slack_config()
    
    target_channel = channel or SLACK_CHANNEL
    headers = {
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Use rich blocks for better formatting if enabled
    if use_blocks and "\n" in text:
        # Parse the message to create blocks
        lines = text.split("\n")
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📅 Meeting Scheduled"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text
                }
            },
            {
                "type": "divider"
            }
        ]
        payload = {
            "channel": target_channel,
            "blocks": blocks,
            "text": text  # Fallback text
        }
    else:
        payload = {
            "channel": target_channel,
            "text": text
        }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                json=payload,
                headers=headers
            )
            response_data = response.json()
            
            if not response_data.get("ok"):
                error_msg = response_data.get("error", "Unknown error")
                print(f"❌ Slack error: {error_msg}")
                raise Exception(f"Slack API error: {error_msg}")
            
            return response_data
        except httpx.TimeoutException:
            print("❌ Slack API request timed out")
            raise
        except httpx.RequestError as e:
            print(f"❌ Slack request error: {e}")
            raise
