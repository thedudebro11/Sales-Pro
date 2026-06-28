"""
Realistic script generation using the 7-step realism engine pipeline.

Pipeline:
  1. Extract tactics  (01)
  2. Extract claims   (02)
  3. Grade claims     (03)
  4. Generate script  (04)
  5. Realism filter   (05)
  6. Compliance filter(06)
  7. Final output     (07)
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

REALISM_DIR = Path(__file__).parent.parent / "realism_engine"
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


def _load_truth_files() -> dict[str, str]:
    return {
        "proof_inventory": _read(EXAMPLE_DIR / "proof_inventory.local_web_gbp.md"),
        "approved_claims": _read(EXAMPLE_DIR / "approved_claims.local_web_gbp.md"),
        "banned_claims":   _read(EXAMPLE_DIR / "banned_claims.local_web_gbp.md"),
    }


def _load_vault_knowledge(query: str) -> str:
    try:
        from agent.sales_agent import load_vault_knowledge_semantic
        return load_vault_knowledge_semantic(query)
    except Exception:
        try:
            from agent.sales_agent import load_vault_knowledge
            return load_vault_knowledge()
        except Exception:
            return "No vault knowledge loaded."


def generate_realistic_script(req: RealisticScriptRequest, on_step=None) -> str:
    def _step(n: int, msg: str):
        console.print(f"[bold cyan][{n}/7][/bold cyan] {msg}…")
        if on_step:
            on_step(n, msg)

    config.ensure_vault()
    truth = _load_truth_files()
    master_rules = load_prompt("00_MASTER_RULES.md")

    query = f"{req.product} {req.audience} {req.platform} {req.goal} {req.city} {req.industry}"
    knowledge = _load_vault_knowledge(query)

    _step(1, "Extracting claims from vault knowledge")
    claim_prompt = fill_template(
        load_prompt("02_EXTRACT_CLAIMS.md"),
        SOURCE_TEXT=knowledge,
    )
    extracted_claims_text = call_claude(master_rules + "\n\n" + claim_prompt)

    _step(2, "Grading claims against proof inventory")
    grade_prompt = fill_template(
        load_prompt("03_GRADE_CLAIMS.md"),
        CLAIMS=extracted_claims_text,
        PROOF_INVENTORY=truth["proof_inventory"],
        OFFER=req.goal,
    )
    graded_text = call_claude(master_rules + "\n\n" + grade_prompt)
    graded = _try_json(graded_text)

    approved_claims = "\n".join(graded.get("approved_claim_bank", [])) if isinstance(graded, dict) else ""
    banned_claims   = "\n".join(graded.get("banned_claim_bank",   [])) if isinstance(graded, dict) else ""
    approved_claims = approved_claims + "\n\n" + truth["approved_claims"]
    banned_claims   = banned_claims   + "\n\n" + truth["banned_claims"]

    _step(3, "Generating safe script draft")
    gen_prompt = fill_template(
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
    draft_script = call_claude(master_rules + "\n\n" + gen_prompt)

    _step(4, "Running field realism filter")
    realism_out = call_claude(
        master_rules + "\n\n" + fill_template(load_prompt("05_REALISM_FILTER.md"), SCRIPT=draft_script)
    )
    realism_json = _try_json(realism_out)
    realism_rewrite = realism_json.get("rewrite", realism_out) if isinstance(realism_json, dict) else realism_out

    _step(5, "Running compliance and truthfulness filter")
    compliance_out = call_claude(
        master_rules + "\n\n" + fill_template(
            load_prompt("06_COMPLIANCE_FILTER.md"),
            SCRIPT=realism_rewrite,
            PLATFORM=req.platform,
        )
    )
    compliance_json = _try_json(compliance_out)
    clean_version = compliance_json.get("clean_version", compliance_out) if isinstance(compliance_json, dict) else compliance_out

    _step(6, "Packaging final output")
    prior_outputs = json.dumps({
        "request":                  req.__dict__,
        "draft_script":             draft_script,
        "realism_filter_output":    realism_out,
        "compliance_filter_output": compliance_out,
        "approved_claims":          approved_claims,
        "banned_claims":            banned_claims,
        "clean_version":            clean_version,
    }, indent=2)
    final = call_claude(
        master_rules + "\n\n" + fill_template(load_prompt("07_FINAL_OUTPUT.md"), ALL_PRIOR_OUTPUTS=prior_outputs),
        max_tokens=8192,
    )

    _step(7, "Saving to vault")
    date = datetime.now().strftime("%Y-%m-%d")
    out_path = config.VAULT_DIRS["scripts"] / f"{date}_realistic_{_slug(req.product)}.md"
    out_path.write_text(
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
    console.print(f"[green]Realistic script saved:[/green] {out_path}")
    return final
