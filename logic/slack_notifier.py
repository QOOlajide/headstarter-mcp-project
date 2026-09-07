"""
Slack channel/user resolution, email extraction, and plain-text notifications.
Slack-first scheduling per requirements Clarification section.
"""
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

from logic.meeting_cache import (
    get_channel_id,
    get_slack_user,
    set_channel_id,
    set_slack_user,
)

load_dotenv()

logger = logging.getLogger(__name__)
SLACK_API_URL = "https://slack.com/api"

# Department sync → expected existing public channel slug
DEPT_CHANNEL_SLUGS = {
    "Engineering": "engineering",
    "Product": "product-team",
    "Sales": "sales-team",
    "Design": "design-team",
    "Cross-Functional": "cross-functional",
}


def get_slack_token() -> Optional[str]:
    return os.getenv("SLACK_BOT_TOKEN")


def sanitize_team_slug(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", name).strip().lower()
    return re.sub(r"\s+", "-", cleaned)


def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _normalize_handle(handle: str) -> str:
    return handle.strip().lstrip("@").lower()


async def _slack_get(
    client: httpx.AsyncClient, token: str, method: str, params: Optional[dict] = None
) -> dict:
    response = await client.get(
        f"{SLACK_API_URL}/{method}",
        headers=_headers(token),
        params=params or {},
    )
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"{method} failed: {data.get('error')}")
    return data


async def _slack_post(
    client: httpx.AsyncClient, token: str, method: str, payload: dict
) -> dict:
    response = await client.post(
        f"{SLACK_API_URL}/{method}",
        headers=_headers(token),
        json=payload,
    )
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"{method} failed: {data.get('error')}")
    return data


async def _list_public_channels(client: httpx.AsyncClient, token: str) -> list[dict]:
    channels: list[dict] = []
    cursor: Optional[str] = None
    while True:
        params: Dict[str, Any] = {
            "types": "public_channel",
            "exclude_archived": True,
            "limit": 200,
        }
        if cursor:
            params["cursor"] = cursor
        data = await _slack_get(client, token, "conversations.list", params)
        channels.extend(data.get("channels", []))
        cursor = data.get("response_metadata", {}).get("next_cursor") or None
        if not cursor:
            break
    return channels


async def resolve_department_channel(
    department: str, team_name: Optional[str] = None
) -> tuple[str, str]:
    """
    Resolve department public channel (assumes pre-existing).
    Returns (#slug, channel_id). Does not create channels.
    """
    token = get_slack_token()
    if not token:
        raise ValueError("SLACK_BOT_TOKEN not found in environment variables")

    slug = sanitize_team_slug(team_name) if team_name else DEPT_CHANNEL_SLUGS.get(
        department, sanitize_team_slug(department)
    )
    cached = get_channel_id(slug)
    if cached:
        return f"#{slug}", cached

    async with httpx.AsyncClient(timeout=15.0) as client:
        for channel in await _list_public_channels(client, token):
            if channel.get("name") == slug:
                set_channel_id(slug, channel["id"])
                return f"#{slug}", channel["id"]

    raise RuntimeError(
        f"Slack channel #{slug} not found. Create it in Slack first "
        "(department channels are assumed pre-existing)."
    )


async def _list_workspace_users(client: httpx.AsyncClient, token: str) -> list[dict]:
    members: list[dict] = []
    cursor: Optional[str] = None
    while True:
        params: Dict[str, Any] = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        data = await _slack_get(client, token, "users.list", params)
        members.extend(data.get("members", []))
        cursor = data.get("response_metadata", {}).get("next_cursor") or None
        if not cursor:
            break
    return members


def _user_record(member: dict) -> dict:
    profile = member.get("profile") or {}
    handle = (member.get("name") or "").lower()
    return {
        "handle": handle,
        "user_id": member.get("id", ""),
        "email": (profile.get("email") or "").strip().lower() or None,
        "display_name": (
            profile.get("display_name")
            or profile.get("real_name")
            or member.get("real_name")
            or handle
        ),
    }


async def resolve_slack_users(handles: List[str]) -> List[dict]:
    """
    Resolve @handles → Slack user_id + email (users:read.email).
    Caches handle → user_id/email in SQLite.
    """
    token = get_slack_token()
    if not token:
        raise ValueError("SLACK_BOT_TOKEN not found in environment variables")

    normalized = [_normalize_handle(h) for h in handles if h and _normalize_handle(h)]
    if not normalized:
        raise ValueError("At least one Slack handle is required for ad-hoc scheduling")

    resolved: List[dict] = []
    missing: List[str] = []

    for handle in normalized:
        cached = get_slack_user(handle)
        if cached and cached.get("user_id"):
            resolved.append(
                {
                    "handle": handle,
                    "user_id": cached["user_id"],
                    "email": cached.get("email"),
                    "display_name": cached.get("display_name") or handle,
                }
            )
        else:
            missing.append(handle)

    if missing:
        async with httpx.AsyncClient(timeout=20.0) as client:
            members = await _list_workspace_users(client, token)
            by_name = {}
            for member in members:
                if member.get("deleted") or member.get("is_bot"):
                    continue
                rec = _user_record(member)
                if rec["handle"]:
                    by_name[rec["handle"]] = rec
                # Also index display name loosely
                display = (rec["display_name"] or "").lower().replace(" ", "")
                if display:
                    by_name.setdefault(display, rec)

            for handle in missing:
                rec = by_name.get(handle) or by_name.get(handle.replace(".", ""))
                if not rec:
                    raise RuntimeError(f"Slack user @{handle} not found in workspace")
                set_slack_user(
                    handle=rec["handle"] or handle,
                    user_id=rec["user_id"],
                    email=rec.get("email"),
                    display_name=rec.get("display_name"),
                )
                # Also cache under the requested handle if different
                if handle != rec["handle"]:
                    set_slack_user(
                        handle=handle,
                        user_id=rec["user_id"],
                        email=rec.get("email"),
                        display_name=rec.get("display_name"),
                    )
                resolved.append(
                    {
                        "handle": handle,
                        "user_id": rec["user_id"],
                        "email": rec.get("email"),
                        "display_name": rec.get("display_name") or handle,
                    }
                )

    return resolved


async def open_group_dm(user_ids: List[str]) -> str:
    """Open/retrieve MPIM via conversations.open. Returns channel ID."""
    token = get_slack_token()
    if not token:
        raise ValueError("SLACK_BOT_TOKEN not found in environment variables")

    unique_ids = list(dict.fromkeys(user_ids))
    async with httpx.AsyncClient(timeout=15.0) as client:
        data = await _slack_post(
            client,
            token,
            "conversations.open",
            {"users": ",".join(unique_ids)},
        )
    channel = data.get("channel") or {}
    channel_id = channel.get("id")
    if not channel_id:
        raise RuntimeError("conversations.open did not return a channel id")
    return channel_id


async def fetch_channel_member_emails(channel_id: str) -> List[dict]:
    """
    Pull channel members and extract profile emails for Notion assignee mapping.
    Requires users:read + users:read.email.
    """
    token = get_slack_token()
    if not token:
        raise ValueError("SLACK_BOT_TOKEN not found in environment variables")

    participants: List[dict] = []
    async with httpx.AsyncClient(timeout=20.0) as client:
        cursor: Optional[str] = None
        member_ids: List[str] = []
        while True:
            params: Dict[str, Any] = {"channel": channel_id, "limit": 200}
            if cursor:
                params["cursor"] = cursor
            data = await _slack_get(client, token, "conversations.members", params)
            member_ids.extend(data.get("members", []))
            cursor = data.get("response_metadata", {}).get("next_cursor") or None
            if not cursor:
                break

        for user_id in member_ids:
            info = await _slack_get(
                client, token, "users.info", {"user": user_id}
            )
            user = info.get("user") or {}
            if user.get("deleted") or user.get("is_bot") or user.get("id", "").startswith("B"):
                continue
            rec = _user_record(user)
            if rec["user_id"]:
                if rec["handle"]:
                    set_slack_user(
                        handle=rec["handle"],
                        user_id=rec["user_id"],
                        email=rec.get("email"),
                        display_name=rec.get("display_name"),
                    )
                participants.append(rec)
    return participants


async def send_slack_message(
    text: str,
    channel: Optional[str] = None,
    team_name: Optional[str] = None,
    notify_channel: bool = False,
) -> Dict[str, Any]:
    """Post plain-text chat.postMessage (no Block Kit)."""
    token = get_slack_token()
    if not token:
        raise ValueError("SLACK_BOT_TOKEN not found in environment variables")

    channel_name = None
    if team_name:
        channel_name, target = await resolve_department_channel(
            department=team_name, team_name=team_name
        )
    elif channel:
        target = channel
    else:
        target = os.getenv("SLACK_CHANNEL")
        if not target:
            raise ValueError("No Slack channel or team_name provided")

    body = text
    if notify_channel and "<!channel>" not in body:
        body = f"<!channel> {body}"

    payload = {"channel": target, "text": body}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{SLACK_API_URL}/chat.postMessage",
            headers=_headers(token),
            json=payload,
        )
        data = response.json()
        if not data.get("ok"):
            error = data.get("error", "unknown")
            logger.error("Slack API error: %s", error)
            raise RuntimeError(f"Slack API error: {error}")

        data["resolved_channel_name"] = channel_name or target
        data["resolved_channel_id"] = target
        return data


def map_assignee_to_email(
    raw_assignee: str,
    participants: List[dict],
) -> str:
    """
    Map Gemini assignee (name/handle/email) → Slack profile email for Notion.
    """
    if not raw_assignee:
        return ""
    raw = raw_assignee.strip()
    lower = raw.lower().lstrip("@")

    if "@" in raw and "." in raw.split("@")[-1]:
        return raw.lower()

    for p in participants:
        email = (p.get("email") or "").lower()
        handle = (p.get("handle") or "").lower()
        display = (p.get("display_name") or "").lower()
        if lower == handle or lower == display:
            return email
        if display and (lower in display or display in lower):
            return email
        if email and lower == email.split("@")[0]:
            return email
    return raw  # leave unresolved string rather than inventing an email
