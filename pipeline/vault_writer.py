import re
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console
import config

console = Console()

_embed_model = None  # lazy singleton — loaded once per process


def _slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text)[:60]


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            console.print("[dim]Loading embedding model (first run may take a moment)…[/dim]")
            _embed_model = SentenceTransformer(config.EMBED_MODEL)
        except ImportError:
            return None
    return _embed_model


def _find_similar_tactic(name: str, description: str, threshold: float = 0.82) -> Path | None:
    """Return an existing tactic note if TF-IDF cosine similarity >= threshold."""
    existing = list(config.VAULT_DIRS["tactics"].glob("*.md"))
    if not existing:
        return None
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return None

    corpus = [p.read_text(encoding="utf-8")[:500] for p in existing]
    query = f"{name} {description}"
    vectorizer = TfidfVectorizer().fit(corpus + [query])
    tfidf = vectorizer.transform(corpus + [query])
    sims = cosine_similarity(tfidf[-1:], tfidf[:-1])[0]
    best_idx = int(sims.argmax())
    return existing[best_idx] if sims[best_idx] >= threshold else None


def _append_embedding(note_path: Path, content: str):
    """Compute and append an embedding for a note to the JSONL index."""
    model = _get_embed_model()
    if model is None:
        return
    try:
        embedding = model.encode(content[:1000]).tolist()
        config.EMBEDDINGS_INDEX.parent.mkdir(parents=True, exist_ok=True)
        with open(config.EMBEDDINGS_INDEX, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"path": str(note_path), "embedding": embedding}) + "\n")
    except Exception:
        pass  # embeddings are optional — never block the main pipeline


def reindex_vault_embeddings():
    """Rebuild .embeddings.jsonl from scratch by re-embedding all vault notes."""
    model = _get_embed_model()
    if model is None:
        console.print("[yellow]sentence-transformers not installed — skipping reindex.[/yellow]")
        console.print("Install with: pip install sentence-transformers")
        return

    config.ensure_vault()
    all_notes = []
    for folder_path in config.VAULT_DIRS.values():
        all_notes.extend(folder_path.glob("*.md"))

    if not all_notes:
        console.print("[yellow]No notes found in vault.[/yellow]")
        return

    console.print(f"[cyan]Reindexing {len(all_notes)} notes…[/cyan]")
    config.EMBEDDINGS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    config.EMBEDDINGS_INDEX.write_text("", encoding="utf-8")

    for note in all_notes:
        content = note.read_text(encoding="utf-8")[:1000]
        embedding = model.encode(content).tolist()
        with open(config.EMBEDDINGS_INDEX, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"path": str(note), "embedding": embedding}) + "\n")

    console.print(f"[green]Reindex complete:[/green] {len(all_notes)} notes → {config.EMBEDDINGS_INDEX}")


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

    video_note_content = f"""---
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
"""
    video_note.write_text(video_note_content, encoding="utf-8")
    _append_embedding(video_note, video_note_content)

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
            similar = _find_similar_tactic(tactic["name"], tactic["description"])
            if similar:
                console.print(f"[yellow]Merged → {similar.stem}[/yellow] (similar to: {tactic['name']})")
                existing_content = similar.read_text(encoding="utf-8").rstrip()
                similar.write_text(
                    existing_content
                    + f"\n\n## Example Quote\n> \"{tactic['quote']}\"\n"
                    + new_ref + "\n",
                    encoding="utf-8",
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
        new_ref = f"\n- [[sales/videos/{date}_{video_id}]] — {data.get('title', '')}"
        if hook_file.exists():
            hook_file.write_text(
                hook_file.read_text(encoding="utf-8").rstrip() + new_ref + "\n",
                encoding="utf-8"
            )
        else:
            hook_file.write_text(f"""# {hook['name']}

## Pattern
{hook.get('pattern', '')}

## Example
> "{hook['text']}"

## Why It Works
{hook.get('why_it_works', '')}

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
