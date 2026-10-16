# Navapack ERP Agent Instructions

Applies within frontend/. Repository-wide guidance is in ../AGENTS.md.

## Before modifying code

- Read README.md and relevant docs; inspect actual source before making claims.
- Reuse existing components, Context stores and calculation helpers.
- Avoid unnecessary dependencies and unrelated page redesigns.
- After meaningful code changes run typecheck and build; run relevant data checks. No lint command currently exists.
- Run frontend commands from this directory. The Git root is now the parent directory.

## Current development phase

Frontend workflow implementation and validation. Unless explicitly requested, do not create backend APIs, migrations, hypothetical database schemas or fake endpoints. Keep frontend boundaries suitable for later API integration.
Existing API calls are client expectations; mock fallback or local success is not proof of persistence.

## Terminology and inventory

- Stock = Finished Goods; /stock Stock IN/OUT affects finished-goods movements.
- Raw Material = production inputs; /raw-materials Stock IN/OUT affects raw-material movements.
- Raw Material categories: Virgin Material, Recycled Granules, Ink.
- Sales Order creation creates demand only; it must not deduct physical stock.
- Current demand comparison neither reserves nor deducts inventory. Verify the confirmed production/issue/dispatch workflow before changing this.
- Preserve unknown opening balances, variant identity and units; never silently merge variants or sum incompatible units.

## Client data

Treat supplied Excel files as business/data references. Preserve actual product/material names and specific grades; do not invent replacements or blindly reproduce sheets.
Keep datasets in data files; document interpretation without unnecessary client-sensitive details.
See docs/finished-goods-reference.md before changing imported finished-goods data.

## Documentation maintenance

Implement and verify first, then update only affected Markdown.
Keep docs/DEVELOPMENT_STATUS.md accurate; update BACKEND_TODO.md when integration work changes, DATA_MODELS.md for model changes and BUSINESS_RULES.md for behavior changes.
Add concise CHANGELOG.md entries for significant user-facing changes; include docs in the feature commit where practical.
Do not rewrite every document or change docs merely to generate activity.
