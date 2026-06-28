#!/usr/bin/env python3
"""
Sales Pro — Instagram → Sales Brain → Script Generator

Usage:
  python main.py add <url>             # Download, transcribe, analyze, add to brain
  python main.py batch <file.txt>      # Process multiple URLs from a text file
  python main.py script                # Generate a sales script from the brain
  python main.py brain                 # Show brain stats
  python main.py reindex               # Rebuild semantic embeddings index
  python main.py serve [--port 8000]   # Launch web UI
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


def cmd_batch(filepath: str):
    """Process a text file of URLs — one per line, # for comments."""
    from pipeline.vault_writer import _find_existing_note_by_url

    batch_file = Path(filepath)
    if not batch_file.exists():
        console.print(f"[red]File not found:[/red] {filepath}")
        return

    raw_lines = batch_file.read_text(encoding="utf-8").splitlines()
    urls = [l.strip() for l in raw_lines if l.strip() and not l.strip().startswith("#")]

    if not urls:
        console.print("[yellow]No URLs found in file.[/yellow]")
        return

    console.print(Panel(f"[bold]{len(urls)} URLs[/bold] to process from [cyan]{filepath}[/cyan]", title="Sales Pro Batch"))

    processed = skipped = failed = 0
    failed_urls: list[str] = []

    for i, url in enumerate(urls, 1):
        console.rule(f"[bold cyan][{i}/{len(urls)}][/bold cyan] {url[:80]}")

        if _find_existing_note_by_url(url):
            console.print(f"[yellow]Skipping duplicate:[/yellow] already in vault")
            skipped += 1
            continue

        try:
            cmd_add(url)
            processed += 1
        except Exception as exc:
            console.print(f"[red]Failed:[/red] {exc}")
            failed += 1
            failed_urls.append(url)

    summary = (
        f"[green]✓ Processed:[/green] {processed}\n"
        f"[yellow]⊘ Skipped (duplicates):[/yellow] {skipped}\n"
        f"[red]✗ Failed:[/red] {failed}"
    )
    if failed_urls:
        summary += "\n\n[bold red]Failed URLs:[/bold red]\n" + "\n".join(f"  {u}" for u in failed_urls)
    console.print(Panel(summary, title="Batch Complete"))


def cmd_enrich():
    """Fill empty sections across all vault notes using Claude."""
    from pipeline.enricher import enrich_all
    enrich_all()


def cmd_reindex():
    """Rebuild the semantic embeddings index from all existing vault notes."""
    from pipeline.vault_writer import reindex_vault_embeddings
    reindex_vault_embeddings()


def cmd_serve(port: int = 8000):
    """Launch the Sales Pro web UI."""
    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn not installed.[/red] Run: pip install 'fastapi[standard]' uvicorn")
        return

    console.print(Panel(
        f"[bold green]Sales Pro Web UI[/bold green]\n"
        f"Open [link=http://localhost:{port}]http://localhost:{port}[/link] in your browser\n"
        f"Press [bold]Ctrl+C[/bold] to stop",
        title="Sales Pro",
    ))

    from web.app import app
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


def cmd_realistic_script():
    """Interactive 7-step realistic script generator with claim grading and compliance filter."""
    from agent.realistic_sales_agent import RealisticScriptRequest, generate_realistic_script

    console.print(Panel(
        "[bold]Realistic Script Generator[/bold]\n"
        "7-step pipeline: claim grading → realism filter → compliance filter\n"
        "No guarantees. No fake stats. No guru language.",
        title="Sales Pro — Realistic Mode",
    ))

    product  = console.input("[bold]What are you selling?[/bold] → ")
    audience = console.input("[bold]Who is your target audience?[/bold] → ")
    platform = console.input("[bold]Platform/context[/bold] (default: Cold call and cold email): ").strip() \
               or "Cold call and cold email"
    tone     = console.input("[bold]Tone[/bold] (default: Helpful local operator, direct, realistic): ").strip() \
               or "Helpful local operator, direct, realistic, consultative, not hypey"
    goal     = console.input("[bold]Goal / CTA[/bold] (default: Book a free 15-min audit): ").strip() \
               or "Book a free 15-minute Website + Google Business Profile audit"
    city     = console.input("[bold]City[/bold] (e.g. Tucson, AZ): ").strip()
    industry = console.input("[bold]Industry[/bold] (e.g. local service businesses): ").strip()
    target   = console.input("[bold]Target business name[/bold] (optional, press Enter to skip): ").strip()

    console.print("[dim]Observed issues (one per line, blank line when done):[/dim]")
    issues_lines: list[str] = []
    while True:
        line = console.input("  → ")
        if not line.strip():
            break
        p = Path(line.strip())
        if p.exists():
            issues_lines.append(p.read_text(encoding="utf-8"))
        else:
            issues_lines.append(line.strip())
    observed_issues = "\n".join(issues_lines)

    req = RealisticScriptRequest(
        product=product,
        audience=audience,
        platform=platform,
        tone=tone,
        goal=goal,
        city=city,
        industry=industry,
        target_business=target,
        observed_issues=observed_issues,
    )

    final = generate_realistic_script(req)
    console.print(Panel(final, title=f"Realistic Script: {product}", expand=False))


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

    add_p = sub.add_parser("add", help="Add a video to the brain")
    add_p.add_argument("url", help="Instagram or YouTube video URL")

    batch_p = sub.add_parser("batch", help="Process multiple URLs from a text file")
    batch_p.add_argument("filepath", help="Path to text file with one URL per line")

    sub.add_parser("script", help="Generate a sales script from the brain")
    sub.add_parser("realistic-script", help="Generate a realistic, claim-filtered script (7-step pipeline)")
    sub.add_parser("brain", help="Show brain stats")
    sub.add_parser("enrich", help="Fill empty sections in all vault notes using Claude")
    sub.add_parser("reindex", help="Rebuild the semantic embeddings index")

    serve_p = sub.add_parser("serve", help="Launch the web UI")
    serve_p.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")

    args = parser.parse_args()

    if args.command == "add":
        cmd_add(args.url)
    elif args.command == "batch":
        cmd_batch(args.filepath)
    elif args.command == "script":
        cmd_script()
    elif args.command == "realistic-script":
        cmd_realistic_script()
    elif args.command == "brain":
        cmd_brain()
    elif args.command == "enrich":
        cmd_enrich()
    elif args.command == "reindex":
        cmd_reindex()
    elif args.command == "serve":
        cmd_serve(args.port)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

