# API contract changelog

What changed **for the screens** in each contract version. The full contract is
`openapi/openapi.json` (also attached to each GitHub Release). Version rules:
[docs/api/contract-versioning.md](../docs/api/contract-versioning.md).

## v0.1.1 — 2026-09-27

Additions only (nothing removed or renamed). Asked for by the frontend team.

- **Approvals:** every approval now carries `available_actions`: the actions the **caller** may take
  right now (state, permissions, staff-only assessments and "already published" all applied).
  Show buttons from it; do not repeat the rules in the app.
- **Clinic stage groups:** `GET /clinics?group=prospects|in_progress|active` filters by Admin tab
  (D5: Prospects = stages 1-2, In Progress = 3-4, Active = 5), and every clinic has `stage_group`.
  The tile counts are unchanged in `GET /dashboard/summary`.
- **`GET /assessments`** (new): the Audit Reports list across every clinic the caller may see, each
  row with `clinic_name` and `primary_practitioner_name`. Filters: `status`, `publication_state`,
  `clinic_id`. Same scope as `GET /clinics`; clinic users see PUBLISHED assessments only.
- **`GET /work-items`** (new): the work queue across clinics, each row with `clinic_name`.
  Filters: `status`, `owner_user_id`, `area`, `clinic_id`. Same scope as `GET /clinics`.
- Local CORS defaults now include `http://localhost:4200`.

## v0.1.0 — 2026-09-27

First versioned contract. Base path `/api/v1`, Bearer token from Cognito, errors are
problem+json (404 = no access to that clinic, 403 = not allowed, 409 = wrong state,
422 = invalid input, 502 = another platform refused, 503 = not set up yet).

**69 routes**, by screen area:

| Area | Routes |
|---|---|
| Me | `GET/PATCH /auth/me` (now with `avatar_url`, `sign_in_method`, `last_login_at`) |
| Settings → My Profile photo | `POST /auth/me/avatar/uploads` · `POST /auth/me/avatar/confirm` · `DELETE /auth/me/avatar` |
| Settings → Notifications | `GET/PUT /auth/me/notification-settings` |
| Settings → General / Integrations (Admin) | `GET/PATCH /settings/platform` · `GET /settings/integrations` |
| Dashboard | `GET /dashboard/summary` |
| Users (Admin) | `GET/POST /users` · `PATCH /users/{id}` · `POST /users/{id}/resend-invite` |
| Clinics | `GET/POST /clinics` · `GET/PATCH /clinics/{id}` · stage, stage history, archive/restore |
| DSM of a clinic (Admin) | `PUT/DELETE /clinics/{id}/assignment` · `GET /clinics/{id}/assignments` |
| Clinic team | `GET/POST /clinics/{id}/team` · `PATCH …/team/{id}` · `…/resend-invite` |
| Practitioners | `GET/POST /clinics/{id}/practitioners` · `PATCH …/{id}` (link a doctor of the same business with `practitioner_id`) |
| Clinic profile | `GET/PUT /clinics/{id}/profile` |
| Online presence | `GET/POST /clinics/{id}/presence-profiles` · `PATCH …/{id}` |
| **Connected accounts (new)** | `GET /clinics/{id}/connections` · `GET …/{platform}` · `POST …/{platform}/start` · `POST …/{platform}/complete` · `POST …/{platform}/disconnect` |
| Numbers (Social Media, charts) | `GET/POST /clinics/{id}/snapshots` (`value_number`; new `latest=true`) |
| Assessments | `GET/POST /clinics/{id}/assessments` · `GET …/{id}` |
| Review & publish | `GET /clinics/{id}/approvals` · `GET …/{id}` · `POST …/approvals/actions` |
| Work items ("Fix Now") | `GET/POST /clinics/{id}/work-items` · `GET/PATCH …/{id}` |
| Reports | `GET/POST /clinics/{id}/reports` · `GET …/{id}` |
| Files | `POST /clinics/{id}/assets/uploads` · `…/{id}/confirm` · `GET …/assets` · `…/{id}/download-url` (new kind `chat_attachment`) |
| **Chat (new)** | `GET/POST /clinics/{id}/chat/messages` · `POST /clinics/{id}/chat/read` · `GET /chat/inbox` |
| Activity log | `GET /clinics/{id}/audit-events` |
| Notifications | `GET /notifications` · `POST /notifications/{id}/read` |

Not in v0.1.0 (planned for later versions): live chat push (WebSocket), a "Refresh data"
button for connected accounts, email copies of notifications, meetings and notes.
