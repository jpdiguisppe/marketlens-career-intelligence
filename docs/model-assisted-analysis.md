# Model-Assisted Smart Fit Plan

MarketLens now has a safe backend foundation for model-assisted extraction, but the public UI should not expose it until the deployment is intentionally configured and the privacy copy is updated.

## Goal

Use a model to extract structured career-fit signals from messy resume and job-description text, then let MarketLens score and display the result with deterministic code.

The model should help with:

- skills and tools that are not already in the curated ontology
- context labels such as frontend, backend, database, cloud, IT support, academic, productivity tools, and security
- direct vs related vs mentioned-only evidence
- hard constraints such as clearance, citizenship, degree, years of experience, work authorization, and travel
- uncertainty notes when the text is ambiguous

The model should not be the final unchecked writer of the report. It should produce schema-validated extraction data that the backend validates, scores, and turns into a calm coaching report.

## Security stance

Model-assisted analysis is disabled by default.

Required backend environment variables:

```text
AI_ANALYSIS_ENABLED=true
OPENAI_API_KEY=<backend-only secret>
OPENAI_MODEL=<chosen model>
```

Optional backend environment variables:

```text
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TIMEOUT_SECONDS=12
```

Rules:

- Never put provider keys in the frontend.
- Never commit provider keys.
- Do not save raw resume or job-description text to the shared database.
- Do not log raw resume or job-description text.
- Redact obvious emails, phone numbers, URLs, GitHub/LinkedIn URLs, and address-like lines before provider calls.
- Treat redaction as a best-effort safety layer, not a full privacy guarantee.
- Send provider requests with `store=false`.
- Use strict schema validation before trusting model output.
- Fall back to deterministic analysis when the provider is disabled, missing configuration, times out, or returns invalid output.
- Keep rate limits on public analysis endpoints.

## Current backend behavior

`POST /analysis/smart` accepts:

```json
{
  "resume_text": "...",
  "job_description": "...",
  "use_model_assisted": true
}
```

When `use_model_assisted` is false, MarketLens uses the deterministic engine.

When `use_model_assisted` is true but the backend is not configured, MarketLens falls back to deterministic analysis and returns metadata like:

```json
{
  "analysis_engine": "deterministic",
  "model_assisted_status": "fallback_unavailable: Model-assisted analysis is disabled for this deployment."
}
```

When model-assisted extraction is enabled and succeeds, MarketLens merges model-extracted skills and requirements into the deterministic pipeline and returns:

```json
{
  "analysis_engine": "model_assisted",
  "model_assisted_status": "used"
}
```

## Current security tests

The backend test suite now checks that:

- obvious contact details are redacted while technical skills remain available for extraction
- provider prompts use redacted text
- requesting model-assisted mode while it is disabled falls back to deterministic analysis
- missing backend provider secrets prevent provider calls
- schema validation can carry unknown skills such as `RabbitMQ`

## Next implementation steps

1. Run a controlled local provider test with a real backend-only API key.
2. Add a frontend opt-in control with clear privacy language.
3. Add provider-status messaging so users know whether deterministic or model-assisted analysis was used.
4. Add more evaluation cases for unknown tools and technologies.
5. Add stronger redaction safeguards for additional personal identifiers if testing exposes misses.
6. Consider Supabase later for auth, saved reports, and row-level ownership once saving user reports becomes a product need.

## Why Supabase is later

Supabase can help with authentication, user ownership, saved reports, and row-level security. It does not replace the need for safe provider calls, explicit opt-in, schema validation, secret management, and no raw-text logging.
