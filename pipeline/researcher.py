"""
Runs PageSpeed analysis + Claude research brief for a business, saves to vault,
and creates/updates the prospect record in the DB.
"""
import json
from datetime import date
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import anthropic
import config
from database import get_db

RESEARCH_PROMPT = """You are a sharp local business analyst helping a digital marketing consultant prepare for a cold outreach call.

Business: {business_name}
City: {city}
Industry: {industry}
Website: {website_url}

PageSpeed Data (mobile):
{pagespeed_data}

GBP / Owner Notes:
{gbp_notes}

Write a research brief in markdown with these exact sections:

## Quick Intel
Who they are, likely decision-maker title, 2-3 typical pain points for this industry.

## Observed Gaps
What's actually broken or missing — be specific, reference the scores and notes.

## The Angle
One sentence: the single strongest reason to call, framed as a fixable gap (not a pitch).

## Opening Line
One natural, specific conversation starter that references something real. Should NOT sound like a sales pitch.

## Likely Objections
Top 3 objections with one-sentence counters each.

## Observed Issues (copyable)
A bulleted list of specific issues suitable for pasting into the Script generator's Observed Issues field.

Keep it scannable and tactical. No fluff."""


def run_pagespeed(url: str) -> dict:
    if not url:
        return {}
    try:
        params = urlencode({"url": url, "strategy": "mobile"})
        api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?{params}"
        with urlopen(api_url, timeout=15) as resp:
            data = json.loads(resp.read())
        cats = data.get("lighthouseResult", {}).get("categories", {})
        audits = data.get("lighthouseResult", {}).get("audits", {})
        return {
            "performance": round((cats.get("performance", {}).get("score") or 0) * 100),
            "accessibility": round((cats.get("accessibility", {}).get("score") or 0) * 100),
            "seo": round((cats.get("seo", {}).get("score") or 0) * 100),
            "lcp": audits.get("largest-contentful-paint", {}).get("displayValue", "n/a"),
            "fcp": audits.get("first-contentful-paint", {}).get("displayValue", "n/a"),
            "tbt": audits.get("total-blocking-time", {}).get("displayValue", "n/a"),
            "cls": audits.get("cumulative-layout-shift", {}).get("displayValue", "n/a"),
        }
    except (URLError, Exception):
        return {}


def research_business(
    business_name: str,
    city: str = "",
    industry: str = "",
    website_url: str = "",
    gbp_notes: str = "",
    on_step=None,
) -> dict:

    def step(msg):
        if on_step:
            on_step(msg)

    step("Running PageSpeed analysis…")
    scores = run_pagespeed(website_url)

    if scores:
        pagespeed_str = (
            f"Performance: {scores.get('performance')}  |  "
            f"Accessibility: {scores.get('accessibility')}  |  SEO: {scores.get('seo')}\n"
            f"LCP: {scores.get('lcp')}  |  FCP: {scores.get('fcp')}  |  "
            f"TBT: {scores.get('tbt')}  |  CLS: {scores.get('cls')}"
        )
    else:
        pagespeed_str = "No URL provided or PageSpeed unavailable."

    step("Generating research brief with Claude…")
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": RESEARCH_PROMPT.format(
                    business_name=business_name,
                    city=city,
                    industry=industry,
                    website_url=website_url or "not provided",
                    pagespeed_data=pagespeed_str,
                    gbp_notes=gbp_notes or "not provided",
                ),
            }
        ],
    )
    brief = msg.content[0].text.strip()

    step("Saving to vault…")
    config.ensure_vault()
    slug = (business_name or "unknown").lower().replace(" ", "_")[:30]
    fname = f"{date.today().isoformat()}_{slug}_research.md"
    note_path = config.VAULT_DIRS["research"] / fname
    note_path.write_text(f"# Research — {business_name}\n\n{brief}\n", encoding="utf-8")

    step("Creating/updating prospect record…")
    conn = get_db()
    prospect_id = None
    try:
        existing = conn.execute(
            "SELECT id FROM prospects WHERE business_name = ? COLLATE NOCASE LIMIT 1",
            (business_name,),
        ).fetchone()
        if existing:
            prospect_id = existing["id"]
            conn.execute(
                "UPDATE prospects SET "
                "city=COALESCE(NULLIF(city,''),?), "
                "industry=COALESCE(NULLIF(industry,''),?), "
                "website_url=COALESCE(NULLIF(website_url,''),?), "
                "updated_at=datetime('now') WHERE id=?",
                (city, industry, website_url, prospect_id),
            )
        else:
            cur = conn.execute(
                "INSERT INTO prospects (business_name, city, industry, website_url, stage) VALUES (?,?,?,?,?)",
                (business_name, city, industry, website_url, "researched"),
            )
            prospect_id = cur.lastrowid
        conn.commit()
    finally:
        conn.close()

    observed_issues = ""
    if "## Observed Issues" in brief:
        observed_issues = brief.split("## Observed Issues")[-1].strip().split("\n##")[0].strip()

    step("Done.")
    return {
        "brief": brief,
        "scores": scores,
        "prospect_id": prospect_id,
        "observed_issues": observed_issues,
        "note_path": str(note_path),
    }
