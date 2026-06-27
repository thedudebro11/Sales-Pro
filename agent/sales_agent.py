import anthropic
from pathlib import Path
from datetime import datetime
from rich.console import Console
import config

console = Console()

SCRIPT_PROMPT = """You are the world's best direct response copywriter and sales script architect.

You have access to a comprehensive sales intelligence brain built from analyzing real Instagram sales videos. Use every tactic, hook, objection handle, and value frame from this knowledge base to write a devastatingly effective sales script.

## KNOWLEDGE BASE
{knowledge}

---

## SCRIPT REQUEST
- **Product / Service:** {product}
- **Target Audience:** {audience}
- **Platform / Context:** {platform}
- **Tone:** {tone}
- **Goal:** {goal}

---

## DELIVERABLE

Write the complete sales script following this structure:

### 1. PATTERN INTERRUPT HOOK (0-3 seconds)
[Grab attention immediately. Use the best hook patterns from the brain.]

### 2. PAIN AGITATION (3-15 seconds)
[Name the exact pain. Make them feel it. Reference real pain points from the brain.]

### 3. CREDIBILITY / PROOF (15-25 seconds)
[Social proof, stats, or authority. Use the best proof elements found.]

### 4. SOLUTION REVEAL (25-40 seconds)
[Introduce the product as the inevitable answer to the pain.]

### 5. VALUE STACK (40-60 seconds)
[Stack specific benefits rapidly. Use the best value stacking patterns found.]

### 6. OBJECTION PRE-EMPTION (60-75 seconds)
[Kill the top 2-3 objections before they surface. Use the exact objection handles from the brain.]

### 7. SCARCITY / URGENCY (75-85 seconds)
[Create real or implied urgency without being fake. Use the best patterns found.]

### 8. CTA (85-90 seconds)
[One clear, low-friction action. Use the most effective CTA patterns from the brain.]

---

After the script, provide:

**TACTIC RATIONALE** — A bullet list of which specific tactics from the brain you used and why.

**A/B HOOK VARIANTS** — 3 alternative opening hooks to test.

**OBJECTION KILL LIST** — Extended objection handles for the top 5 objections for this product.
"""

def load_vault_knowledge() -> str:
    """Load all vault notes into a single context string for the agent."""
    config.ensure_vault()
    sections = []

    for folder_name, folder_path in config.VAULT_DIRS.items():
        if folder_name == "scripts":
            continue
        files = list(folder_path.glob("*.md"))
        if not files:
            continue
        sections.append(f"\n## {folder_name.upper()} ({len(files)} notes)\n")
        for f in sorted(files):
            content = f.read_text(encoding="utf-8")
            # truncate very long notes (transcripts) to keep context manageable
            if len(content) > 2000:
                content = content[:2000] + "\n…[truncated]"
            sections.append(f"### {f.stem}\n{content}\n")

    if not sections:
        return "No sales intelligence loaded yet. Run `python main.py <url>` first to populate the brain."

    return "\n".join(sections)


def generate_script(
    product: str,
    audience: str,
    platform: str = "Instagram Reels / TikTok",
    tone: str = "Conversational and confident",
    goal: str = "Book a call / DM for more info",
) -> str:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    console.print("[cyan]Loading sales brain knowledge…[/cyan]")
    knowledge = load_vault_knowledge()
    console.print(f"[dim]Brain context: {len(knowledge.split()):,} words[/dim]")

    console.print("[cyan]Generating ultimate sales script…[/cyan]")
    message = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=8096,
        messages=[{
            "role": "user",
            "content": SCRIPT_PROMPT.format(
                knowledge=knowledge,
                product=product,
                audience=audience,
                platform=platform,
                tone=tone,
                goal=goal,
            )
        }]
    )

    script = message.content[0].text.strip()

    # save to vault
    config.ensure_vault()
    from re import sub
    slug = sub(r"[^a-zA-Z0-9_-]", "_", product)[:50]
    date = datetime.now().strftime("%Y-%m-%d")
    script_file = config.VAULT_DIRS["scripts"] / f"{date}_{slug}.md"
    script_file.write_text(f"# Sales Script: {product}\n\n**Generated:** {date}\n**Audience:** {audience}\n\n{script}\n", encoding="utf-8")

    console.print(f"[green]Script saved:[/green] {script_file}")
    return script
