import re
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console
import config

console = Console()


def _slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text)[:60]


def _find_existing_note_by_url(url: str) -> Path | None:
    """Return the path of an existing video note with this URL, or None."""
    if not url:
        return None
    for note_path in config.VAULT_DIRS["videos"].glob("*.md"):
        text = note_path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        end = text.find("---", 3)
        if end == -1:
            continue
        if f'url: "{url}"' in text[3:end]:
            return note_path
    return None


def write_to_vault(data: dict) -> Path:
    """Write all extracted intelligence into the Obsidian vault as linked notes."""
    config.ensure_vault()

    url = data.get("url", "")
    existing = _find_existing_note_by_url(url)
    if existing:
        console.print(f"[yellow]Skipping duplicate:[/yellow] {existing.name} (URL already in vault)")
        return existing

    video_id = _slug(data.get("title", "untitled"))
    date = datetime.now().strftime("%Y-%m-%d")
    creator = data.get("creator", "Unknown")
    creator_slug = _slug(creator)

    # ── 1. Main video note ──────────────────────────────────────────────────
    video_note = config.VAULT_DIRS["videos"] / f"{date}_{video_id}.md"
    tactics_links = "\n".join(
        f"- [[sales/tactics/{_slug(t['name'])}]]" for t in data.get("tactics", [])
    )
    hook_links = "\n".join(
        f"- [[sales/hooks/{_slug(h['name'])}]]" for h in data.get("hooks", [])
    )
    objection_links = "\n".join(
        f"- [[sales/objections/{_slug(o['objection'][:40])}]]"
        for o in data.get("objection_handles", [])
    )
    tags_yaml = "\n".join(f"  - {t}" for t in ["sales-video"] + data.get("tags", []))
    transcript_quoted = "\n".join(
        f"> {line}" for line in data.get("transcript", "").split("\n")
    )

    video_note.write_text(f"""---
date: {date}
creator: "{creator}"
url: "{url}"
tone: "{data.get('tone', '')}"
description: "{data.get('summary', '')[:150].replace('"', "'")}"
tags:
{tags_yaml}
---

# {data.get('title', 'Untitled')}

## Summary
{data.get('summary', '')}

## Opening Hook
> {data.get('hooks', [{}])[0].get('text', '') if data.get('hooks') else ''}

## Pain Points
{chr(10).join(f"- {p}" for p in data.get('pain_points', []))}

## Value Stack
{chr(10).join(f"- {v}" for v in data.get('value_stack', []))}

## Proof Elements
{chr(10).join(f"- {p}" for p in data.get('proof_elements', []))}

## Scarcity / Urgency
{data.get('scarcity_urgency') or 'None used'}

## CTA
> {data.get('cta', '')}

## Tactics
{tactics_links or 'None extracted'}

## Hooks
{hook_links or 'None extracted'}

## Objection Handles
{objection_links or 'None extracted'}

## Full Transcript

> [!note]- Full Transcript
{transcript_quoted}
""", encoding="utf-8")

    # ── 2. Tactic notes ─────────────────────────────────────────────────────
    for tactic in data.get("tactics", []):
        tactic_file = config.VAULT_DIRS["tactics"] / f"{_slug(tactic['name'])}.md"
        new_ref = f"\n- [[sales/videos/{date}_{video_id}]] — {data.get('title', '')}"
        if tactic_file.exists():
            tactic_file.write_text(
                tactic_file.read_text(encoding="utf-8").rstrip() + new_ref + "\n",
                encoding="utf-8"
            )
        else:
            tactic_file.write_text(f"""# {tactic['name']}

## Definition
{tactic['description']}

## When to Use


## Example Quote
> "{tactic['quote']}"

## Related
{new_ref}
""", encoding="utf-8")

    # ── 3. Hook notes ───────────────────────────────────────────────────────
    for hook in data.get("hooks", []):
        hook_file = config.VAULT_DIRS["hooks"] / f"{_slug(hook['name'])}.md"
        new_ref = f"\n- [[Videos/{date}_{video_id}]] — {data.get('title', '')}"
        if hook_file.exists():
            hook_file.write_text(
                hook_file.read_text(encoding="utf-8").rstrip() + new_ref + "\n",
                encoding="utf-8"
            )
        else:
            hook_file.write_text(f"""# {hook['name']}

## Pattern


## Example
> "{hook['text']}"

## Why It Works


## Related
{new_ref}
""", encoding="utf-8")

    # ── 4. Objection handle notes ────────────────────────────────────────────
    for obj in data.get("objection_handles", []):
        obj_file = config.VAULT_DIRS["objections"] / f"{_slug(obj['objection'][:40])}.md"
        if not obj_file.exists():
            obj_file.write_text(f"""# {obj['objection']}

## Objection
{obj['objection']}

## Response
{obj['response']}

## Why It Works


## Related
- [[sales/videos/{date}_{video_id}]] — {data.get('title', '')}
""", encoding="utf-8")

    # ── 5. Creator note ──────────────────────────────────────────────────────
    creator_file = config.VAULT_DIRS["creators"] / f"{creator_slug}.md"
    new_video_ref = f"\n- [[sales/videos/{date}_{video_id}]] — {data.get('title', '')} ({date})"
    if creator_file.exists():
        creator_file.write_text(
            creator_file.read_text(encoding="utf-8").rstrip() + new_video_ref + "\n",
            encoding="utf-8"
        )
    else:
        creator_file.write_text(f"""# Creator: {creator}

## Videos Analyzed
{new_video_ref}
""", encoding="utf-8")

    # ── 6. Update _Index ─────────────────────────────────────────────────────
    _update_index(data, date, video_id)

    console.print(f"[green]Vault updated:[/green] {video_note}")
    return video_note


def _update_index(data: dict, date: str, video_id: str):
    index = config.VAULT_PATH / "sales/_Index.md"
    entry = (
        f"\n| {date} | [[sales/videos/{date}_{video_id}\\|{data.get('title', '')}]] "
        f"| {data.get('creator', '')} "
        f"| {', '.join(data.get('tags', [])[:3])} |"
    )
    content = index.read_text(encoding="utf-8") if index.stat().st_size > 0 else (
        "# Sales Brain — Master Index\n\n"
        "| Date | Video | Creator | Tags |\n"
        "| ---- | ----- | ------- | ---- |"
    )
    index.write_text(content.rstrip() + entry + "\n", encoding="utf-8")
