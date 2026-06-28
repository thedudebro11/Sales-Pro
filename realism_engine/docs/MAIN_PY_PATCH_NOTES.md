# main.py Patch Notes for Claude

Add a new command without removing existing behavior.

Suggested command:

```bash
python main.py realistic-script
```

Suggested function:

```python
def cmd_realistic_script():
    from agent.realistic_sales_agent import RealisticScriptRequest, generate_realistic_script

    product = console.input("[bold]What are you selling?[/bold] → ")
    audience = console.input("[bold]Who is your target audience?[/bold] → ")
    platform = console.input("[bold]Platform/context[/bold] (default: Cold call and cold email): ").strip() or "Cold call and cold email"
    tone = console.input("[bold]Tone[/bold] (default: Helpful local operator): ").strip() or "Helpful local operator, direct, realistic, consultative, not hypey"
    goal = console.input("[bold]Goal / CTA[/bold] (default: Book a free 15-minute audit): ").strip() or "Book a free 15-minute Website + Google Business Profile audit"
    city = console.input("[bold]City[/bold] (optional): ").strip()
    industry = console.input("[bold]Industry[/bold] (optional): ").strip()
    target_business = console.input("[bold]Target business[/bold] (optional): ").strip()
    observed_issues = console.input("[bold]Observed issues[/bold] (optional): ").strip()

    req = RealisticScriptRequest(
        product=product,
        audience=audience,
        platform=platform,
        tone=tone,
        goal=goal,
        city=city,
        industry=industry,
        target_business=target_business,
        observed_issues=observed_issues,
    )
    script = generate_realistic_script(req)
    console.print(Panel(script, title=f"Realistic Sales Script: {product}", expand=False))
```

Then add to parser:

```python
sub.add_parser("realistic-script", help="Generate an evidence-aware realistic sales script")
```

And command routing:

```python
elif args.command == "realistic-script":
    cmd_realistic_script()
```
