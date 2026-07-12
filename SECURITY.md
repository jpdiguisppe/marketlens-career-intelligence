# Security Policy

MarketLens is currently a portfolio/demo application, not a production service for sensitive personal data.

## Supported Use

The live demo is intended for sample job postings and non-sensitive resume-style text only.

Do not upload:

- real Social Security numbers
- addresses or phone numbers
- private medical, financial, or legal information
- secrets, API keys, passwords, or database URLs
- confidential employer or customer data

## Current Security Controls

The backend includes:

- admin API key protection for write/delete endpoints
- CORS configuration for the deployed frontend origin
- request size limits on free-text fields
- CSV upload size and row-count limits
- basic public endpoint rate limiting for analysis endpoints
- SQLAlchemy ORM usage instead of raw string-built SQL queries

Admin-only endpoints require the `X-Admin-API-Key` header. The key should be stored only as a backend environment variable, such as Railway `ADMIN_API_KEY`.

## Known Limitations

Before this project should be treated as a real public beta, it still needs:

- real authentication and authorization
- per-user data ownership
- database migrations
- stronger distributed rate limiting
- structured security logging
- dependency vulnerability scanning
- accessibility audit fixes
- a privacy policy and terms if real users or resumes are collected

## Reporting a Vulnerability

Please open a private issue or contact the project owner directly. Do not publicly post secrets, database URLs, tokens, or exploit details.
