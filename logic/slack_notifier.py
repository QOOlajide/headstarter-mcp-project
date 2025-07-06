import os
from dotenv import load_dotenv
import httpx

from dotenv import load_dotenv
load_dotenv()

SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")

SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")

async def send_slack_message(text: str):
    headers = {
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "channel": SLACK_CHANNEL,
        "text": text
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("https://slack.com/api/chat.postMessage", json=payload, headers=headers)
        if not response.json().get("ok"):
            print("❌ Slack error:", response.json())
