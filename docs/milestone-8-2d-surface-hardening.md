\
# Milestone 8.2D — Surface hardening

## Controls implemented

- request bodies are capped at 2 MB before JSON or multipart parsing
- public expensive operations use a 12-request/minute instance-local policy; ordinary analysis uses 30/minute; admin writes use 10/minute; private DB operations use 90/minute per authenticated user
- `X-Forwarded-For` is ignored unless the immediate ASGI peer is inside explicitly configured `TRUSTED_PROXY_CIDRS`
- the limiter remains instance-local and is not represented as distributed protection; Railway/edge controls or a shared rate-limit store remain the appropriate high-volume complement
- DOCX uploads are preflighted for archive count, expanded bytes, per-entry size, compression ratio, encrypted members, unsafe paths, and XML entity declarations before `python-docx` parses them
- PDF uploads are bounded by page count, pypdf decompression ceilings, page content-stream size, and extracted-text size; external JBIG2 decoder execution is disabled
- production FastAPI docs, ReDoc, and OpenAPI discovery are disabled while local development docs remain available
- backend API responses receive HSTS, MIME-sniffing, frame, referrer, permissions, cache-control, and production API CSP headers
- the static frontend receives a Clerk-compatible CSP plus HSTS, clickjacking, MIME-sniffing, referrer, and permissions headers
- backend and frontend runtime containers switch to non-root users

## Trusted proxy deployment note

`TRUSTED_PROXY_CIDRS` must contain only CIDRs for infrastructure that is actually trusted to overwrite or sanitize `X-Forwarded-For`. Leaving it unset is intentionally safe: MarketLens ignores forwarded client identity and uses the direct ASGI peer instead. Do not add broad public CIDRs merely to obtain per-user IP analytics.

## Browser CSP note

The frontend CSP permits the MarketLens backend plus Clerk Frontend API/protection/telemetry hosts required by the current authentication integration. It keeps `object-src` disabled and forbids framing through both CSP `frame-ancestors` and `X-Frame-Options`.

## Parser rationale

pypdf's security and text-extraction documentation explicitly provides decompression limits and recommends checking decoded page content before text extraction for memory safety. MarketLens lowers those limits because resumes are small documents. DOCX is an OOXML ZIP container, so archive expansion and XML declarations are validated before high-level parsing.

## Residual limitation

Rate limiting is still process-local. This work materially reduces single-instance and obvious abuse but does not claim a globally distributed quota. A shared store or platform edge policy can be added later if traffic volume requires it.
