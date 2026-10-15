# Frontend authentication adapter proposal — not implemented

Inspected ../frontend/src/context/AuthContext.tsx and ../frontend/src/lib/api.ts.
Current login sends username (email value), expects a single optional role, defaults
to receptionist, stores tokens in localStorage, and holds identity only in memory.
There is no me restoration or refresh flow. Logout is local only. The 401 interceptor
clears only the legacy token. Providers retain domain state across identity changes.
Demo role login is separately gated and must remain available for current demo workflows.

A separately approved, authentication-only adapter could:

1. Select a dedicated auth base `/api/v1/`; changing the shared API base alone would
   also redirect existing job/recycling/costing/trace consumers to unimplemented resources.
2. Send `{email,password}` instead of `{username,password}` and require a complete
   server user response. Remove the fallback role. Map server capabilities and any
   approved multi-role selection explicitly; current frontend User assumes a single role.
3. Restore identity from me on load, serialize refresh requests, retain every rotated
   refresh, retry a failed request once, and clear all tokens/identity on terminal failure.
4. Revoke the active refresh with backend logout before local cleanup, handling offline
   failure explicitly. Clear/refetch company/user-scoped stores on identity changes.
5. Render structured error fields/code/request_id; do not silently fallback to demo
   after a real authentication or API failure. Preserve explicit demo entry separately.

Choose browser token storage first: current localStorage is exposed to script execution.
The implemented API uses bearer tokens and JSON refresh, with no credentialed CORS or
cookie session flow. Moving refresh to HttpOnly cookies requires a separate backend
contract, CSRF controls and frontend changes. No storage choice was silently implemented.

Later adapters must handle paginated responses, snake_case, Decimal strings, UUID source
mapping, version preconditions and idempotency keys. No sales, job, QC or inventory
behavior should be connected until its persistent endpoint and authorization are complete.
