import json
import anthropic
from pathlib import Path
from rich.console import Console
import config

console = Console()
BATCH_SIZE = 20
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def _section_content(content: str, section: str) -> str:
    header = f"## {section}"
    idx = content.find(header)
    if idx == -1:
        return ""
    content_start = content.index("\n", idx) + 1
    next_header = content.find("\n##", content_start)
    end = next_header if next_header != -1 else len(content)
    return content[content_start:end].strip()


def _fill_section(content: str, section: str, value: str) -> str:
    """Fill an empty section. Skips if section already has content."""
    header = f"## {section}"
    idx = content.find(header)
    if idx == -1:
        return content
    content_start = content.index("\n", idx) + 1
    next_header = content.find("\n##", content_start)
    end = next_header if next_header != -1 else len(content)
    if content[content_start:end].strip():
        return content  # already filled — never overwrite
    return content[:content_start] + value.strip() + "\n\n" + content[end:]


def _call_claude(prompt: str) -> dict:
    msg = _get_client().messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()
    return json.loads(raw)


def enrich_hooks():
    hooks_dir = config.VAULT_DIRS["hooks"]
    files = sorted(hooks_dir.glob("*.md"))

    to_enrich = []
    for f in files:
        content = f.read_text(encoding="utf-8")
        if not _section_content(content, "Pattern") or not _section_content(content, "Why It Works"):
            to_enrich.append({
                "file": f,
                "name": f.stem.replace("_", " "),
                "example": _section_content(content, "Example"),
            })

    if not to_enrich:
        console.print("[green]Hooks already fully enriched.[/green]")
        return

    console.print(f"[cyan]Enriching {len(to_enrich)} hooks…[/cyan]")

    for i in range(0, len(to_enrich), BATCH_SIZE):
        batch = to_enrich[i : i + BATCH_SIZE]
        id_map = {f"id_{j}": item for j, item in enumerate(batch)}

        notes_text = "\n\n".join(
            f'{key}:\n  Hook type: "{item["name"]}"\n  Example: {item["example"]}'
            for key, item in id_map.items()
        )

        prompt = f"""You are an elite sales trainer and persuasion psychologist.

For each hook, provide TWO fields:

"pattern" — The reusable fill-in-the-blank formula behind this hook. Written so any salesperson can apply it to ANY offer immediately. Specific and structural, not vague. (2-3 sentences.)

"why_it_works" — The exact psychological or neuroscience mechanism at play. Name the cognitive bias, emotional trigger, or behavioral principle. Be precise and educational — not generic motivational speak. (2-3 sentences.)

Return ONLY valid JSON with the same IDs:

{{
  "id_0": {{"pattern": "...", "why_it_works": "..."}},
  "id_1": {{"pattern": "...", "why_it_works": "..."}}
}}

HOOKS:
{notes_text}"""

        try:
            result = _call_claude(prompt)
            for key, item in id_map.items():
                data = result.get(key, {})
                if not data:
                    console.print(f"[yellow]No data for {item['name']}[/yellow]")
                    continue
                content = item["file"].read_text(encoding="utf-8")
                if data.get("pattern"):
                    content = _fill_section(content, "Pattern", data["pattern"])
                if data.get("why_it_works"):
                    content = _fill_section(content, "Why It Works", data["why_it_works"])
                item["file"].write_text(content, encoding="utf-8")
                console.print(f"  [green]✓[/green] {item['name']}")
        except Exception as e:
            console.print(f"[red]Hook batch {i//BATCH_SIZE + 1} failed: {e}[/red]")

    console.print("[green]Hooks done.[/green]")


def enrich_tactics():
    tactics_dir = config.VAULT_DIRS["tactics"]
    files = sorted(tactics_dir.glob("*.md"))

    to_enrich = []
    for f in files:
        content = f.read_text(encoding="utf-8")
        if not _section_content(content, "When to Use"):
            to_enrich.append({
                "file": f,
                "name": f.stem.replace("_", " "),
                "definition": _section_content(content, "Definition"),
                "example": _section_content(content, "Example Quote"),
            })

    if not to_enrich:
        console.print("[green]Tactics already fully enriched.[/green]")
        return

    console.print(f"[cyan]Enriching {len(to_enrich)} tactics…[/cyan]")

    for i in range(0, len(to_enrich), BATCH_SIZE):
        batch = to_enrich[i : i + BATCH_SIZE]
        id_map = {f"id_{j}": item for j, item in enumerate(batch)}

        notes_text = "\n\n".join(
            f'{key}:\n  Tactic: "{item["name"]}"\n  Definition: {item["definition"]}\n  Example: {item["example"]}'
            for key, item in id_map.items()
        )

        prompt = f"""You are an elite sales trainer with 20 years of field experience closing high-ticket deals.

For each tactic, provide:

"when_to_use" — Exactly when and where in the sales conversation to deploy this. Be specific:
- What stage (cold outreach / discovery / objection handling / close / follow-up)
- What prospect signal or situation triggers it
- What emotional or conversational state the prospect needs to be in
- Any situations where you should NOT use it
(4-5 sentences. Highly tactical and actionable — not general.)

Return ONLY valid JSON:

{{
  "id_0": {{"when_to_use": "..."}},
  "id_1": {{"when_to_use": "..."}}
}}

TACTICS:
{notes_text}"""

        try:
            result = _call_claude(prompt)
            for key, item in id_map.items():
                data = result.get(key, {})
                if not data:
                    console.print(f"[yellow]No data for {item['name']}[/yellow]")
                    continue
                content = item["file"].read_text(encoding="utf-8")
                if data.get("when_to_use"):
                    content = _fill_section(content, "When to Use", data["when_to_use"])
                item["file"].write_text(content, encoding="utf-8")
                console.print(f"  [green]✓[/green] {item['name']}")
        except Exception as e:
            console.print(f"[red]Tactic batch {i//BATCH_SIZE + 1} failed: {e}[/red]")

    console.print("[green]Tactics done.[/green]")


def enrich_objections():
    objections_dir = config.VAULT_DIRS["objections"]
    files = sorted(objections_dir.glob("*.md"))

    to_enrich = []
    for f in files:
        content = f.read_text(encoding="utf-8")
        if not _section_content(content, "Why It Works"):
            to_enrich.append({
                "file": f,
                "name": f.stem.replace("_", " "),
                "objection": _section_content(content, "Objection"),
                "response": _section_content(content, "Response"),
            })

    if not to_enrich:
        console.print("[green]Objections already fully enriched.[/green]")
        return

    console.print(f"[cyan]Enriching {len(to_enrich)} objections…[/cyan]")

    for i in range(0, len(to_enrich), BATCH_SIZE):
        batch = to_enrich[i : i + BATCH_SIZE]
        id_map = {f"id_{j}": item for j, item in enumerate(batch)}

        notes_text = "\n\n".join(
            f'{key}:\n  Objection: "{item["objection"]}"\n  Response: {item["response"]}'
            for key, item in id_map.items()
        )

        prompt = f"""You are an elite sales psychologist and closer who has trained thousands of reps.

For each objection-response pair, provide:

"why_it_works" — The deep psychology behind WHY this specific response dismantles this specific objection. Explain:
- The root fear or limiting belief driving the objection
- The psychological principle the response exploits (loss aversion, social proof, cognitive dissonance, identity, scarcity, authority, reciprocity, etc.)
- Why this reframe lands emotionally, not just logically
Be precise and specific to THIS objection — not generic sales advice. (3-4 sentences.)

Return ONLY valid JSON:

{{
  "id_0": {{"why_it_works": "..."}},
  "id_1": {{"why_it_works": "..."}}
}}

OBJECTIONS:
{notes_text}"""

        try:
            result = _call_claude(prompt)
            for key, item in id_map.items():
                data = result.get(key, {})
                if not data:
                    console.print(f"[yellow]No data for {item['name'][:50]}[/yellow]")
                    continue
                content = item["file"].read_text(encoding="utf-8")
                if data.get("why_it_works"):
                    content = _fill_section(content, "Why It Works", data["why_it_works"])
                item["file"].write_text(content, encoding="utf-8")
                console.print(f"  [green]✓[/green] {item['name'][:60]}")
        except Exception as e:
            console.print(f"[red]Objection batch {i//BATCH_SIZE + 1} failed: {e}[/red]")

    console.print("[green]Objections done.[/green]")


def enrich_all():
    console.print("[bold cyan]━━ Vault Enrichment ━━[/bold cyan]")
    enrich_hooks()
    enrich_tactics()
    enrich_objections()
    console.print("[bold green]━━ Enrichment complete ━━[/bold green]")
