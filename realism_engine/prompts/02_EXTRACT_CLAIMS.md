# 02_EXTRACT_CLAIMS.md

You are analyzing a sales, SEO, marketing, legal/compliance, buyer psychology, cold call, cold email, or local business source.

Your job is to extract every factual or performance claim that could appear in a sales script.

## Input

{{SOURCE_TEXT}}

## Output format

Return valid JSON matching this structure:

```json
{
  "claims_extracted": [
    {
      "exact_claim": "claim text",
      "claim_category": "SEO | Google Business Profile | website_speed | conversion | reviews | cold_calling | cold_email | buyer_psychology | legal_compliance | case_study | statistic | opinion",
      "objective_or_subjective": "objective | subjective | mixed",
      "source_provides_evidence": true,
      "safe_to_repeat": false,
      "requires_source_citation": true,
      "could_become_outdated": true,
      "could_mislead_in_sales_script": true,
      "why": "short explanation"
    }
  ],
  "dangerous_claims": ["claim"],
  "safe_rewrites": [
    {
      "risky": "We can get you top 3 on Google Maps.",
      "safe": "We can improve the controllable factors that make your business more competitive in local search."
    }
  ]
}
```

## Rules

- Do not generate a sales script yet.
- Extract claims even when they are implied, not just directly stated.
- Mark statistics as risky unless the source includes evidence.
- Mark case studies as unusable unless the user owns or can prove the case study.
- Mark Google ranking guarantees as dangerous.
