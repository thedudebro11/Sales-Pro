# Claude Implementation Prompt — Sales Pro Realism Engine

You are working inside my existing `Sales-Pro` repo.

I added a folder called `realism_engine/` containing prompts, docs, examples, schemas, and optional Python drop-in code.

Your job is to wire this into the repo carefully without breaking the current video ingestion pipeline.

## Current repo summary

The repo already has:

- `main.py` with commands like `add`, `batch`, `script`, `brain`, `reindex`, `serve`
- `pipeline/analyzer.py` for extracting sales intelligence from transcripts
- `agent/sales_agent.py` for generating scripts from the Obsidian vault
- `pipeline/vault_writer.py` for writing notes
- `web/app.py` for the FastAPI UI
- `config.py` for model/vault settings

## Problem to fix

The current script generator is too hype-driven. It rewards “devastatingly effective” sales copy and can produce bold claims like guaranteed top 3 Google Map Pack ranking, fake case studies, unsupported click statistics, and overaggressive language.

I want a realistic, evidence-aware sales pipeline.

## Main goal

Add a new script generation mode called `realistic` that runs this 7-step pipeline:

1. Extract tactics
2. Extract claims
3. Grade claims against proof inventory
4. Generate script using only approved claims
5. Run realism filter
6. Run compliance/truthfulness filter
7. Package final output

## Non-negotiable rules

- Do not remove the existing `script` command unless you replace it safely.
- Add a new command first, like:

```bash
python main.py realistic-script
```

or:

```bash
python main.py script --mode realistic
```

Prefer the least risky implementation.

- Do not invent case studies.
- Do not allow ranking guarantees.
- Do not allow exact statistics unless a verified source is supplied.
- Do not allow fake scarcity.
- Do not allow the final script to sound like an SEO guru.

## Files to use

Read and use:

```text
realism_engine/prompts/00_MASTER_RULES.md
realism_engine/prompts/01_EXTRACT_TACTICS.md
realism_engine/prompts/02_EXTRACT_CLAIMS.md
realism_engine/prompts/03_GRADE_CLAIMS.md
realism_engine/prompts/04_GENERATE_SCRIPT.md
realism_engine/prompts/05_REALISM_FILTER.md
realism_engine/prompts/06_COMPLIANCE_FILTER.md
realism_engine/prompts/07_FINAL_OUTPUT.md
realism_engine/examples/proof_inventory.local_web_gbp.md
realism_engine/examples/approved_claims.local_web_gbp.md
realism_engine/examples/banned_claims.local_web_gbp.md
```

Optional useful files:

```text
realism_engine/python_dropin/agent/realistic_sales_agent.py
realism_engine/python_dropin/pipeline/claim_filter.py
realism_engine/python_dropin/pipeline/source_ingestor.py
```

Use the drop-in files as a reference. You may copy/adapt them into the actual app structure if needed.

## Implementation requirements

### 1. Prompt loader

Add a helper that loads prompt markdown files from `realism_engine/prompts/`.

It should:

- Read by file name
- Replace placeholders like `{{SCRIPT}}`, `{{CLAIMS}}`, etc.
- Fail clearly if a prompt file is missing

### 2. Proof inventory loader

Add a helper that loads the proof inventory from:

```text
realism_engine/examples/proof_inventory.local_web_gbp.md
```

Later this can become user-editable.

### 3. Claim grading

The realistic generator should never use vault knowledge directly without filtering.

It should:

- Load relevant vault knowledge
- Extract claims from it
- Grade claims against proof inventory
- Merge in approved/banned claim bank files
- Pass only approved claims into script generation

### 4. Realistic script generation

The script generation prompt must include:

- Master rules
- Product/service
- Audience
- Platform
- Tone
- Goal
- Observed issues if provided
- Approved claims
- Banned claims
- Proof inventory

### 5. Realism filter

After initial script generation, pass it through `05_REALISM_FILTER.md`.

Use the rewritten version from the realism filter as the next stage input.

### 6. Compliance filter

Pass the realism-filtered version through `06_COMPLIANCE_FILTER.md`.

Use the clean version as the final packaging input.

### 7. Final output

Pass all prior outputs into `07_FINAL_OUTPUT.md`.

Save the final output to the vault under:

```text
sales/scripts/YYYY-MM-DD_realistic_<slug>.md
```

Include metadata at the top:

```markdown
# Realistic Sales Script: <product>

Generated: <date>
Mode: realistic
Audience: <audience>
Platform: <platform>
Proof inventory: local_web_gbp
Claim filter: enabled
Realism filter: enabled
Compliance filter: enabled
```

## CLI design

Add a command that asks:

```text
What are you selling?
Who is your target audience?
Platform/context?
Tone?
Goal/CTA?
City?
Industry?
Target business? optional
Observed issues? optional multiline or path
```

Good defaults:

```text
Platform/context: Cold call and cold email
Tone: Helpful local operator, direct, realistic, consultative, not hypey
Goal/CTA: Book a free 15-minute Website + Google Business Profile audit
```

## Web UI

Do not change the web UI until the CLI works.

After CLI works, add a “Realistic Mode” checkbox to `/api/script` and the frontend.

## Tests

Add lightweight tests or manual checks:

1. A script generated for local SEO must not contain:
   - “guarantee”
   - “top 3” unless framed as a goal, not promise
   - “70%” unless source supplied
   - fake client claims
2. The final script must include at least one low-pressure CTA.
3. The final script must include a banned-lines section or equivalent.
4. The final script must be shorter and more natural than the original hype script.

## Important implementation style

Be careful and incremental.

First, inspect the repo.
Then propose the file changes.
Then implement.
Then run syntax checks.
Then show me exactly how to test it.

Do not delete working code.
Do not rewrite the whole app.
Do not make unrelated changes.

## First test request to use after implementation

Use this test case:

```text
Product/service: Website rebuilds, website optimization, and Google Business Profile optimization
Audience: Small business owners who may be losing calls because their website is outdated, unclear, slow, or disconnected from their Google Business Profile
Platform/context: Cold call and cold email
Tone: Helpful local operator, direct, realistic, consultative, not hypey
Goal/CTA: Book a free 15-minute Website + Google Business Profile audit
City: Tucson, AZ
Industry: local service businesses
Observed issues: mobile site unclear, weak CTA, incomplete GBP, competitor profiles look more complete
```

The final output should sound like a real person calling a local business, not a hype SEO closer.
