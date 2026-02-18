"""
Notion Authentication Handler
Manages Notion API key validation and permission checks
"""
import os
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv

load_dotenv()

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

def get_notion_token() -> Optional[str]:
    """Get Notion API key from environment variables"""
    return os.getenv("NOTION_API_KEY")

def get_notion_headers(token: Optional[str] = None) -> Dict[str, str]:
    """
    Get Notion API headers with authentication
    Raises ValueError if token is not available
    """
    token_to_use = token or get_notion_token()
    if not token_to_use:
        raise ValueError("NOTION_API_KEY not found in environment variables")
    
    return {
        "Authorization": f"Bearer {token_to_use}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }

async def validate_notion_token(token: Optional[str] = None) -> bool:
    """
    Validate Notion API token by making a users.me API call
    Returns True if token is valid
    """
    token_to_check = token or get_notion_token()
    if not token_to_check:
        return False
    
    headers = get_notion_headers(token_to_check)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{NOTION_API_URL}/users/me",
                headers=headers,
                timeout=5.0
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error validating Notion token: {e}")
            return False

async def check_notion_permissions(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Check Notion API permissions and user info
    Returns dictionary with permission information
    """
    token_to_check = token or get_notion_token()
    if not token_to_check:
        return {"valid": False, "error": "No token provided"}
    
    headers = get_notion_headers(token_to_check)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{NOTION_API_URL}/users/me",
                headers=headers
            )
            
            if response.status_code != 200:
                return {
                    "valid": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
            
            user_data = response.json()
            return {
                "valid": True,
                "user_id": user_data.get("id"),
                "name": user_data.get("name"),
                "type": user_data.get("type")
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }

