# Monorepo migration and deployment

## Layout and history

The existing Git metadata was moved from frontend/.git to .git at the workspace root.
No repository was initialized and no commit history was rewritten. The existing origin
remains https://github.com/Careergize/ERP-Navapack.git. The migration branch is
codex/monorepo, based on 5aa0687d969db58741f5a60e36e8c4d851bff418.

The frontend stays in frontend/; the completed Phase 1 backend stays in backend/ and
is included in the same index. The ordinary migration commit records the relocation
and backend addition. Older commits still have src/, package.json and docs/ at their
historical root. Use `git log --follow -- frontend/src/App.tsx` to inspect file lineage
across the move. The pre-migration main and origin/main refs remain at their original tip.

Before the move, a complete `git bundle create ... --all` backup was created and
verified under ignored .migration-backup/. It includes private local Codex checkpoint
refs as well as branch refs; keep the backup local. Do not push `--mirror` or `--all`.
The backup is not another initialized repository. Existing metadata/configuration,
local refs and reflogs were retained by the directory move.

Environment files, virtual environments, PostgreSQL data, npm dependencies, build
outputs and logs remain on disk and ignored. The unused empty root package-lock.json
also remains on disk but is removed from the index; frontend/package-lock.json remains
tracked and authoritative. No source or local data is deleted by the migration.

## Independent application commands

Frontend: working directory frontend, `npm ci`, `npm run build` (output dist),
`node ./node_modules/typescript/bin/tsc --noEmit`, and relevant scripts/check-*.mjs.
Its package.json/lockfile, Vite configuration, environment and SPA rewrites stay together.

Backend: working directory backend, its own .venv and requirements/lock.txt, PostgreSQL,
`python manage.py check`, `python manage.py makemigrations --check --dry-run`, and
`python manage.py test tests --settings=config.settings.test --noinput`.
Runtime deployment uses backend/config WSGI or ASGI settings as documented in its README.
No combined build, backend hosting on Vercel or frontend authentication adapter is added.

## Vercel cutover (requires deployment coordination)

Local configuration inspected: frontend/vercel.json rewrites all paths to /index.html;
frontend/package.json builds TypeScript then Vite; Vite emits dist with relative assets.
The live Vercel dashboard has not been inspected or modified.

For the existing frontend project when the deployed branch contains the new layout:

1. Retain its GitHub repository connection, domains and existing production branch.
2. Set project **Root Directory** to `frontend`.
3. Use Vite framework preset, install `npm ci`, build `npm run build`, output `dist`.
   Paths and commands are relative to Root Directory; do not add another `cd frontend`.
4. Keep frontend/vercel.json in place; no root copy is needed.
5. Preserve Preview/Production environment scopes and existing VITE variables.
   Do not introduce an API URL change as part of the repository move.
6. Check any dashboard build overrides, ignored-build commands and path filters for
   old root assumptions. Shared files outside frontend are not required by this app.
7. Validate a deployment of the migration branch before production cutover, then verify
   a deep-link reload (for example /sales-orders), static assets and explicit demo login.

Reference: [Vercel monorepos](https://vercel.com/docs/monorepos).

Root Directory is a project setting: changing it while the deployed branch still has
the old root layout can break later builds. Use an isolated preview project with Root
Directory frontend to validate the migration branch if needed, leaving the existing
production project unchanged until the layout and settings can be coordinated. Creating
that preview project is a separate deployment action, not part of this local migration.
The current deployed artifact remains available while local work is reviewed.

The existing SPA catch-all is not an API proxy. The frontend production API default is
/api; serving Django at the same origin would require a separately approved route/proxy
contract placed before SPA fallback. Backend Phase 1 has /api/v1 auth and health routes
only. Do not silently redirect existing domain consumers to unimplemented backend routes.

## Review and publication boundary

Review `git diff --cached --name-status -M`, `git diff --cached --check`, staged file
names and application checks before committing. Verify the original frontend tip is
an ancestor with `git merge-base --is-ancestor 5aa0687 HEAD`.

The migration is local. No push, force-push, remote branch deletion, main-branch move or
Vercel/dashboard update is performed. Publish the migration branch and merge only after
explicit authorization and deployment cutover coordination. Reverting to an older Git
layout later also requires restoring matching Vercel settings; do not reset or force-push.

## Local verification completed

- Verified the pre-migration history bundle and unchanged origin URL.
- Checked all 146 original frontend tracked files against their new indexed paths;
  only the documented README/agent/architecture/status/changelog edits differ.
- Verified application files remain on disk and non-document source is unchanged.
  Both existing .env files were checked by hash without exposing their values.
- Included 51 backend files and excluded environment files, virtual environments,
  PostgreSQL data, dependencies, build output, logs and the history backup from the index.
- Frontend TypeScript noEmit check and Vite production build passed. Output was written
  to ignored backend/.local/frontend-monorepo-build, preserving the previous dist.
  Existing large-chunk warning remains. All nine frontend regression scripts passed.
- Backend system check and migration drift check passed. All 35 tests passed on the
  existing disposable PostgreSQL cluster, including concurrent-command/refresh tests.
  Django destroyed its test database; the local cluster was stopped after verification.
- Staged whitespace and local documentation-link checks passed.

No production deployment or browser acceptance test was performed during this migration.
