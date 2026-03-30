# Flight Tracking & ATC Management System

Backend: FastAPI + SQLAlchemy with SQLite for local dev or Cloud SQL (MySQL) in production. Frontend: static HTML/JS served from `/ui`. Optional asynchronous messaging uses Google Cloud Tasks.

## Repository layout
- `app/` – FastAPI app, routers, database models, Cloud Tasks callback
- `frontend/` – static dashboard (served by FastAPI)
- `requirements.txt` – Python dependencies
- `Dockerfile` – container image for Cloud Run or Docker
- `cloudbuild.yaml` – Cloud Build recipe to deploy to Cloud Run

## Prerequisites
- Python 3.12+ and `pip`
- (Recommended) virtualenv: `python -m venv venv && source venv/bin/activate`
- For containerized deploys: Docker
- For GCP deploys: `gcloud` CLI + a Cloud SQL (MySQL) instance and Cloud Tasks queue

## Local development (SQLite, no extra setup)
1) Install deps
```bash
pip install -r requirements.txt
```
2) Run the API
```bash
uvicorn app.main:app --reload --port 8000
```
3) Open the UI at http://localhost:8000/ui (API docs: http://localhost:8000/docs). SQLite file `atc_local.db` is created automatically in the repo root. Health checks: `/health`, `/health/db`.

### Local environment variables
None required for SQLite. Optional overrides:
- `PORT` (default 8000 locally, 8080 in Docker)
- `GOOGLE_CLOUD_PROJECT`, `CLOUD_TASKS_LOCATION`, `CLOUD_TASKS_QUEUE`, `SERVICE_URL` – only needed if you want Cloud Tasks to run while local; otherwise messaging is skipped.

## Running with Docker
```bash
docker build -t atc-system .
docker run --rm -p 8000:8080 \
  -e PORT=8080 \
  -e DB_USER=... -e DB_PASS=... -e DB_NAME=... \
  -e INSTANCE_CONNECTION_NAME=... \
  -e GOOGLE_CLOUD_PROJECT=... -e SERVICE_URL=https://your-service-url \
  atc-system
```
When `INSTANCE_CONNECTION_NAME` is set the app uses Cloud SQL (MySQL) over the unix socket `/cloudsql/<instance>`; without it the container falls back to SQLite.

## Deploying to Google Cloud Run via Cloud Build
1) One-time setup (Cloud Shell):
```bash
gcloud tasks queues create atc-events --location=northamerica-northeast2
gcloud run services add-iam-policy-binding airports \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role=roles/run.invoker \
  --region=northamerica-northeast2
```
2) Ensure a Cloud SQL MySQL instance exists and note its connection name.

3) Trigger Cloud Build with substitutions (update values):
```bash
gcloud builds submit --config cloudbuild.yaml --substitutions \
  _DB_USER=myuser,_DB_PASS=mypassword,_DB_NAME=atc,\
  _INSTANCE_CONNECTION_NAME=project:region:instance,\
  _GOOGLE_CLOUD_PROJECT=my-gcp-project,\
  _SERVICE_URL=https://airports-xxxx-pd.a.run.app,\
  _SA_EMAIL=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com
```
Cloud Build will build the image and deploy a Cloud Run service named `airports` in region `northamerica-northeast2` with the required env vars.

### Required runtime env vars (Cloud Run)
- `DB_USER`, `DB_PASS`, `DB_NAME`, `INSTANCE_CONNECTION_NAME` – Cloud SQL credentials/socket
- `GOOGLE_CLOUD_PROJECT` – used by Cloud Tasks client
- `CLOUD_TASKS_LOCATION` (default `northamerica-northeast1`)
- `CLOUD_TASKS_QUEUE` (default `atc-events`)
- `SERVICE_URL` – public URL of the deployed service, used so Cloud Tasks POST back to `/tasks/handle`
- `SA_EMAIL` – service account email used for Cloud Tasks signing (passed from cloudbuild substitution)
- `PORT` – provided by Cloud Run automatically

## Operational notes
- Database schema is auto-created at startup; `/admin/recreate-db` can drop & recreate tables if the schema drifts (remove or protect this endpoint in production).
- Tasks endpoint: Cloud Tasks POSTs to `/tasks/handle`; events are logged even if handler errors.
- Frontend is served statically at `/ui`; APIs are relative to the same origin.

## Useful commands
- Lint/type-check quickly: `python -m py_compile app/**/*.py` (no formatter configured)
- Run health locally: `curl http://localhost:8000/health` and `curl http://localhost:8000/health/db`
