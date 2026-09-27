# What the backend needs from AWS

A short list to share with the DevOps owner. **How** to set these up is their decision.

## Permissions for the API

| Feature | Needs |
|---|---|
| Profile photos (Settings → My Profile) | read/write/delete files under `users/*` in the assets bucket (today only `clinics/*`) |
| Connected accounts (Instagram, Google, …) | create, update, restore and delete secrets named `radial-pulse/<env>/connections/*` in Secrets Manager, encrypted with the environment KMS key |

Later, the data-sync jobs (worker) will only need to **read** those secrets.

## Settings for the API

| Setting | What it is |
|---|---|
| `OAUTH_REDIRECT_URIS` | the frontend addresses the platforms may send the clinic back to (comma-separated) |
| `CONNECTION_SECRETS_KMS_KEY_ID` | the KMS key for the connected-account secrets |
| `GOOGLE_OAUTH_CLIENT_ID` / `_SECRET`, `META_APP_ID` / `_SECRET`, `LINKEDIN_CLIENT_ID` / `_SECRET`, `X_CLIENT_ID` / `_SECRET` | each platform's app credentials (the `_SECRET` ones are secrets) |

A platform without its credentials shows "not set up yet" in the app; nothing breaks.

## Database

The next deploy runs migration **0010** (chat, connected accounts, settings).
