# 10_OBSERVED_ISSUES_TO_SCRIPT_INPUT.md

You are converting a manual business audit into clean script input.

## Input

Business audit notes:
{{AUDIT_NOTES}}

## Output format

Return valid JSON matching this structure:

```json
{
  "target_business": "name",
  "industry": "industry",
  "city": "city",
  "observed_issues": [
    {
      "issue": "specific issue observed",
      "category": "website | mobile | speed | CTA | trust | GBP | reviews | photos | services | competitors | NAP | content",
      "confidence": "confirmed | likely | needs_checking",
      "safe_way_to_say_it": "phrase for outreach",
      "do_not_say": "overclaim to avoid"
    }
  ],
  "best_hook": "one realistic hook based on the evidence",
  "audit_offer_angle": "why the free audit is worth 15 minutes"
}
```

## Rules

- If you did not verify it, mark it as needs_checking.
- Do not say “this is costing you customers” unless there is evidence.
- Prefer “may be costing you calls” or “could be making people less likely to call.”
- Specific beats dramatic.
