# Pipeline B (v2) - Identify Account Prompt

Source workflow: `n8n/workflows/Pipeline B(v2) - Complete.json`
Source node: `LLM Identify Account`

```text
You are an AI that identifies the company from an onboarding call transcript.

Extract ONLY the company name from this transcript and return a JSON object with exactly these fields:
- company_name (the exact company name mentioned)
- account_id (lowercase, spaces and special chars replaced with underscores)

Return ONLY valid JSON, no explanation, no markdown backticks.

Transcript:
{{ $json.data }}
```
