# Security dependency audit exceptions

MarketLens dependency scanners fail on every published advisory except the explicitly reviewed, time-bounded exceptions below. An exception is not a statement that the dependency is vulnerability-free; it records why the affected code path is not currently exposed and when the decision must be revisited.

## Clerk-transitive `cryptography` advisories

| Field | Value |
| --- | --- |
| Package | `cryptography==48.0.1` |
| Dependency owner | `clerk-backend-api==6.0.1` |
| Constraint | Clerk currently requires `cryptography>=45.0.0,<49.0.0` |
| Review deadline | 2026-09-30 or Milestone 8.2B completion, whichever comes first |
| Required action | Upgrade the Clerk dependency chain or replace the SDK verification path, then remove all exceptions |

### `PYSEC-2026-3552` / `CVE-2026-69247`

The advisory affects PKCS#7 envelope decryption APIs. MarketLens does not decrypt PKCS#7, S/MIME, or attacker-supplied encrypted envelopes. The installed package is transitive through Clerk authentication.

### `PYSEC-2026-3553` / `CVE-2026-69249`

The advisory affects certificate-chain construction with attacker-controlled duplicate self-signed certificates. MarketLens application code does not invoke `cryptography` certificate-chain construction. Clerk token verification is performed through the Clerk SDK and does not accept user-supplied certificate chains through a MarketLens endpoint.

### `PYSEC-2026-3554` / `CVE-2026-69248`

The advisory affects name-constraint validation involving wildcard certificate names. MarketLens application code does not invoke the affected verifier or accept user-supplied certificate chains.

## Enforcement

The CI workflow ignores only the three exact `PYSEC` identifiers above while continuing to scan both runtime and development requirements. Any additional advisory remains blocking. The exceptions must be removed immediately if MarketLens begins using an affected API, if Clerk releases a compatible fixed dependency chain, or when the review deadline is reached.
