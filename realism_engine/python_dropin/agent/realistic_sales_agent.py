"""
Optional drop-in reference for Sales Pro realistic script generation.

Claude can copy/adapt this into agent/realistic_sales_agent.py.
It assumes the existing repo has config.py and uses anthropic.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic
from rich.console import Console

import config

console = Console()

REALISM_DIR = Path("realism_engine")
PROMPT_DIR = REALISM_DIR / "prompts"
EXAMPLE_DIR = REALISM_DIR / "examples"


@dataclass
class RealisticScriptRequest:
    product: str
    audience: str
    platform: str = "Cold call and cold email"
    tone: str = "Helpful local operator, direct, realistic, consultative, not hypey"
    goal: str = "Book a free 15-minute Website + Google Business Profile audit"
    city: str = ""
    industry: str = ""
    target_business: str = ""
    observed_issues: str = ""


def _read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing required realism engine file: {path}")
    return path.read_text(encoding="utf-8")


def load_prompt(name: str) -> str:
    return _read(PROMPT_DIR / name)


def fill_template(template: str, **kwargs: str) -> str:
    out = template
    for key, value in kwargs.items():
        out = out.replace("{{" + key + "}}", value or "")
    return out


def call_claude(prompt: str, max_tokens: int = 8192) -> str:
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def _try_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": text}


def _slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text)[:60].strip("_") or "script"


def load_default_truth_files() -> dict[str, str]:
    return {
        "proof_inventory": _read(EXAMPLE_DIR / "proof_inventory.local_web_gbp.md"),
        "approved_claims": _read(EXAMPLE_DIR / "approved_claims.local_web_gbp.md"),
        "banned_claims": _read(EXAMPLE_DIR / "banned_claims.local_web_gbp.md"),
    }


def load_relevant_knowledge(query: str) -> str:
    # Use existing semantic loader if available, otherwise load simple vault knowledge.
    try:
        from agent.sales_agent import load_vault_knowledge_semantic
        return load_vault_knowledge_semantic(query)
    except Exception:
        try:
            from agent.sales_agent import load_vault_knowledge
            return load_vault_knowledge()
        except Exception:
            return "No vault knowledge loaded."


def generate_realistic_script(req: RealisticScriptRequest) -> str:
    config.ensure_vault()
    truth = load_default_truth_files()
    master_rules = load_prompt("00_MASTER_RULES.md")

    query = f"{req.product} {req.audience} {req.platform} {req.goal} {req.city} {req.industry}"
    knowledge = load_relevant_knowledge(query)

    console.print("[cyan]Realism engine: extracting claims from vault knowledge…[/cyan]")
    claim_prompt = fill_template(
        load_prompt("02_EXTRACT_CLAIMS.md"),
        SOURCE_TEXT=knowledge,
    )
    extracted_claims_text = call_claude(master_rules + "\n\n" + claim_prompt)

    console.print("[cyan]Realism engine: grading claims against proof inventory…[/cyan]")
    grade_prompt = fill_template(
        load_prompt("03_GRADE_CLAIMS.md"),
        CLAIMS=extracted_claims_text,
        PROOF_INVENTORY=truth["proof_inventory"],
        OFFER=req.goal,
    )
    graded_claims_text = call_claude(master_rules + "\n\n" + grade_prompt)
    graded = _try_json(graded_claims_text)

    approved_claims = "\n".join(graded.get("approved_claim_bank", [])) if isinstance(graded, dict) else ""
    banned_claims = "\n".join(graded.get("banned_claim_bank", [])) if isinstance(graded, dict) else ""
    approved_claims = approved_claims + "\n\n" + truth["approved_claims"]
    banned_claims = banned_claims + "\n\n" + truth["banned_claims"]

    console.print("[cyan]Realism engine: generating safe script draft…[/cyan]")
    generation_prompt = fill_template(
        load_prompt("04_GENERATE_SCRIPT.md"),
        TARGET_BUSINESS=req.target_business,
        INDUSTRY=req.industry,
        CITY=req.city,
        OBSERVED_ISSUES=req.observed_issues,
        APPROVED_CLAIMS=approved_claims,
        BANNED_CLAIMS=banned_claims,
        OFFER=req.goal,
        PLATFORM=req.platform,
    )
    draft_script = call_claude(master_rules + "\n\n" + generation_prompt)

    console.print("[cyan]Realism engine: running field realism filter…[/cyan]")
    realism_prompt = fill_template(load_prompt("05_REALISM_FILTER.md"), SCRIPT=draft_script)
    realism_output = call_claude(master_rules + "\n\n" + realism_prompt)
    realism_json = _try_json(realism_output)
    realism_rewrite = realism_json.get("rewrite", realism_output) if isinstance(realism_json, dict) else realism_output

    console.print("[cyan]Realism engine: running truthfulness/compliance filter…[/cyan]")
    compliance_prompt = fill_template(load_prompt("06_COMPLIANCE_FILTER.md"), SCRIPT=realism_rewrite, PLATFORM=req.platform)
    compliance_output = call_claude(master_rules + "\n\n" + compliance_prompt)
    compliance_json = _try_json(compliance_output)
    clean_version = compliance_json.get("clean_version", compliance_output) if isinstance(compliance_json, dict) else compliance_output

    console.print("[cyan]Realism engine: packaging final output…[/cyan]")
    prior_outputs = json.dumps({
        "request": req.__dict__,
        "draft_script": draft_script,
        "realism_filter_output": realism_output,
        "compliance_filter_output": compliance_output,
        "approved_claims": approved_claims,
        "banned_claims": banned_claims,
        "clean_version": clean_version,
    }, indent=2)
    final_prompt = fill_template(load_prompt("07_FINAL_OUTPUT.md"), ALL_PRIOR_OUTPUTS=prior_outputs)
    final = call_claude(master_rules + "\n\n" + final_prompt, max_tokens=8192)

    date = datetime.now().strftime("%Y-%m-%d")
    out = config.VAULT_DIRS["scripts"] / f"{date}_realistic_{_slug(req.product)}.md"
    out.write_text(
        f"# Realistic Sales Script: {req.product}\n\n"
        f"Generated: {date}\n"
        f"Mode: realistic\n"
        f"Audience: {req.audience}\n"
        f"Platform: {req.platform}\n"
        f"Proof inventory: local_web_gbp\n"
        f"Claim filter: enabled\n"
        f"Realism filter: enabled\n"
        f"Compliance filter: enabled\n\n"
        f"{final}\n",
        encoding="utf-8",
    )
    console.print(f"[green]Realistic script saved:[/green] {out}")
    return final
