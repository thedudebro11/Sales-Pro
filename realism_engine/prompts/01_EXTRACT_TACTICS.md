# 01_EXTRACT_TACTICS.md

You are analyzing a sales video, transcript, article, PDF, call breakdown, field note, or sales training document.

Your job is to extract useful sales tactics without copying hype, fake claims, or unrealistic language.

## Input

{{SOURCE_TEXT}}

## Output format

Return valid JSON matching this structure:

```json
{
  "source_summary": "plain English summary of what this source teaches",
  "useful_tactics": [
    {
      "tactic_name": "short name",
      "what_it_does_psychologically": "why the tactic works",
      "conversation_stage": "opener | discovery | pitch | objection | close | follow_up | email | voicemail",
      "small_business_owner_reaction": "how a skeptical local owner might react",
      "risk_level": "safe | aggressive | risky",
      "realistic_local_business_version": "how to say this without hype"
    }
  ],
  "phrases_worth_saving": ["phrase"],
  "phrases_to_avoid": ["phrase"],
  "small_business_translation": ["realistic rewrite"],
  "final_tactic_score": 1
}
```

## Rules

- Do not generate a full script yet.
- Separate useful persuasion structure from exaggerated claims.
- A tactic can be useful even if the source itself sounds hypey.
- If a phrase sounds fake or manipulative, mark it as avoid.
- Prefer real-world small business language.
