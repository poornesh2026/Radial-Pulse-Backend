# Decisions — made, and still needing approval

## Made (non-negotiable inputs)

Nx · pnpm · React + TypeScript (web) · React Native + TypeScript with Expo (mobile) ·
Python + FastAPI · PostgreSQL / Aurora PostgreSQL · SQLAlchemy 2 · Alembic · Pydantic ·
pytest · AWS · Terraform · GitHub Actions · Docker · Cognito + Google + PKCE + API Gateway JWT.

## Made during scaffolding (reversible, explained)

| Decision                                                                                             | Why                                                                              |
| ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Vite for the web app                                                                                 | Fast, standard for React SPAs; no SSR needed for an authenticated dashboard      |
| React Router 7, TanStack Query                                                                       | Mainstream, typed; keeps server state out of components                          |
| `openapi-typescript` + `openapi-fetch` for the client                                                | Backend stays the source of truth; types regenerate from OpenAPI                 |
| uv for Python                                                                                        | Fast, lockfile-based, works on Windows/macOS/Linux                               |
| Sync SQLAlchemy + psycopg 3                                                                          | Simpler than async; FastAPI runs sync routes in a thread pool; revisit if needed |
| Enums stored as VARCHAR + CHECK                                                                      | Adding a value never needs `ALTER TYPE`                                          |
| Lefthook for git hooks                                                                               | Single binary via npm, cross-platform, fast, parallel                            |
| ECS Fargate + internal ALB behind API Gateway (VPC link)                                             | Long-running FastAPI with a DB pool; no servers to patch                         |
| Aurora Serverless v2, scale-to-zero in DEV                                                           | Lowest cost for a small dev load                                                 |
| S3 + CloudFront for the web app                                                                      | Needed to host the SPA; cheapest managed option                                  |
| Single NAT in DEV, one per AZ in PROD                                                                | Cost vs. resilience                                                              |
| Region `ap-south-1` (Mumbai)                                                                         | India-only target market                                                         |
| Invite-only users, linked on first sign-in by verified email                                         | Outbound sales model: nobody self-registers                                      |
| 404 (not 403) when a user has no access to a clinic                                                  | Do not reveal which clinics exist                                                |
| Role names: Platform Administrator / Digital Success Manager / Clinic Administrator (review 2026-09) | Business terminology; migrated with a data mapping (0002), not a rename          |
| PostgreSQL row-level security + non-owner `radial_app` role                                          | Second isolation net under the application gate (0004)                           |
| IAM DB auth for api/worker; master secret only in migrate                                            | No long-lived DB password in running services                                    |
| One SQS queue + DLQ + one worker service                                                             | Enough for assessments; add job types, not queues                                |
| One unified Digital Presence Assessment (6 fixed sections)                                           | Product decision; engines are domain-owned plugins                               |
| One generic `presence_profiles` table with a `platform` column                                       | No per-platform tables                                                           |

## Milestone 1 product decisions (26 Sep 2026)

Full detail: [database-schema.md](database-schema.md), section 0.

| # | Decision |
|---|---|
| D1 | **5 clinic stages**: prospective_client → profile_enriched → assessment_completed → client_discussion → active_client. Leads are given to us. A clinic that says no is **archived** with a required reason (no extra stage). |
| D2 | **Exactly one active DSM per clinic** (database rule). "Update Assignment" swaps them; old rows are kept as history. |
| D3 | "Client Organization" = the business (`organizations`) that owns one or more clinics. |
| D4 | Doctor → **Practitioner** everywhere (table, API, permissions). `clinic_id` is not renamed. |
| D5 | Admin tabs: Prospects = stages 1–2 · In Progress = 3–4 · Active = 5 · archived hidden behind a filter. |
| D6 | Stage moves are **manual** (Admin or the clinic's DSM) in Milestone 1. |
| D7 | A clinic can become **Customer** only with at least one active Clinic Administrator. |
| D8 | Improvement Opportunity = an **assessment finding**. D9: its work status lives on the **work item** (one open item per finding code). |
| D10 | No hard deletes: deactivate / archive. |
| D12 | Login: **Google only** in Milestone 1 (the architecture document's "email-based" option is not built). |
| D13 | **Invite emails** are sent automatically (backend `log` until SES is configured by Person 3). |
| D14 | A Clinic Administrator may add **other Clinic Administrators** to their own clinic. A Customer clinic cannot lose its last one. |
| D15 | The clinic's **DSM alone** reviews and publishes an assessment. Clinic users can never approve, reject or retract an assessment. |

## Need team / mentor approval

1. **Assessment scoring** — today the overall score is an equal-weight mean of completed
   sections (`methodology_version 2026.09-v0`). The product owner must approve weights,
   section list and what a "partial" assessment shows to clinics.
2. **Role → permission table** (`app/core/rbac.py`, [multi-tenancy.md](multi-tenancy.md)).
   Open points: may a Clinic Administrator add other Clinic Administrators (`team:manage`,
   today: no — staff only)? May a Digital Success Manager read the user list (today: no)?
   May a Digital Success Manager create clinics (today: yes, and is auto-assigned)?
3. **Clinic Team Member** — DECIDED (Sep 2026): view-only in their own clinic plus uploading
   photos/files; granted by the Admin, the clinic's DSM or a Clinic Administrator.
4. **Four-eyes rule** — should the person who submits an assessment be blocked from approving it?
5. **One practitioner, many clinics** — DECIDED (Sep 2026): a doctor belongs to the business
   (`practitioners.organization_id`) and is linked to each branch through `clinic_practitioners`.
   Only branches of the same business can share a doctor (migration 0008).
6. **Separate AWS accounts for DEV and PROD** (recommended; Terraform supports both).
7. **HTTP service-to-service auth** for other teams' agents/connectors (Cognito client
   credentials → `ServicePrincipal`). The worker already uses the in-process version.
8. **Engine packaging and deployment** — how domain teams ship engines (same image via
   entry points today; a separate crawler image with Playwright if needed).
9. **Scheduled re-assessments** (every 1–2 weeks?) — EventBridge Scheduler → job. Needs a product decision.
10. **RLS on identity tables** — DONE (Sep 2026, migration 0007): every table is under RLS.
11. **Cognito pre-sign-up trigger** to reject Google accounts that were not invited
    (today they are rejected by the API instead).
12. **Production image promotion** — PROD currently rebuilds from the released commit.
    Promote the exact DEV image digest instead (needs cross-account ECR access).
13. **Custom domains** (app/api/auth) and ACM certificates.
14. **Chat** — design agreed (PostgreSQL history, S3 attachments, WebSockets only for
    delivery); build timing and whether messages may contain health information are open.
15. **Health information** — if patient data is ever stored, a formal compliance assessment
    is required first (no HIPAA or similar claim is made).
16. **Nx Cloud / remote cache** — off (`NX_NO_CLOUD`). Enable if CI gets slow.
17. **Internal ALB hop is plain HTTP inside the VPC** (TLS ends at API Gateway). Acceptable
    for now; end-to-end TLS needs a private certificate.
18. **Worker autoscaling** on queue depth — not needed at one task; revisit with real load.
19. **Archive retention** — old `metric_snapshots` (>180 days) and `audit_events` (>365 days) move
    to an S3 archive monthly (built). Open: how long the archive is kept (suggested 7 years) and
    whether audit files use S3 Object Lock. Needs a business/legal decision before PROD.
