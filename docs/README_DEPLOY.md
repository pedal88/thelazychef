# Deployment Guide

Production runs on **Google Cloud Run** in project `thelazychefai-prod`, with **Cloud SQL (Postgres)** and a **Cloud Storage** bucket for assets. Deployment is fully automated by GitHub Actions (`.github/workflows/deploy.yaml`).

## How a deploy happens

1.  Open a pull request → the **Lint & Test** job runs (flake8 syntax checks + `pytest tests/`).
2.  Merge to `main` → **Lint & Test** runs again, then **Build & Deploy to Prod**:
    1.  Authenticates to Google Cloud via Workload Identity Federation (no key files).
    2.  Builds the Docker image and pushes it to Artifact Registry (`europe-north2-docker.pkg.dev/<PROJECT_ID>/app-repo/lazy-chef-app`).
    3.  Scans the image with Trivy; **critical/high vulnerabilities fail the deploy**.
    4.  Runs the Cloud Run job `lazy-chef-db-migration` (`flask db upgrade`) against Cloud SQL.
    5.  Deploys the image to the Cloud Run service `lazy-chef-app` (region `europe-west1`).

A deploy takes about 6 minutes. Watch it under the repo's **Actions** tab or with `gh run watch`.

To redeploy without a code change (e.g. after changing a secret), open the latest run on `main` in the Actions tab and click **Re-run all jobs**.

## Production infrastructure

| Resource | Value |
|---|---|
| GCP project | `thelazychefai-prod` |
| Cloud Run service | `lazy-chef-app` (`europe-west1`) |
| Migration job | `lazy-chef-db-migration` |
| Cloud SQL instance | `thelazychefai-prod:europe-north2:lazy-chef-db-eu` |
| Asset bucket | `thelazychef-assets` |
| Artifact Registry | `europe-north2-docker.pkg.dev/<PROJECT_ID>/app-repo` |

## GitHub secrets

Set under **Settings → Secrets and variables → Actions**. They're passed to Cloud Run as environment variables on every deploy.

| Secret | Purpose |
|---|---|
| `SECRET_KEY` | Flask session signing key. **The app refuses to start on Cloud Run without it.** Generate with `python -c "import secrets; print(secrets.token_hex(32))"`. Changing it logs everyone out. |
| `GOOGLE_API_KEY` | Gemini / Imagen API key. Its AI Studio project must have billing (Postpay recommended; a depleted prepay balance breaks generation with a 402 error). |
| `DB_USER`, `DB_PASS`, `DB_NAME` | Cloud SQL credentials |
| `PROJECT_ID` | GCP project for Artifact Registry |
| `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT` | Workload Identity Federation for GitHub → Google Cloud auth |

After changing a secret, redeploy (see above) for it to take effect.

## Troubleshooting

*   **Deploy fails at "Deploy to Cloud Run" / revision won't start**: check the Cloud Run logs. A missing or empty `SECRET_KEY` raises `RuntimeError: SECRET_KEY environment variable must be set in production`.
*   **Deploy fails at Trivy**: a dependency or base-image package has a known critical/high CVE. Bump the package in `requirements.txt` (see PR history for examples).
*   **Recipe generation shows "AI generation is temporarily unavailable (billing)"**: the Gemini key's project is out of credits; top up or switch to Postpay in [AI Studio](https://ai.studio/projects).
*   **Migration job fails**: run `gcloud run jobs executions list --job lazy-chef-db-migration --region europe-west1` and inspect the failing execution's logs.

Historical notes on the original manual setup: [README_CLOUD_DEPLOYMENT.md](README_CLOUD_DEPLOYMENT.md).
