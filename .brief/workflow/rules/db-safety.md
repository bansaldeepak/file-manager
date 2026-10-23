---
paths:
  - "**/migrations/**"
  - "**/migration/**"
  - "**/prisma/schema.prisma"
  - "**/prisma/**/*.sql"
  - "**/drizzle/**"
  - "**/alembic/**"
  - "**/*.sql"
  - "**/db/seed*"
  - "**/schema.rb"
---

# Database Safety — Non-Negotiable

Data is sacred. Losing data — even local test data — is unacceptable. These rules apply to ALL
environments (local, dev, staging, prod) and to every tool (`prisma`, `drizzle`, `alembic`, `goose`,
`wrangler d1`, raw SQL).

## Hard Stop — Before Running Anything, Not Just Destructive Statements

**Running the migration tool is itself the risky action** — a migration file can contain a `DROP`,
`TRUNCATE`, or a data-losing column change without that being obvious from the command name alone.
Treat "run the migration" and "run a destructive command" as the same category of risk.

Before running **any** migration command, applying a schema change, or executing raw SQL/ORM calls
that delete, drop, truncate, or overwrite rows:

1. **Read the migration/statement first** — never run one blind, including ones you just generated
2. **State exactly what it will do** and name what data could be lost, even if you expect "none"
3. **Wait for explicit user approval, every time** — approval to write the schema change is not
   approval to run it; approval for yesterday's migration is not approval for today's
4. If approved and data matters: **back it up first** (`SELECT * FROM table` → dump, or copy the
   SQLite/DB file)

This applies to local and test databases too — test data takes time to create and represents real
effort. "It's just my local DB" is not an exemption.

## Never Drop or Delete Tables

- **Never run `DROP TABLE`** — not even locally. Confirm first and explain the data-loss implications,
  even if the user asked for it.
- **Never run `TRUNCATE TABLE`** or `DELETE FROM table` without a `WHERE` clause.
- **Always prefer non-destructive alternatives**: `ALTER TABLE ADD COLUMN`, `ALTER TABLE RENAME
  COLUMN`, `CREATE TABLE IF NOT EXISTS`.
- If a table genuinely needs recreation (e.g., a column rename SQLite can't do in place): create the
  new table, copy the data across, verify the copy, only then drop the old one and rename.

## Migration Safety

- **Use the project's migration tooling** — never hand-run raw SQL files. Use framework commands that
  track applied state (`wrangler d1 migrations apply`, `prisma migrate deploy`, `alembic upgrade
  head`, `goose up`).
- **Never modify a migration already applied to any remote environment** — write a new one instead.
- **Never hand-write migrations the framework generates** — use `prisma migrate dev`/`diff` or the
  equivalent generator; hand-write only when the generator can't express the operation.
- **Column renames in SQLite** — use `ALTER TABLE ... RENAME COLUMN` (SQLite 3.25+/D1). Never
  drop-and-recreate for a rename.
- **Column type changes** — add the new column, backfill, drop the old one in a later migration after
  verification — never in one step.
- **Test migrations against a copy of the DB**, never against the primary database without a backup.
- **No idempotent hacks** — don't paper over re-running migrations with `IF NOT EXISTS` / `|| echo`.
  If the tool tracks applied state correctly, each migration runs exactly once; if it doesn't run
  cleanly, that's a signal to fix, not suppress.

## Recovery-First Mindset

- Schema conflict → **migrate the data, don't destroy it**
- Test failure → **fix the test or code, don't reset the DB**
- Suspected corruption → **copy the DB file first**, then attempt repair
