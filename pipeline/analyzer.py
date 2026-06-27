import json
import anthropic
from rich.console import Console
import config

console = Console()

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
      "text": "exact hook phrase or sentence used to open / grab attention"
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

    console.print("[cyan]Analyzing sales intelligence with Claude…[/cyan]")
    message = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": EXTRACTION_PROMPT.replace("{transcript}", transcript),
        }]
    )

    raw = message.content[0].text.strip()
    # strip accidental markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()

    data = json.loads(raw)
    data["url"] = url
    data["transcript"] = transcript
    console.print(f"[green]Extracted[/green] {len(data.get('tactics', []))} tactics, "
                  f"{len(data.get('hooks', []))} hooks, "
                  f"{len(data.get('objection_handles', []))} objection handles")
    return data
