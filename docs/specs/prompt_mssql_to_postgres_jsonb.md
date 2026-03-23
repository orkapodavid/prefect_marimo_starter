# prompt.md — Ask an LLM agent to build a Microsoft SQL Server → PostgreSQL JSONB migration

Please implement a **generic first-pass data migration** from **Microsoft SQL Server** to **PostgreSQL** for a single table.

## Goal
Move data from one SQL Server table into one PostgreSQL table.

The design should be intentionally simple:
- Keep only metadata fields as top-level PostgreSQL columns.
- Store most other source columns inside a single `jsonb` column called `payload`.
- This is only the first migration pass. We can normalize or refine later.

## Important schema rule
Keep these fields outside the JSONB payload when they exist:
- source primary key or identifier
- created at
- updated at
- created by
- updated by
- optional row index / deterministic extraction order

Put almost everything else into `payload jsonb`.

## What I want you to build
Please produce:
1. PostgreSQL target table DDL
2. required indexes
3. SQL Server source-introspection SQL
4. Python migration script
5. config-driven column mapping
6. batch extraction + batch loading
7. simple validation checks
8. README with setup and usage

## Technical expectations
- Inspect the SQL Server source schema before finalizing mappings.
- Prefer system-catalog/schema introspection over hardcoding everything.
- Use a PostgreSQL target table with:
  - surrogate `id`
  - `source_table`
  - `source_pk`
  - `source_row_index` if useful
  - `created_at`
  - `updated_at`
  - `created_by`
  - `updated_by`
  - `payload jsonb`
  - `migration_batch_id`
  - `migrated_at`
- Use minimal but practical indexes, including a GIN index on `payload`.
- Read and write in batches.
- Make the migration rerunnable.

## Mapping rules
- Explicit metadata mappings should be configurable.
- Unmapped business columns should go into `payload`.
- Exclude clearly technical columns by default when appropriate, such as `rowversion`, SQL Server `timestamp`, or computed columns, unless explicitly requested.
- Preserve null values.
- Prefer safe serialization over perfect type fidelity.

## Type handling guidance
- numbers → JSON numbers where safe
- booleans → JSON booleans
- text → JSON strings
- GUIDs → strings
- date/time values → top-level timestamps for mapped metadata fields, otherwise safe ISO-like strings in JSON
- binary/blob fields → exclude by default unless explicitly requested
- XML → string unless transformed intentionally

## Idempotency
Support one explicit strategy:
- truncate and reload, or
- delete scope and reload, or
- upsert by source key if one exists

Document which strategy you chose and why.

## Validation
Include at least:
- source row count
- target row count
- non-null payload check
- spot-check examples
- behavior on rerun

## Constraints
- Keep phase 1 boring and maintainable.
- Do not over-normalize.
- Do not build CDC.
- Do not over-optimize prematurely.
- Focus on correctness, simplicity, and debuggability.

## Deliverable style
Please return:
- complete code
- DDL
- config examples
- command examples
- a short explanation of design decisions
- a list of phase-2 improvements that are intentionally deferred
