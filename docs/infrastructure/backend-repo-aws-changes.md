# AWS / GitHub changes for the separate backend repo (for Person 3)

The backend moved from the `radial-pulse` monorepo to **`radial-pulse-backend`**. The deploy
steps are the same (build image → migrate task → roll api + worker), but a few things point at
the old repo name or need new permissions.

## 1. GitHub

- [ ] Create the repo `<org>/radial-pulse-backend` (private) and push (see the README).
- [ ] Protect `main`: pull request + 1 review + required check **"CI passed"**.
- [ ] Environments `dev` and `production` (production: required reviewers). Copy the same
      environment **variables** as the monorepo had (`AWS_REGION`, `AWS_DEPLOY_ROLE_ARN`,
      `ECR_REPOSITORY_URL`, `ECS_*`, `MIGRATION_*`, `API_BASE_URL`). The `WEB_*` / `VITE_*` ones
      now belong to the frontend repo.
- [ ] Allow GitHub Actions to create releases (Settings → Actions → Workflow permissions:
      read and write, or keep read-only — `release.yml` asks for `contents: write` itself).

## 2. OIDC trust (Terraform `modules/iam`)

The deploy role trusts `repo:<org>/<github_repo>:environment:<env>`. Now the API is deployed
from the backend repo and the web app from the frontend repo, so the trust needs **both**:

```hcl
# modules/iam/main.tf — trust statement condition
values = [for repo in var.github_repos : "repo:${var.github_org}/${repo}:environment:${each.value}"]
# environments/*/terraform.tfvars
github_repos = ["radial-pulse-backend", "radial-pulse-frontend"]
```

(Or split into a backend deploy role and a web deploy role — cleaner, each with only what it needs.)

## 3. New IAM permissions for the API task role

| Why | Permission | Resource |
|---|---|---|
| Profile photos (Settings → My Profile) | `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` | `<assets-bucket>/users/*` (today only `clinics/*`) |
| Connected accounts: save/remove tokens | `secretsmanager:CreateSecret`, `PutSecretValue`, `RestoreSecret`, `DeleteSecret`, `DescribeSecret`, `TagResource` | `arn:aws:secretsmanager:<region>:<acct>:secret:radial-pulse/<env>/connections/*` |
| …encrypted with the env KMS key | `kms:GenerateDataKey`, `kms:Decrypt`, `kms:Encrypt` | the environment KMS key |

Worker task role (for the data-sync jobs, later): `secretsmanager:GetSecretValue` on the same
prefix + `kms:Decrypt`.

## 4. New API settings (ECS task definition)

| Variable | Value | Kind |
|---|---|---|
| `OAUTH_REDIRECT_URIS` | the frontend callback URLs + mobile scheme, comma-separated | plain |
| `CONNECTION_SECRETS_KMS_KEY_ID` | the environment KMS key ARN | plain |
| `GOOGLE_OAUTH_CLIENT_ID` / `META_APP_ID` / `LINKEDIN_CLIENT_ID` / `X_CLIENT_ID` | from each platform's developer console | plain |
| `GOOGLE_OAUTH_CLIENT_SECRET` / `META_APP_SECRET` / `LINKEDIN_CLIENT_SECRET` / `X_CLIENT_SECRET` | same | **secret** — add to `radial-pulse/<env>/api` in Secrets Manager, inject via `secrets` |

A platform without its id + secret simply shows "not set up yet" in the app — nothing breaks.

## 5. Nothing else changes

Same ECR repository, same ECS services and task families, same migrate task, same database.
The first deploy from the new repo runs migration **0010** (chat, connected accounts, settings).
