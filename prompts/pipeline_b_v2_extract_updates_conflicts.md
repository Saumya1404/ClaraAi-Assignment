# Pipeline B (v2) - Extract Updates and Conflicts Prompt

Source workflow: `n8n/workflows/Pipeline B(v2) - Complete.json`
Source node: `LLM Extract Updates + Conflicts`

```text
You are an AI that updates a business account memo based on an onboarding call transcript.

Here is the existing v1 account memo:
{{ $json.v1_memo_text }}

Here is the onboarding call transcript:
{{ $json.transcript }}

Your task:
1. Extract ALL new or updated information from the onboarding transcript.
2. For EACH field in the memo, determine if the onboarding transcript provides an update.
3. Produce a response as ONLY valid JSON with exactly these top-level keys:

{
  "updated_memo": { ... the full updated account memo with all fields ... },
  "changes": [
    {
      "field": "field_name",
      "v1_value": "old value or null",
      "v2_value": "new value",
      "reason": "why this changed based on transcript",
      "conflict": false
    }
  ],
  "conflicts": [
    {
      "field": "field_name",
      "v1_value": "old value",
      "v2_value": "new contradicting value",
      "resolution": "which value was kept and why"
    }
  ]
}

Rules:
- updated_memo must include ALL original fields, updated where the transcript provides new info
- If a field is not mentioned in the onboarding transcript, keep the v1 value unchanged
- A conflict occurs when the onboarding transcript directly contradicts a v1 value (not just adds to it)
- Mark conflict: true in changes array when there is a conflict
- Never invent data. Only use information explicitly stated in the transcript.
- Do not include account_id, version, or created_at in updated_memo - those are added programmatically
- Return ONLY valid JSON, no explanation, no markdown backticks
```
