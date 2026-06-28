# 08_REAL_CALL_FEEDBACK.md

You are analyzing field feedback from real cold calls, emails, voicemails, or text follow-ups.

Your job is to turn real-world reactions into better future scripts.

## Input

Call/email notes:
{{FIELD_NOTES}}

Current script:
{{CURRENT_SCRIPT}}

## Output format

Return valid JSON matching this structure:

```json
{
  "what_happened": "summary",
  "prospect_reactions": ["reaction"],
  "objections_heard": ["objection"],
  "phrases_that_worked": ["phrase"],
  "phrases_that_failed": ["phrase"],
  "new_data_points": [
    {
      "data_point": "field learning",
      "confidence": "low | medium | high",
      "how_to_use_it_next_time": "recommendation"
    }
  ],
  "updated_script_recommendation": "rewrite"
}
```

## Rules

- Do not overfit one call.
- If a pattern repeats across several calls, flag it as important.
- Real field data beats influencer advice.
- Preserve exact wording if the prospect said something useful.
