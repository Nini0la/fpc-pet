# Security and privacy

- Identity is derived only from an opaque random HttpOnly session cookie. Clients never send authoritative user IDs. Production always resolves the account to the fixed `owner`; the username selector exists only in development/test so isolation can be exercised. Session and CSRF values are stored hashed; cookies are SameSite=Strict and Secure in production.
- Login compares an environment access code in constant time. Mutations require an exact allowlisted Origin plus double-submit CSRF token. CORS uses exact configured origins, never `*` with credentials.
- Production startup fails closed when required secrets/configuration are absent. Access codes, auth headers, raw prompts, chain-of-thought, and secrets are excluded from events and logs.
- API text and identifier lengths are bounded. SQLAlchemy parameterizes queries. Errors are generic. React renders message content as escaped text (no `dangerouslySetInnerHTML`). Foreign-user IDs return the same 404 as absent IDs when requests are valid.
- Corrections increment versions and add content-free metadata-only provenance; old text is not copied to the audit row. Deletion tombstones and overwrites primary user content, filters it from lists/recall, and prevents later recall. Database backups may retain deleted data until operators rotate them.
- Retention is operator-controlled and indefinite by default for active records and provenance. Sessions expire after seven days. A production deployment must define backup retention and erasure procedures before handling sensitive data.
- This project is an original narrow continuity prototype. It does not expose, implement, or claim knowledge of proprietary FPC internals.

Known M1 limits: one shared environment access code, no rate limiter, no key rotation UI, literal SQL recall, no field encryption, and no external model provider. Put it behind TLS and a trusted reverse proxy.
