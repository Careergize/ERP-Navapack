# API conventions

Base `/api/v1/`, trailing slashes, JSON snake_case, active bearer JWT. Only health,
readiness, login and refresh are public. No compatibility aliases or domain routes exist.

Application entities use UUID identifiers and UTC server timestamps. Django permission
and Simple JWT internal tables retain upstream identifiers. Future quantities/money use
Decimal serialized as strings; precision/unit/currency choices require separate approval.
No quantity or money schema has been guessed in Phase 1.

StandardPagination supports page/page_size (25 default, 100 maximum) and returns
count/next/previous/results. Filtering uses DjangoFilterBackend and explicit per-view
filtersets, search_fields and ordering_fields. Future resource views must specify stable
ordering `-created_at,id`. Do not expose arbitrary ORM fields. These are configured
infrastructure; there are no resource list endpoints yet.

Every response carries X-Request-ID. Clients may send a valid UUID X-Request-ID;
invalid values are replaced. Error shape:

```json
{"error":{"code":"validation_error","message":"Invalid input.","fields":{"email":["Enter a valid email address."]},"details":{},"request_id":"uuid"}}
```

Validation errors use 400; absent/invalid credentials 401; denied permissions 403;
missing routes/resources 404; method mismatch 405; idempotency conflict 409;
stale resource version 412; missing precondition 428; throttle 429 with Retry-After;
unready 503; unexpected API failure 500 with internal_error and no implementation detail.
Error codes include invalid_credentials, token_not_valid, permission_denied,
token_owner_mismatch, self_approval_forbidden, independence_required,
idempotency_conflict, version_conflict and version_required. The envelope preserves
nested DRF field errors without exposing exception traces.

Applicable future mutations require `If-Match: "7"`. Missing is 428; malformed, weak,
wildcard, zero and unquoted values are 400; stale is 412. Responses should emit an
ETag for the current version from the domain adapter (no versioned domain endpoint
exists in this phase). Idempotency-Key accepts up to 200 printable ASCII characters
without spaces, scoped by server-resolved scope/action/actor. UUID keys are recommended.
Adapters must include resource IDs and preconditions in the canonical hashed payload.

Authentication endpoints do not use command idempotency or If-Match: refresh rotation
and revocation are serialized on the outstanding-token row. Login is limited to five
requests per minute per REMOTE_ADDR; refresh to thirty, shared through PostgreSQL fixed
windows. These limits complement ingress abuse controls and are not a DDoS defense.
