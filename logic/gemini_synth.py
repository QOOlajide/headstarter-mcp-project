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
When assigning action items, prefer emails from the known participant email list.
If only a first name/handle is spoken, map it to the matching known email when possible.
Use empty strings / empty arrays when unknown. Prefer ISO due dates when a deadline is implied.
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

    known = known_emails or []
    known_block = (
        "KNOWN PARTICIPANT EMAILS (from Slack profiles):\n"
        + "\n".join(f"- {e}" for e in known)
        if known
        else "KNOWN PARTICIPANT EMAILS: (none provided)"
    )

    response = model.generate_content(
        f"{EXTRACTION_PROMPT}\n\n{known_block}\n\nTRANSCRIPT:\n{transcript}"
    )
    raw = response.text or "{}"
    data = json.loads(raw)

    summary: List[str] = data.get("summary_bullets") or []
    actions: List[Dict[str, Any]] = data.get("action_items") or []
    return {"summary_bullets": summary, "action_items": actions}
