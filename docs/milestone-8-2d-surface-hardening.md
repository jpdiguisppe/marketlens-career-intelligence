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
- the static frontend receives a Clerk-compatible CSP plus HSTS, clickjacking, MIME-sniffing, referrer, permissions, and no-store headers
- the frontend CSP receives the validated configured API origin at container startup rather than hard-coding one deployment hostname
- backend and frontend runtime containers switch to non-root users
- the Uvicorn access-log sanitizer preserves the formatter's structured argument contract while continuing to sanitize user-influenced strings

## Trusted proxy deployment note

`TRUSTED_PROXY_CIDRS` must contain only CIDRs for infrastructure that is actually trusted to overwrite or sanitize `X-Forwarded-For`. Leaving it unset is intentionally safe: MarketLens ignores forwarded client identity and uses the direct ASGI peer instead. Do not add broad public CIDRs merely to obtain per-user IP analytics.

## Browser CSP note

The frontend CSP permits the configured MarketLens API origin plus Clerk Frontend API/protection/telemetry hosts required by the current authentication integration. It keeps `object-src` disabled and forbids framing through both CSP `frame-ancestors` and `X-Frame-Options`. The configured API URL is normalized to an HTTP(S) origin before substitution into Nginx configuration; malformed values fall back to the local development origin rather than being copied into CSP syntax.

## Parser rationale

pypdf's security and text-extraction documentation explicitly provides decompression limits and recommends checking decoded page content before text extraction for memory safety. MarketLens lowers those limits because resumes are small documents. DOCX is an OOXML ZIP container, so archive expansion and XML declarations are validated before high-level parsing.

## Runtime validation

A permanent `Container Runtime Security Smoke` workflow builds and starts both images rather than stopping at image creation. It verifies that:

- the backend and frontend processes run with non-zero user IDs
- the backend answers `/health` with the required API security/cache headers
- the frontend starts successfully on its unprivileged port
- the frontend root receives CSP, HSTS, frame, MIME-sniffing, and no-store controls
- the generated CSP contains the runtime-configured API origin
- `config.js` exposes the matching runtime API URL
- backend access logging does not emit formatter errors after real HTTP requests

A separate `Production Security Surface` workflow runs after merges to `main`, waits until both Railway services report the exact merge revision, and then performs bounded production checks for private-route authentication, disabled API documentation, CORS behavior, security headers, CSP isolation, and API cache protection.

## Residual limitation

Rate limiting is still process-local. This work materially reduces single-instance and obvious abuse but does not claim a globally distributed quota. A shared store or platform edge policy can be added later if traffic volume requires it. The live PostgreSQL restricted-role/RLS credential cutover is also tracked separately in Milestone 8.2C and is not implied by this workstream.
