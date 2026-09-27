# For the frontend (Person 2): getting and using the contract

## 1. Get the contract

Each contract version is a GitHub Release of this repo, **"API contract vX.Y.Z"**, with one file:
`openapi.json`. What changed is in the release notes (same text as `openapi/CHANGELOG.md`).

Download it with the GitHub CLI (works for private repos once you are signed in with `gh auth login`):

```bash
gh release download v0.1.0 --repo <org>/radial-pulse-backend \
  --pattern openapi.json --dir packages/api-client/openapi --clobber
```

### Suggested `api:sync` target in the frontend repo

Pin the version in a small file so every developer and CI generate the same types:

```text
packages/api-client/openapi/VERSION      →  v0.1.0
```

```jsonc
// packages/api-client/project.json
"api:sync": {
  "executor": "nx:run-commands",
  "options": {
    "commands": [
      "gh release download $(cat packages/api-client/openapi/VERSION) --repo <org>/radial-pulse-backend --pattern openapi.json --dir packages/api-client/openapi --clobber",
      "pnpm nx run api-client:generate"
    ],
    "parallel": false
  }
}
```

To move to a new contract: change `VERSION`, run `api:sync`, fix what TypeScript reports, commit
the new `openapi.json` + generated types together.

In the frontend's CI, give `gh` a token that can read this repo (a fine-grained token with
**Contents: read** on `radial-pulse-backend`, stored as a secret such as `BACKEND_CONTRACT_TOKEN`,
used as `GH_TOKEN`).

## 2. Which contract is running?

`GET /health` → `{ "version": "<git sha>", "contract_version": "0.1.0", … }`.
DEV runs the newest `main`; it can be ahead of the last release.

## 3. Rules that save time

- **Never add a field on the frontend** that the contract lacks. Ask for a contract change.
- Use `GET /auth/me` → `permissions` and `clinics[].permissions` to show/hide buttons only; the API
  checks again.
- Errors are always `{ type, title, status, detail }`. 404 on a clinic route = no access (or it
  does not exist); show "not found".
- Times are UTC ISO strings. Show them in the timezone from `GET /settings/platform`
  (`Asia/Kolkata` by default) with its `date_format`.

## 4. New in v0.1.0: chat, connected accounts, settings

### Chat (Client Collaboration)

| Screen action | Call |
|---|---|
| Open a clinic's chat | `GET /clinics/{id}/chat/messages` (newest page, oldest first) → then `POST …/chat/read` |
| Scroll up | `GET …/chat/messages?before=<first id>` |
| While the chat is open (every 10–15 s) | `GET …/chat/messages?after=<last id>` |
| Unread badge / "Unread Chats" tile / chat list | `GET /chat/inbox` (poll every 30–60 s) |
| Send text | `POST …/chat/messages` `{ "body": "…" }` |
| Send a photo/PDF | upload with `POST …/assets/uploads` (kind `chat_attachment`) → PUT to S3 → `…/confirm` → `POST …/chat/messages` `{ "attachment_asset_id": "…" }` |

Use `sender_side` (`radial_pulse` / `clinic`) to pick the bubble side. Show a short notice in the
chat: *"Please do not share patient health information here."* Clinic Team Members can read the
chat but not send (hide the input when `chat:write` is missing).

### Connected accounts

1. `GET /clinics/{id}/connections` → six cards. `available: false` = disable the Connect button
   ("coming soon"); `status` = `not_connected | pending | connected | needs_reconnect | disconnected`.
2. **Connect**: `POST …/connections/{platform}/start` `{ "redirect_uri": "<your callback page>" }`
   → open `authorization_url` (web: same tab or popup; mobile: `expo-web-browser` auth session).
3. The platform returns to your callback with `?code=…&state=…` → `POST …/connections/{platform}/complete`
   `{ "code", "state" }` → the updated card. 409 = took too long (press Connect again);
   502 = the platform refused; 503 = not set up yet.
4. Disconnect: `POST …/connections/{platform}/disconnect`.

Your callback addresses must be on the backend's `OAUTH_REDIRECT_URIS` list — send Person 1 the
exact web URL(s) and the mobile scheme (e.g. `radialpulse://connections/callback`).

The Social Media screen numbers: `GET /clinics/{id}/snapshots?source=instagram&latest=true`
(cards), `…/snapshots?metric_key=instagram.followers` (growth chart; use `value_number`).

### Settings

| Tab | Calls |
|---|---|
| My Profile | `GET/PATCH /auth/me`; photo: `POST /auth/me/avatar/uploads` → PUT to S3 → `POST /auth/me/avatar/confirm` `{ key }`; `DELETE /auth/me/avatar` |
| Notifications | `GET /auth/me/notification-settings` · `PUT` with only the switches that changed |
| Security | `GET /auth/me` → `sign_in_method` ("google"), `last_login_at`. No password to change |
| General (Admin) | `GET /settings/platform` (everyone can read) · `PATCH` (Admin) |
| Integrations (Admin) | `GET /settings/integrations` |
| Help & Support (clinic app) | `support_email` / `support_phone` from `GET /settings/platform` |
