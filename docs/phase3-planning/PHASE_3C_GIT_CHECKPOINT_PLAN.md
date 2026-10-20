# Proposed Phase 3B/3C reproducibility checkpoint

20 October 2026. Proposal only: **no branch creation, staging, commit, push or deployment performed**. Existing dirty work belongs to the user. HEAD at start82a32a1410ebbc13207b39f1325f8ddff4d64301 on main; index empty.

## Source capture and scope

PHASE_3C_REPRODUCIBILITY_MANIFEST.json inventories every tracked/nonignored regular source/document file except itself, with exact relative path, byte size and SHA-256, plus Git tracked/modified/untracked status. It records baseline HEAD and dependency lock identities. Ignored client originals are verified separately against CLIENT_SOURCE_MANIFEST.json; their hashes are evidence, not an instruction to stage originals. Environment secrets, .local databases/logs/probes, .venv, node_modules, dist/build output and caches are excluded by existing ignore rules. The snapshot is exact file evidence, not a promise of bit-identical Python/Node/native build artifacts.

The manifest intentionally excludes its own file to avoid a circular hash. Historical report source hashes describe this working-tree snapshot, not release approval. A later authorized commit changes HEAD/Git status but does not invalidate unchanged source bytes; verify the file SHA-256 values independently of that metadata.

## Proposed checkpoint sequence (requires explicit authorization)

1. Freeze/review the captured source. Confirm no concurrent edits, compare every manifest hash, inspect all tracked diffs AND untracked files. Review ownership of pre-existing Phase3B/3C work; do not overwrite or silently claim it as new remediation. Resolve discrepancies before any staging.
2. Review one coherent checkpoint containing the pending3B engine,3C workflow and remediation dependency closure. A commit containing only new3C files would omit required untracked ledger models/services/migrations/tests. Models.py currently imports both domains, so splitting requires carefully reviewed commits/hunks rather than blindly staging directory subsets. Prefer a single reproducible checkpoint for this existing accumulated work; splitting is a separate authorized task.
3. After permission, optionally create an isolated codex/phase3c-1-remediation-checkpoint branch from the verified HEAD. Prepare an explicit path allowlist using the manifest working_tree_changes list and its untracked_domain_files list. Include required source/tests/migrations/frontend/affected docs and both source-capture documents. Do not use broad git add . or stage ignored artifacts/client originals/secrets. No real scope/permission/data fixture may be included as a deployment seed.
4. Review staged content against the manifest and inspect staged diff. Validate requirements/lock.txt and package-lock.json are present, source guard/base settings remain disabled, migration dependencies are complete, and no operational enabled route/grant/import exists. Expected baseline15 pending migrations plus new0010/0011 means17 pending in the unchanged configured application DB. Do not migrate it as part of a source checkpoint.
5. Use the report's fresh disposable PostgreSQL/full boundary tests and frontend checks as evidence for the exact snapshot; rerun if source changes. Verify the source manifest again after any fixes. A clean disposable installation is not populated-database upgrade acceptance or deployment-runtime certification.
6. Obtain explicit commit authorization for the reviewed staged result before committing. Check resulting commit/tree contains all intended paths and dependency closure; verify manifest hashes from a separate clean checkout with independently installed locked dependencies and a disposable PostgreSQL environment. No forced history changes, no unrelated source removal. This task has not performed these actions.
7. Push and deployment require separate explicit authorization. A Git checkpoint neither approves business policies nor enables live posting. Production rollout remains blocked by governed scopes/authority, source registration/adoption, QC/openings/period rules, populated upgrade/browser/runtime security and documented SOP cutover.

## Untracked source and release gates

The exact current list is generated under untracked_domain_files in PHASE_3C_REPRODUCIBILITY_MANIFEST.json; all other untracked documents are listed in working_tree_changes. Do not assume an untracked file is disposable or safe to omit. Existing Phase3B ledger services/models/guards/test-runner/base settings remain unchanged by this remediation; hashes are checked against the task-start manifest.

Remaining actual decisions: canonical upstream document issuer/namespace and occurrence/line identifiers; trusted registration/correction/cancellation publisher; how rejected source claims may be reissued with independent history; production evidence permissions/retention; warehouse-scope lifecycle and named authority; historical reconciliation/freeze/period policy. The current registry is immutable fixture data inside stamped tests only, no publisher API or live provisioning workaround.

Recommendation: once the recorded synthetic checks pass, CONDITIONAL GO to scope a separately authorized synthetic-only Phase3D foundation. Do not start Phase3D here, invent real QC tolerances/frequencies, or relax existing fail-closed controls. Live use remains NO-GO.
