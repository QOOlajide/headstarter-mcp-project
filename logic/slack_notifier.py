"""
Slack Authentication Handler - SECURE VERSION
Manages Slack bot token validation and permission checks
"""
import os
import logging
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
SLACK_API_URL = "https://slack.com/api"
TOKEN_PATTERN = r"^xoxb-[0-9]+-[0-9]+-[a-zA-Z0-9_-]+$"  # Slack bot token format

def _is_valid_token_format(token: str) -> bool:
    """Validate token format before using it"""
    import re
    return bool(re.match(TOKEN_PATTERN, token))

def get_slack_token() -> Optional[str]:
    """Get Slack bot token from environment variables"""
    token = os.getenv("SLACK_BOT_TOKEN")
    if token and not _is_valid_token_format(token):
        logger.warning("Invalid Slack token format detected")
        return None
    return token

async def validate_slack_token(token: Optional[str] = None) -> bool:
    """
    Validate Slack bot token by making an auth.test API call (ASYNC)
    Returns True if token is valid
    """
    token_to_check = token or get_slack_token()
    if not token_to_check:
        return False
    
    if not _is_valid_token_format(token_to_check):
        logger.warning("Attempted validation with invalid token format")
        return False
    
    headers = {
        "Authorization": f"Bearer {token_to_check}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SLACK_API_URL}/auth.test",
                headers=headers,
                timeout=5.0
            )
            result = response.json()
            success = result.get("ok", False)
            if not success:
                logger.warning(f"Token validation failed: {result.get('error', 'unknown')}")
            return success
    except httpx.TimeoutException:
        logger.error("Slack API timeout during token validation")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {type(e).__name__}")
        return False

async def check_slack_permissions(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Check Slack bot permissions and scopes
    Returns dictionary with permission information
    """
    token_to_check = token or get_slack_token()
    if not token_to_check:
        return {"valid": False}
    
    if not _is_valid_token_format(token_to_check):
        logger.warning("Attempted permission check with invalid token format")
        return {"valid": False}
    
    headers = {
        "Authorization": f"Bearer {token_to_check}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.post(
                f"{SLACK_API_URL}/auth.test",
                headers=headers,
                timeout=5.0
            )
            auth_data = auth_response.json()
            
            if not auth_data.get("ok"):
                logger.warning("Token invalid during permission check")
                return {"valid": False}
            
            bot_info_response = await client.post(
                f"{SLACK_API_URL}/bots.info",
                headers=headers,
                json={"bot": auth_data.get("bot_id")},
                timeout=5.0
            )
            
            return {
                "valid": True,
                "user_id": auth_data.get("user_id"),
                "team_id": auth_data.get("team_id"),
                "bot_id": auth_data.get("bot_id"),
                "scopes": bot_info_response.json().get("bot", {}).get("scopes", [])
            }
        except Exception as e:
            logger.error(f"Unexpected error during permission check: {type(e).__name__}")
            return {"valid": False}