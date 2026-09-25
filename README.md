# services/api — Radial Pulse platform API

Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · Pydantic 2 · PostgreSQL (Aurora in AWS).
Owner: **Person 1**. Nx project name: `api` (tags `type:service`, `scope:api`).

## Layers (one direction only)

```
routers  →  services  →  repositories  →  models
   ↑            ↑
schemas     core (config, security, rbac, errors, logging)
```

| Folder          | Job                                                                   | Must NOT                          |
| --------------- | --------------------------------------------------------------------- | --------------------------------- |
| `api/v1/routers`| HTTP: parse input, call one service function, shape the response      | query the DB, hold business rules |
| `schemas`       | Pydantic request/response models (the API contract)                   | import models' sessions           |
| `services`      | Business rules, audit events, commit                                  | import FastAPI                    |
| `repositories`  | All SQL. Clinic-scoped reads always take `clinic_id`                  | contain business rules            |
| `models`        | SQLAlchemy tables                                                     | contain request logic             |
| `dependencies`  | DB session, auth (`get_principal`), tenancy (`clinic_access`)         |                                   |
| `core`          | settings, JWT verification, RBAC, error types, logging                |                                   |
| `integrations`  | S3, Cognito userInfo (behind small Protocols)                         |                                   |
| `assessments`   | Engine contract (`engines.py`) + placeholder scoring                  | contain SEO/GBP/social logic      |
| `jobs`          | Job queue backends (SQS / database poll / in-memory) + message v1     | carry data or tokens in messages  |
| `worker`        | `python -m app.worker`: receive → claim → run handler → retry/fail    | import FastAPI or routers         |
| `db/tenant.py`  | Hands the allowed clinic ids to PostgreSQL row-level security         |                                   |
| `middleware`    | request id + access log, security headers                             |                                   |

## Tenant isolation — the one rule

Every route under `/clinics/{clinic_id}/…` depends on `clinic_access(Permission.X)`.
No access to the clinic → **404**. Access but missing permission → **403**.
Repositories filter every clinic-scoped query by `clinic_id`, so an id from another
clinic returns nothing. `tests/api/test_tenant_isolation.py` proves it for every
route — **add your new route to that file**.

PostgreSQL **row-level security** is the second net: the API and worker log in as members
of the non-owner `radial_app` role, and `clinic_access` narrows the transaction to the one
clinic. **A new table with `clinic_id` needs an RLS policy in its migration** (copy 0004);
`tests/integration/test_rls.py` fails otherwise.

## Commands (run from the repo root)

```bash
pnpm nx run api:install            # uv sync (creates .venv)
docker compose up -d postgres      # local PostgreSQL 16
pnpm nx run api:migrate            # alembic upgrade head
pnpm nx run api:dev                # http://localhost:8000/docs
pnpm nx run api:worker             # background worker (JOB_QUEUE_BACKEND=database locally)
pnpm nx run api:create-admin --email=you@example.com --name="You"   # first Platform Administrator
pnpm nx run api:test               # fast tests (SQLite)
pnpm nx run api:integration-test   # full suite on PostgreSQL (needs TEST_DATABASE_URL)
pnpm nx run api:lint               # ruff
pnpm nx run api:typecheck          # mypy --strict
pnpm nx run api:openapi            # writes packages/api-client/openapi/openapi.json
pnpm nx run api:migration --name="add consent source"   # new Alembic revision
```

## Migrations

1. Change models in `app/models/`.
2. `pnpm nx run api:migration --name="short description"` (autogenerate against a DB at head).
3. **Read the generated file.** Autogenerate misses things (data moves, triggers, renames).
4. `pnpm nx run api:integration-test` — `test_migrations_match_models` fails if models and migrations drift.
5. Migrations must be backwards-compatible with the previous app version (expand → migrate → contract),
   because the deploy runs migrations before the new containers start.
6. Migrations run as the database **owner** (`MIGRATION_DATABASE_URL`); the app runs as
   `radial_app` (`DATABASE_URL`). New clinic tables: add RLS. Changed stored values
   (roles, statuses): write a data mapping and a downgrade (see 0002).

## Auth in local development

There is **no auth bypass**. Point `COGNITO_*` at the DEV user pool and sign in through the
web app, or call `/health` and `/docs` without auth. Tests use real JWT verification
with a throwaway RSA key.
