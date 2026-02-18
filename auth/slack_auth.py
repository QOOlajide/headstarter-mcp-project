"""
Slack Authentication Handler
Manages Slack bot token validation and permission checks
"""
import os
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv

load_dotenv()

SLACK_API_URL = "https://slack.com/api"

def get_slack_token() -> Optional[str]:
    """Get Slack bot token from environment variables"""
    return os.getenv("SLACK_BOT_TOKEN")

def validate_slack_token(token: Optional[str] = None) -> bool:
    """
    Validate Slack bot token by making an auth.test API call
    Returns True if token is valid
    """
    token_to_check = token or get_slack_token()
    if not token_to_check:
        return False
    
    headers = {
        "Authorization": f"Bearer {token_to_check}",
        "Content-Type": "application/json"
    }
    
    try:
        response = httpx.post(
            f"{SLACK_API_URL}/auth.test",
            headers=headers,
            timeout=5.0
        )
        result = response.json()
        return result.get("ok", False)
    except Exception as e:
        print(f"Error validating Slack token: {e}")
        return False

async def check_slack_permissions(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Check Slack bot permissions and scopes
    Returns dictionary with permission information
    """
    token_to_check = token or get_slack_token()
    if not token_to_check:
        return {"valid": False, "error": "No token provided"}
    
    headers = {
        "Authorization": f"Bearer {token_to_check}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Check auth info
            auth_response = await client.post(
                f"{SLACK_API_URL}/auth.test",
                headers=headers
            )
            auth_data = auth_response.json()
            
            if not auth_data.get("ok"):
                return {
                    "valid": False,
                    "error": auth_data.get("error", "Unknown error")
                }
            
            # Check bot info for scopes
            bot_info_response = await client.post(
                f"{SLACK_API_URL}/bots.info",
                headers=headers,
                json={"bot": auth_data.get("bot_id")}
            )
            
            return {
                "valid": True,
                "user_id": auth_data.get("user_id"),
                "team_id": auth_data.get("team_id"),
                "bot_id": auth_data.get("bot_id"),
                "scopes": bot_info_response.json().get("bot", {}).get("scopes", [])
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }

