# 09_ARTICLE_PDF_INGEST.md

You are ingesting an article, PDF, official documentation page, blog post, legal guide, SEO study, or marketing research document.

Your job is to turn long-form written material into structured Sales Pro knowledge.

## Input

Source title:
{{SOURCE_TITLE}}

Source URL or file name:
{{SOURCE_REFERENCE}}

Source type:
{{SOURCE_TYPE}}

Source text:
{{SOURCE_TEXT}}

## Output format

Return valid JSON matching this structure:

```json
{
  "source_summary": "what this document says",
  "source_type": "official_documentation | legal_compliance | industry_research | expert_opinion | case_study | blog_post | unknown",
  "trust_level": "high | medium | low",
  "date_sensitivity": "stable | may_change | current_events_sensitive",
  "key_facts": [
    {
      "fact": "fact",
      "safe_sales_use": "how this can be used safely",
      "risk": "low | medium | high"
    }
  ],
  "useful_script_angles": ["angle"],
  "claims_to_avoid": ["claim"],
  "safe_language_bank": ["phrase"],
  "requires_source_citation": true
}
```

## Rules

- Official sources are more trustworthy than sales blogs.
- Opinion pieces should not be treated as facts.
- Statistics require source/date context.
- Do not turn research into guarantees.
- For Google/SEO, prefer cautious language.
