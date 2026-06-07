# Hosting watchlist-monitor on Google Cloud Platform

This guide deploys the **web UI** to **Cloud Run** (serverless), with **Cloud SQL
for PostgreSQL** as the persistent database and **Cloud Scheduler** driving the
daily email job. Once deployed you get a public HTTPS URL you can open from
anywhere.

> **Why Postgres, not SQLite?** Cloud Run instances have an *ephemeral*
> filesystem and scale to zero — a SQLite file would be wiped on every restart.
> The code auto-switches to Postgres when the `DATABASE_URL` env var is present
> (see `monitor/store.py`); locally it still uses SQLite with no changes.

---

## What you'll create

| Component | Purpose | Rough cost |
|---|---|---|
| Cloud Run service | Runs the FastAPI app | Pay-per-request; ~$0–5/mo at personal volume |
| Cloud SQL (Postgres) | Persistent DB | ~$8–10/mo (smallest `db-f1-micro`) |
| Cloud Scheduler job | Triggers the daily report | Free (≤3 jobs) |
| Secret Manager | Holds DB URL, SMTP, tokens | Negligible |
| Artifact Registry | Stores the built image | Negligible |

There is **no permanently-free Postgres** on GCP — budget ~$10/month. To avoid
that cost entirely, keep using the GitHub Actions cron + local UI combo instead.

---

## Prerequisites

1. A GCP project with billing enabled. Note your **PROJECT_ID**.
2. The `gcloud` CLI installed and authenticated: `gcloud auth login`.
3. Pick a region, e.g. `us-central1` (or `asia-south1` for India).

```bash
export PROJECT_ID=your-project-id
export REGION=us-central1
gcloud config set project $PROJECT_ID

# Enable the APIs we need
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

---

## Step 1 — Create the Cloud SQL (Postgres) instance

```bash
# Instance (smallest tier; takes a few minutes)
gcloud sql instances create watchlist-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION

# A database and a user
gcloud sql databases create watchlist --instance=watchlist-db
gcloud sql users create appuser \
  --instance=watchlist-db \
  --password='CHOOSE-A-STRONG-PASSWORD'

# Note the connection name — looks like:  your-project-id:us-central1:watchlist-db
gcloud sql instances describe watchlist-db --format='value(connectionName)'
```

Cloud Run connects to Cloud SQL over a Unix socket at
`/cloudsql/<CONNECTION_NAME>`. The `DATABASE_URL` therefore uses the socket host:

```
postgresql://appuser:CHOOSE-A-STRONG-PASSWORD@/watchlist?host=/cloudsql/PROJECT_ID:REGION:watchlist-db
```

psycopg2 understands that URL form directly — no code changes needed.

---

## Step 2 — Store secrets in Secret Manager

Create one secret per value. `DATABASE_URL` and `JOB_TOKEN` are required; the SMTP
and OpenAI ones are optional (omit them and email just prints to the logs).

```bash
CONN=$(gcloud sql instances describe watchlist-db --format='value(connectionName)')

printf 'postgresql://appuser:CHOOSE-A-STRONG-PASSWORD@/watchlist?host=/cloudsql/%s' "$CONN" \
  | gcloud secrets create DATABASE_URL --data-file=-

# A random shared secret that protects the daily-job endpoint
openssl rand -hex 24 | gcloud secrets create JOB_TOKEN --data-file=-

# Optional — email delivery (Gmail app password, SendGrid, etc.)
printf 'smtp.gmail.com' | gcloud secrets create SMTP_HOST --data-file=-
printf '587'            | gcloud secrets create SMTP_PORT --data-file=-
printf 'you@gmail.com'  | gcloud secrets create SMTP_USER --data-file=-
printf 'your-app-pass'  | gcloud secrets create SMTP_PASS --data-file=-
printf 'you@gmail.com'  | gcloud secrets create MAIL_TO   --data-file=-

# Optional — AI context notes
printf 'sk-...' | gcloud secrets create OPENAI_API_KEY --data-file=-
```

> If you skip the optional secrets, also remove them from the `--set-secrets`
> lists in Step 3 and in `.github/workflows/deploy-gcp.yml`.

---

## Step 3 — Deploy to Cloud Run (manual, from source)

The simplest path — Cloud Run builds the `Dockerfile` for you:

```bash
gcloud run deploy watchlist-monitor \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --add-cloudsql-instances "$CONN" \
  --set-secrets "DATABASE_URL=DATABASE_URL:latest,JOB_TOKEN=JOB_TOKEN:latest,SMTP_HOST=SMTP_HOST:latest,SMTP_PORT=SMTP_PORT:latest,SMTP_USER=SMTP_USER:latest,SMTP_PASS=SMTP_PASS:latest,MAIL_TO=MAIL_TO:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest" \
  --memory 512Mi
```

When it finishes it prints a **Service URL** like
`https://watchlist-monitor-xxxxx-uc.a.run.app`. Open it — the UI loads, and on
first request the tables are created and seeded from `config.yaml`.

Grant the Cloud Run service account access to the secrets if prompted:

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
for s in DATABASE_URL JOB_TOKEN SMTP_HOST SMTP_PORT SMTP_USER SMTP_PASS MAIL_TO OPENAI_API_KEY; do
  gcloud secrets add-iam-policy-binding $s \
    --member="serviceAccount:$SA" \
    --role="roles/secretmanager.secretAccessor"
done
```

---

## Step 4 — Schedule the daily report (Cloud Scheduler)

The in-app APScheduler can't run on Cloud Run (instances sleep between requests),
so an external scheduler calls the protected `/api/job/run-daily` endpoint:

```bash
SERVICE_URL=$(gcloud run services describe watchlist-monitor --region $REGION --format='value(status.url)')
JOB_TOKEN=$(gcloud secrets versions access latest --secret=JOB_TOKEN)

gcloud scheduler jobs create http watchlist-daily \
  --location $REGION \
  --schedule "30 16 * * 1-5" \
  --time-zone "America/New_York" \
  --uri "$SERVICE_URL/api/job/run-daily" \
  --http-method POST \
  --headers "X-Job-Token=$JOB_TOKEN"
```

Adjust `--schedule` (cron) and `--time-zone` to taste (e.g.
`"0 18 * * 1-5"` + `Asia/Kolkata` for an evening report in India).

Test it immediately:

```bash
gcloud scheduler jobs run watchlist-daily --location $REGION
```

---

## Step 5 (optional) — Auto-deploy from GitHub

`.github/workflows/deploy-gcp.yml` redeploys on every push to `main` using
**keyless Workload Identity Federation**. Set these repo secrets:

| Secret | Value |
|---|---|
| `GCP_PROJECT_ID` | your project id |
| `GCP_REGION` | e.g. `us-central1` |
| `GCP_WIF_PROVIDER` | the Workload Identity provider resource name |
| `GCP_DEPLOY_SA` | a deploy service-account email |
| `CLOUD_SQL_CONNECTION_NAME` | output of the `connectionName` command |

Setting up WIF is a one-time step — follow Google's guide
("google-github-actions/auth" → Workload Identity Federation). The deploy SA needs
`roles/run.admin`, `roles/cloudsql.client`, `roles/iam.serviceAccountUser`, and
`roles/secretmanager.secretAccessor`.

---

## Security notes

- `--allow-unauthenticated` makes the UI **public to anyone with the URL**. This
  app has no login. For a single private user, either (a) remove that flag and put
  it behind **Identity-Aware Proxy (IAP)**, or (b) restrict by VPC/known IPs.
- The `/api/job/run-daily` endpoint is always protected by the `X-Job-Token`
  shared secret regardless of the above.
- yfinance is **personal-use**; a public deployment serving many users could
  violate its terms and get rate-limited. Keep this for your own use.
- The "Export to config.yaml" button writes to the container's ephemeral disk on
  Cloud Run and won't persist — it's a local-dev convenience only.

---

## Updating / tearing down

```bash
# Redeploy after code changes
gcloud run deploy watchlist-monitor --source . --region $REGION

# Tear everything down to stop billing
gcloud scheduler jobs delete watchlist-daily --location $REGION
gcloud run services delete watchlist-monitor --region $REGION
gcloud sql instances delete watchlist-db
```
