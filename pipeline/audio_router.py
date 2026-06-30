"""
Classifies an audio file (sales call, client meeting, voice note, etc.)
then routes it to the appropriate handler.
"""
import json
from pathlib import Path

import anthropic
import config

CLASSIFY_PROMPT = """Classify this audio transcript into exactly one category:

- "sales_call": outbound or inbound cold/warm sales call with a prospect
- "follow_up_call": follow-up call with a prospect spoken to before
- "client_meeting": call or meeting with an existing paying client
- "discovery_call": structured intake or discovery session
- "voice_note": personal memo, task note, or reminder to self

Return ONLY valid JSON:
{{"type": "<category>", "business_name": "<inferred business or person name, empty string if unclear>", "confidence": "high|medium|low"}}

Transcript:
{transcript}"""

MEETING_PROMPT = """Extract structured data from this client meeting transcript.

Return ONLY valid JSON:
{{
  "client_name": "<business name>",
  "deliverables": ["<deliverable 1>", "<deliverable 2>"],
  "amounts_discussed": [<number or 0>],
  "timeline": "<e.g. 2 weeks>",
  "next_steps": "<what happens next>",
  "notes": "<any other important context>"
}}

Transcript:
{transcript}"""


def route_audio(audio_path: Path, on_step=None) -> dict:
    from pipeline.transcriber import transcribe

    def step(msg):
        if on_step:
            on_step(msg)

    step("Transcribing audio…")
    transcript = transcribe(audio_path)

    step("Classifying audio type…")
    ai = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    raw = ai.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": CLASSIFY_PROMPT.format(transcript=transcript)}],
    ).content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    classification = json.loads(raw)

    audio_type = classification.get("type", "voice_note")
    business_name = classification.get("business_name", "")

    if audio_type in ("sales_call", "follow_up_call", "discovery_call"):
        step(f"Routing as {audio_type}…")
        from pipeline.call_logger import log_call
        result = log_call(audio_path, business_name=business_name, on_step=on_step)
        result["routed_as"] = audio_type
        return result

    if audio_type == "client_meeting":
        step("Routing as client meeting…")
        return _log_meeting(audio_path, transcript, business_name, ai, on_step=on_step)

    # Voice note — save to vault, delete audio
    _delete(audio_path)
    step("Saving voice note to vault…")
    _save_voice_note(transcript)
    return {"routed_as": "voice_note", "message": "Saved to vault"}


def _log_meeting(audio_path: Path, transcript: str, business_name: str, ai, on_step=None) -> dict:
    def step(msg):
        if on_step:
            on_step(msg)

    raw = ai.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": MEETING_PROMPT.format(transcript=transcript)}],
    ).content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    intel = json.loads(raw)

    _delete(audio_path)

    step("Saving meeting notes…")
    from database import get_db
    conn = get_db()
    try:
        client_row = conn.execute(
            "SELECT id FROM clients WHERE business_name = ? COLLATE NOCASE LIMIT 1",
            (intel.get("client_name", business_name),),
        ).fetchone()
        if client_row and intel.get("deliverables"):
            for d in intel["deliverables"]:
                conn.execute(
                    "INSERT INTO deliverables (client_id, title) VALUES (?,?)",
                    (client_row["id"], d),
                )
            conn.commit()
    finally:
        conn.close()

    step("Done.")
    return {"routed_as": "client_meeting", "intel": intel}


def _save_voice_note(transcript: str):
    config.ensure_vault()
    from datetime import date
    path = config.VAULT_DIRS["tactics"] / f"{date.today().isoformat()}_voice_note.md"
    path.write_text(f"# Voice Note — {date.today().isoformat()}\n\n{transcript}\n", encoding="utf-8")


def _delete(path: Path):
    try:
        path.unlink()
    except Exception:
        pass
