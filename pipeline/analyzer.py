import re
import json
import anthropic
from rich.console import Console
import config

console = Console()


def _extract_creator_hint(transcript: str) -> str:
    """Scan the first 400 chars for a spoken self-introduction and return the name, or ''."""
    snippet = transcript[:400]
    patterns = [
        r"(?:hi|hey)[,!]?\s+i'?m\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"my name is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"i'?m\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[,\.]",
    ]
    for pattern in patterns:
        m = re.search(pattern, snippet, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


EXTRACTION_PROMPT = """You are a world-class sales analyst. Analyze this Instagram video transcript and extract every sales intelligence signal it contains.

Return ONLY valid JSON matching this exact schema — no commentary, no markdown fences:

{
  "title": "short descriptive title for this video",
  "creator": "creator handle or 'Unknown'",
  "summary": "2-3 sentence summary of what they're selling and how",
  "tone": "e.g. aggressive closer / educational / story-driven / authority / scarcity",
  "hooks": [
    {
      "name": "hook type label (e.g. Question Hook, Outcome Vision Hook, Pain Agitation Hook, Shocking Stat Hook, Social Proof Hook, Story Hook, Curiosity Gap Hook, Challenge Hook)",
      "text": "exact hook phrase or sentence used to open / grab attention",
      "pattern": "the reusable structural pattern behind this hook (1 sentence, generalized — not specific to this video)",
      "why_it_works": "psychological or persuasion principle that makes this hook effective (1-2 sentences)"
    }
  ],
  "pain_points": [
    "specific pain point or problem addressed"
  ],
  "tactics": [
    {
      "name": "short tactic name",
      "description": "what they did and why it works psychologically",
      "quote": "exact quote from transcript that demonstrates it"
    }
  ],
  "objection_handles": [
    {
      "objection": "the objection raised or implied",
      "response": "how they handled it"
    }
  ],
  "cta": "the exact call-to-action used",
  "proof_elements": [
    "testimonials, case studies, stats, or social proof used"
  ],
  "scarcity_urgency": "any scarcity or urgency elements used, or null",
  "value_stack": [
    "each distinct value point or benefit offered"
  ],
  "tags": ["keyword", "tags", "for", "search"]
}

TRANSCRIPT:
{transcript}
"""

def analyze(transcript: str, url: str) -> dict:
    """Send transcript to Claude and extract structured sales intelligence."""
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    creator_hint = _extract_creator_hint(transcript)
    hint_note = (
        f'\nCREATOR HINT: The speaker introduced themselves as "{creator_hint}". '
        f'Use this name for the "creator" field if no social handle is explicitly mentioned.\n'
    ) if creator_hint else ""

    prompt = EXTRACTION_PROMPT.replace("{transcript}", hint_note + transcript)

    console.print("[cyan]Analyzing sales intelligence with Claude…[/cyan]")
    if creator_hint:
        console.print(f"[dim]Creator hint detected: {creator_hint}[/dim]")

    message = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": prompt,
        }]
    )

    raw = message.content[0].text.strip()
    # strip accidental markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Claude returned invalid JSON (transcript may be too long): {e}"
        ) from e
    data["url"] = url
    data["transcript"] = transcript
    console.print(f"[green]Extracted[/green] {len(data.get('tactics', []))} tactics, "
                  f"{len(data.get('hooks', []))} hooks, "
                  f"{len(data.get('objection_handles', []))} objection handles")
    return data
