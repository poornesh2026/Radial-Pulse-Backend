# Contributing

Three developers, one monorepo, clear ownership. Read this once; keep
[AGENTS.md](AGENTS.md) handy — the rules there apply to humans too.

## Team ownership

| Person | Role                       | Owns                                                                                                              |
| ------ | -------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 1      | Backend / Database         | `services/api` — schema, migrations, API contracts, auth backend, RBAC, tenant isolation, business logic          |
| 2      | Frontend / Mobile          | `apps/web`, `apps/mobile`, `packages/ui`, `packages/design-tokens`, API integration, UX                           |
| 3      | AWS / DevOps / Integration | `infra/`, `.github/`, `scripts/`, Nx + pnpm config, hooks, Docker, environments, integration testing, agent rules |

Shared: `packages/shared-types` (1+2), `packages/config` (2+3), `docs/architecture` (all).
CODEOWNERS enforces reviews. Anyone may change anything — the owner reviews it.

Role words: always **Platform Administrator**, **Digital Success Manager**, **Clinic
Administrator** (and, later, **Clinic Team Member**). Do not say "internal manager",
"analyst", "clinic owner" or "client" for roles.

## Naming

| Thing                  | Convention                                   | Example                                               |
| ---------------------- | -------------------------------------------- | ----------------------------------------------------- |
| Nx projects / packages | kebab-case, `@radial-pulse/<name>`           | `@radial-pulse/design-tokens`                         |
| React components/pages | PascalCase file = component                  | `ClinicDetailsPage.tsx`                               |
| Hooks                  | `useThing`                                   | `useClinicsQuery`                                     |
| TS constants           | `PascalCase` object + type                   | `ApprovalState.SUBMITTED`                             |
| Python modules         | snake_case                                   | `work_items.py`                                       |
| DB tables              | plural snake_case                            | `clinic_memberships`                                  |
| API paths              | plural kebab-case nouns                      | `/clinics/{clinic_id}/work-items`                     |
| Permissions            | `resource:action`                            | `profile:write`                                       |
| Audit actions          | `resource.verb`                              | `asset.upload_confirmed`                              |
| Roles                  | code = snake_case; UI = `ROLE_LABELS`        | `digital_success_manager` → "Digital Success Manager" |
| Job types              | `resource.verb`                              | `assessment.run`                                      |
| Terraform              | snake_case resources, kebab names            | `aws_s3_bucket.assets` → `radial-pulse-dev-assets-…`  |
| Env vars               | UPPER*SNAKE; `VITE*`/`EXPO*PUBLIC*` = public | `COGNITO_USER_POOL_ID`                                |

## How work flows

1. Branch from `main` (`feature/…`, `fix/…`, `chore/…`, `infra/…`, `docs/…`).
2. Make the change **in the right project**. Add tests.
3. `pnpm nx affected -t lint typecheck test build`.
4. Open a PR; fill the checklist. CI runs affected checks, security scans, Terraform checks.
5. Owner reviews → squash-merge → DEV deploys automatically.

Details: [git workflow](docs/development/git-workflow.md) · [setup](docs/development/setup.md) ·
[testing](docs/development/testing.md) · [environments](docs/development/environment.md).

## Area guides

- **Backend** — `services/api/README.md`, `docs/api/README.md`. Migrations: model →
  `nx run api:migration` → review → `nx run api:integration-test`.
- **Frontend** — `apps/web/README.md`, `Design.md`. Data via `services/queries.ts`, auth via `useSession()`.
- **Mobile** — `apps/mobile/README.md`. Tokens from `design-tokens`, never `ui`.
- **Infrastructure** — `docs/infrastructure/README.md`. Plan in PR, apply DEV on merge, PROD with approval.

## Definition of done

- Tests for the new behaviour (and a tenant-isolation line for new clinic routes).
- Lint, typecheck, tests, build pass for affected projects.
- Contract regenerated if the API changed; migration added if models changed.
- Docs updated if you changed architecture, permissions, env vars or workflows.
- No secrets, no fake data, no TODOs without an owner.
