# Install Guide

## Step 1 — Put the pack into your repo

Unzip this pack.

Copy the folder into your Sales Pro repo root:

```text
Sales-Pro/realism_engine/
```

## Step 2 — Open the repo in VS Code

Open the full `Sales-Pro` folder, not just this pack.

## Step 3 — Give Claude the implementation prompt

Paste the full contents of:

```text
realism_engine/claude/CLAUDE_IMPLEMENTATION_PROMPT.md
```

into Claude Code.

## Step 4 — Tell Claude to implement in phases

Do not let Claude rewrite everything at once.

Make it do this order:

1. Add prompt loading.
2. Add proof inventory loading.
3. Add claim grading.
4. Add realistic script generation.
5. Add CLI command.
6. Add web UI option only after CLI works.
7. Add tests.

## Step 5 — Test with your actual offer

Use this as the first test request:

```text
Product/service: Website rebuilds, website optimization, and Google Business Profile optimization
Audience: Small service business owners in Tucson
Platform: Cold call and cold email
Tone: Helpful local operator, direct but not hypey
Goal: Book a free 15-minute website + GBP audit
Proof inventory: examples/proof_inventory.local_web_gbp.md
Observed issues: examples/observed_issues.example.md
```

## Step 6 — Reject any output that violates the banned claim bank

If Claude produces “top 3 guaranteed,” “70% of clicks,” or fake case studies, it failed the assignment.
