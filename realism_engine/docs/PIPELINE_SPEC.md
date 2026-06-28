# Sales Pro Realism Engine — Pipeline Spec

## Purpose

The existing Sales Pro system learns sales tactics from videos. That is useful, but it can accidentally copy exaggerated claims from internet sales content.

This engine adds judgment.

## New pipeline

```text
Source content
  ↓
01 Extract tactics
  ↓
02 Extract claims
  ↓
03 Grade claims against proof inventory
  ↓
04 Generate script using only approved claims
  ↓
05 Realism filter
  ↓
06 Compliance/truthfulness filter
  ↓
07 Final output package
```

## Source types supported

- YouTube/Instagram transcripts
- Sales training notes
- Call notes
- Cold email examples
- Articles
- PDFs converted to text
- Official documentation
- SEO research
- FTC/compliance guidance
- Real field feedback

## Data hierarchy

When sources disagree, use this priority:

1. User’s verified proof inventory
2. Official documentation and legal/compliance sources
3. User’s real call notes and client outcomes
4. Current industry research with date and source
5. Expert articles and blogs
6. Sales influencers and videos

Sales influencer content is useful for structure, not facts.

## Claim safety model

Every claim should be classified:

- GREEN: usable now
- YELLOW: soften before use
- RED: banned unless proof is added

## Script voice

The final script should sound like:

> “I looked at your business, noticed a few fixable issues, and can show you what I would fix first.”

Not:

> “I can dominate Google Maps and get you more leads guaranteed.”

## Success criteria

A script passes if:

- It can be said naturally by the user.
- It survives a 10-second interruption.
- It does not invent proof.
- It avoids Google ranking guarantees.
- It gives the owner a reason to take a 15-minute audit call.
- It sounds specific without being reckless.
