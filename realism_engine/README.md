# Sales Pro Realism Engine Pack

This pack turns Sales Pro from a hype-based sales script generator into a practical, evidence-aware outreach system.

The goal is simple: **strong sales scripts that a real small business owner might actually believe**.

## What this adds

- A 7-step prompt pipeline for turning videos, articles, PDFs, and field notes into safer outreach.
- A proof inventory so the AI only makes claims the business can actually support.
- A banned-claim bank to stop fake SEO guarantees like “I can get you top 3.”
- A realism filter that rewrites scripts into natural small-business language.
- A compliance/truthfulness filter for cold email and cold call risk.
- A Claude implementation prompt for wiring the system into the existing Sales Pro repo.
- Optional Python drop-in modules Claude can adapt instead of building from scratch.

## Recommended folder location

Copy this folder into the root of your `Sales-Pro` repo:

```text
Sales-Pro/
  realism_engine/
    prompts/
    schemas/
    examples/
    docs/
    claude/
    python_dropin/
```

Or copy the contents directly into:

```text
Sales-Pro/
  prompts/realism_engine/
  docs/realism_engine/
  examples/realism_engine/
```

The Claude prompt in `claude/CLAUDE_IMPLEMENTATION_PROMPT.md` tells Claude exactly how to decide the final structure.

## The pipeline

1. **Extract tactics** from videos, articles, PDFs, transcripts, and notes.
2. **Extract claims** from those sources.
3. **Grade claims** against actual proof.
4. **Generate the script** using only approved claims.
5. **Run realism filter** so it sounds like a real local operator.
6. **Run compliance/truthfulness filter** so it avoids guarantees and deceptive claims.
7. **Package final output** into recommended, aggressive, and soft versions.

## Main philosophy

Sales Pro should not sound like an SEO guru.

It should sound like:

> A helpful local operator who already looked at the business, found a few fixable issues, and wants to show the owner what may be holding them back.

## Before using

Fill this out first:

```text
examples/proof_inventory.local_web_gbp.md
```

That file is the truth layer. If the proof inventory says you do not have case studies yet, the AI is not allowed to invent case studies.

## Best default offer

A free 15-minute Website + Google Business Profile audit where the business owner gets:

1. A live look at their website and GBP.
2. A competitor comparison.
3. A list of weak or missing trust/conversion signals.
4. The top 3 to 5 fixes to prioritize first.

## Never promise

- Guaranteed top 3 Google Map Pack ranking.
- Guaranteed calls.
- Guaranteed revenue.
- Exact click percentages without a verified source.
- Fake client results.
- Fake scarcity.
- Fake “I am not selling anything” language when there is clearly a business goal.
