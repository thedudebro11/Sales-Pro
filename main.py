#!/usr/bin/env python3
"""
Sales Pro — Instagram → Sales Brain → Script Generator

Usage:
  python main.py add <instagram_url>          # Download, transcribe, analyze, add to brain
  python main.py script                       # Generate a sales script from the brain
  python main.py brain                        # Show brain stats
"""

import sys
import argparse
import tempfile
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def cmd_add(url: str):
    """Full pipeline: download → transcribe → analyze → write to vault."""
    from pipeline.downloader import download_instagram_video, extract_audio
    from pipeline.transcriber import transcribe
    from pipeline.analyzer import analyze
    from pipeline.vault_writer import write_to_vault

    with tempfile.TemporaryDirectory(prefix="sales_pro_") as tmpdir:
        tmp = Path(tmpdir)
        video_path = download_instagram_video(url, output_dir=tmp)
        audio_path = extract_audio(video_path)
        transcript = transcribe(audio_path)
        data = analyze(transcript, url)
        note_path = write_to_vault(data)

    console.print(Panel(
        f"[bold green]Brain updated![/bold green]\n"
        f"Title: {data.get('title')}\n"
        f"Tactics: {len(data.get('tactics', []))}\n"
        f"Hooks: {len(data.get('hooks', []))}\n"
        f"Objection handles: {len(data.get('objection_handles', []))}\n"
        f"Note: {note_path}",
        title="Sales Pro",
    ))


def cmd_script():
    """Interactive script generator using the brain."""
    from agent.sales_agent import generate_script

    console.print(Panel("[bold]Sales Script Generator[/bold]\nAnswering a few questions to craft your script.", title="Sales Pro"))

    product  = console.input("[bold]What are you selling?[/bold] → ")
    audience = console.input("[bold]Who is your target audience?[/bold] → ")
    platform = console.input("[bold]Platform/context[/bold] (default: Instagram Reels): ").strip() or "Instagram Reels / TikTok"
    tone     = console.input("[bold]Tone[/bold] (default: Conversational and confident): ").strip() or "Conversational and confident"
    goal     = console.input("[bold]Goal / CTA[/bold] (default: Book a call / DM): ").strip() or "Book a call / DM for more info"

    script = generate_script(product, audience, platform, tone, goal)
    console.print(Panel(script, title=f"Sales Script: {product}", expand=False))


def cmd_brain():
    """Show brain stats."""
    import config
    config.ensure_vault()

    table = Table(title="Sales Brain Stats")
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="green")

    for name, path in config.VAULT_DIRS.items():
        count = len(list(path.glob("*.md")))
        table.add_row(name.title(), str(count))

    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Sales Pro — Instagram → Sales Brain")
    sub = parser.add_subparsers(dest="command")

    add_p = sub.add_parser("add", help="Add an Instagram video to the brain")
    add_p.add_argument("url", help="Instagram video URL")

    sub.add_parser("script", help="Generate a sales script from the brain")
    sub.add_parser("brain", help="Show brain stats")

    args = parser.parse_args()

    if args.command == "add":
        cmd_add(args.url)
    elif args.command == "script":
        cmd_script()
    elif args.command == "brain":
        cmd_brain()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
