"""
Optional source ingestor reference.

Use this for articles, PDFs converted to text, sales notes, or transcripts.
It saves raw source text into the vault so the realism engine can analyze it later.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import config


def _slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text)[:80].strip("_") or "source"


def save_source_text(title: str, source_type: str, reference: str, text: str) -> Path:
    config.ensure_vault()
    sources_dir = config.VAULT_PATH / "sales/sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    path = sources_dir / f"{date}_{_slug(title)}.md"
    path.write_text(
        f"# {title}\n\n"
        f"Date added: {date}\n"
        f"Source type: {source_type}\n"
        f"Reference: {reference}\n\n"
        f"## Source Text\n\n{text}\n",
        encoding="utf-8",
    )
    return path
