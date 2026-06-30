"""
Transcribes a call recording, extracts sales intel via Claude, saves to DB + vault,
schedules follow-up, then deletes the audio file immediately.
"""
from pathlib import Path
import json
from datetime import date, timedelta

import anthropic
import config
from database import get_db

EXTRACTION_PROMPT = """You transcribed a sales outreach call. Extract structured intel.

Return ONLY valid JSON with these exact keys:
{{
  "outcome": "interested|not_interested|callback|voicemail|no_answer|wrong_number|do_not_call",
  "opener_used": "the opening line or approach used (1-2 sentences)",
  "objections": ["objection 1", "objection 2"],
  "cta_used": "what call-to-action was attempted",
  "cta_response": "how they responded to the CTA",
  "duration_estimate": "e.g. 3 min",
  "notes": "any other important context",
  "followup_type": "call|text|email|none",
  "followup_days": 3,
  "followup_draft": "draft message for the follow-up, empty string if none"
}}

Transcript:
{transcript}"""


def log_call(audio_path: Path, business_name: str = "", industry: str = "",
             city: str = "", on_step=None) -> dict:
    from pipeline.transcriber import transcribe

    def step(msg):
        if on_step:
            on_step(msg)

    step("Transcribing audio…")
    transcript = transcribe(audio_path)

    try:
        audio_path.unlink()
    except Exception:
        pass

    step("Extracting call intelligence with Claude…")
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(transcript=transcript)}],
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    intel = json.loads(raw)

    step("Saving to pipeline database…")
    conn = get_db()
    prospect_id = None
    try:
        existing = conn.execute(
            "SELECT id FROM prospects WHERE business_name = ? COLLATE NOCASE LIMIT 1",
            (business_name,)
        ).fetchone() if business_name else None

        if existing:
            prospect_id = existing["id"]
        else:
            cur = conn.execute(
                "INSERT INTO prospects (business_name, industry, city, stage) VALUES (?,?,?,?)",
                (business_name or "Unknown", industry, city, "called"),
            )
            prospect_id = cur.lastrowid

        conn.execute(
            "UPDATE prospects SET stage='called', updated_at=datetime('now') "
            "WHERE id=? AND stage='researched'",
            (prospect_id,),
        )

        conn.execute(
            "INSERT INTO interactions (prospect_id, type, outcome, opener_used, objections, "
            "cta_used, cta_response, notes, duration_estimate) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                prospect_id, "call",
                intel.get("outcome", ""),
                intel.get("opener_used", ""),
                json.dumps(intel.get("objections", [])),
                intel.get("cta_used", ""),
                intel.get("cta_response", ""),
                intel.get("notes", ""),
                intel.get("duration_estimate", ""),
            ),
        )

        followup_days = int(intel.get("followup_days") or 0)
        followup_type = intel.get("followup_type", "none")
        if followup_days > 0 and followup_type != "none":
            followup_date = (date.today() + timedelta(days=followup_days)).isoformat()
            conn.execute(
                "INSERT INTO followups (prospect_id, type, message_draft, scheduled_for) VALUES (?,?,?,?)",
                (prospect_id, followup_type, intel.get("followup_draft", ""), followup_date),
            )

        conn.commit()
    finally:
        conn.close()

    step("Saving call log to vault…")
    _save_call_log(business_name, city, industry, transcript, intel)
    _track_pattern(intel, industry, city)

    step("Done.")
    return {
        "prospect_id": prospect_id,
        "outcome": intel.get("outcome"),
        "followup_scheduled": followup_days > 0 if "followup_days" in intel else False,
    }


def _save_call_log(business_name, city, industry, transcript, intel):
    config.ensure_vault()
    slug = (business_name or "unknown").lower().replace(" ", "_")[:30]
    fname = f"{date.today().isoformat()}_{slug}.md"
    path = config.VAULT_DIRS["calls"] / fname

    objections = intel.get("objections", [])
    if isinstance(objections, str):
        objections = [objections] if objections else []

    content = f"""# Call Log — {business_name or 'Unknown'}

**Date:** {date.today().isoformat()}
**City:** {city}
**Industry:** {industry}
**Outcome:** {intel.get('outcome', '')}
**Duration:** {intel.get('duration_estimate', '')}

## Opener Used
{intel.get('opener_used', '')}

## Objections
{chr(10).join(f'- {o}' for o in objections) or 'None noted'}

## CTA
**Used:** {intel.get('cta_used', '')}
**Response:** {intel.get('cta_response', '')}

## Notes
{intel.get('notes', '')}

## Follow-Up
**Type:** {intel.get('followup_type', 'none')}
**Draft:** {intel.get('followup_draft', '')}

## Full Transcript
{transcript}
"""
    path.write_text(content, encoding="utf-8")


def _track_pattern(intel, industry, city):
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO call_patterns (industry, opener_type, cta_type, outcome, city) VALUES (?,?,?,?,?)",
            (
                industry,
                (intel.get("opener_used") or "")[:80],
                (intel.get("cta_used") or "")[:80],
                intel.get("outcome", ""),
                city,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass
