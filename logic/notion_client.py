"""
Notion API Integration
Creates meeting notes pages in Notion workspace
"""
import os
from typing import Dict, Any, List
import httpx
from dotenv import load_dotenv

load_dotenv()

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

def get_notion_headers() -> Dict[str, str]:
    """Get Notion API headers with authentication"""
    notion_token = os.getenv("NOTION_API_KEY")
    if not notion_token:
        raise ValueError("NOTION_API_KEY not found in environment variables")
    
    return {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }

async def create_meeting_page(
    title: str,
    attendees: List[str],
    scheduled_time: str,
    duration_minutes: int,
    meet_link: str,
    description: str = ""
) -> Dict[str, Any]:
    """
    Create a meeting notes page in Notion
    Requires NOTION_DATABASE_ID environment variable
    """
    database_id = os.getenv("NOTION_DATABASE_ID")
    if not database_id:
        raise ValueError("NOTION_DATABASE_ID not found in environment variables. Please set up a Notion database first.")
    
    headers = get_notion_headers()
    
    # Format attendees list
    attendees_text = "\n".join([f"- {email}" for email in attendees])
    
    # Create page content with meeting details
    page_content = {
        "parent": {"database_id": database_id},
        "properties": {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            "Date": {
                "date": {
                    "start": scheduled_time
                }
            },
            "Duration": {
                "rich_text": [
                    {
                        "text": {
                            "content": f"{duration_minutes} minutes"
                        }
                    }
                ]
            }
        },
        "children": [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Meeting Details"
                            }
                        }
                    ]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": description or "No description provided"
                            }
                        }
                    ]
                }
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Attendees"
                            }
                        }
                    ]
                }
            },
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": attendees_text
                            }
                        }
                    ]
                }
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Meeting Link"
                            }
                        }
                    ]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": meet_link
                            },
                            "annotations": {
                                "link": {
                                    "url": meet_link
                                }
                            }
                        }
                    ]
                }
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Agenda"
                            }
                        }
                    ]
                }
            },
            {
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Add agenda items here"
                            }
                        }
                    ],
                    "checked": False
                }
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Action Items"
                            }
                        }
                    ]
                }
            },
            {
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Add action items here"
                            }
                        }
                    ],
                    "checked": False
                }
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Notes"
                            }
                        }
                    ]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Meeting notes will be added here..."
                            }
                        }
                    ]
                }
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{NOTION_API_URL}/pages",
                headers=headers,
                json=page_content
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Notion API error: {e.response.text}")
            raise
        except Exception as e:
            print(f"Error creating Notion page: {e}")
            raise

