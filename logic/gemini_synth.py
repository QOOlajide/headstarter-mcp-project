"""
Google Gemini synthesis for meeting transcripts (requirements §4.4).
"""
import json
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

EXTRACTION_PROMPT = """You are a meeting analyst. Given a raw meeting transcript, return ONLY valid JSON matching this schema:
{
  "summary_bullets": ["string"],
  "action_items": [
    {
      "task": "string",
      "assignee_email": "string",
      "priority": "High | Medium | Low",
      "due_date": "YYYY-MM-DD"
    }
  ]
}
Assignee rules (strict):
- assignee_email MUST be copied exactly from the KNOWN PARTICIPANT EMAILS list below.
- If a spoken name/handle clearly matches one known email, use that email.
- NEVER invent, guess, or output an email that is not on that list.
- If the owner is unclear or not on the list, set assignee_email to "".
- Prefer ISO due dates when a deadline is implied. Use empty strings / empty arrays when unknown.
"""


def synthesize_transcript(
    transcript: str,
    known_emails: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Call Gemini (gemini-3.1-flash-lite by default) with JSON mime type.
    Returns dict with summary_bullets and action_items.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")

    model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise ImportError(
            "google-generativeai is required. Install with: pip install google-generativeai"
        ) from exc

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config={"response_mime_type": "application/json"},
    )

    known = [e.strip().lower() for e in (known_emails or []) if e and str(e).strip()]
    known_set = set(known)
    if known:
        known_block = (
            "KNOWN PARTICIPANT EMAILS (from Slack profiles) — "
            "assignee_email MUST be one of these exactly, or \"\":\n"
            + "\n".join(f"- {e}" for e in known)
        )
    else:
        known_block = (
            "KNOWN PARTICIPANT EMAILS: (none provided)\n"
            "Because the list is empty, every action item MUST use "
            'assignee_email: "". Do not invent any email addresses.'
        )

    response = model.generate_content(
        f"{EXTRACTION_PROMPT}\n\n{known_block}\n\nTRANSCRIPT:\n{transcript}"
    )
    raw = response.text or "{}"
    data = json.loads(raw)

    summary: List[str] = data.get("summary_bullets") or []
    actions: List[Dict[str, Any]] = data.get("action_items") or []
    # Hard filter: drop any assignee_email not in the known meeting list.
    for item in actions:
        if not isinstance(item, dict):
            continue
        email = (item.get("assignee_email") or "").strip().lower()
        item["assignee_email"] = email if email in known_set else ""
    return {"summary_bullets": summary, "action_items": actions}
