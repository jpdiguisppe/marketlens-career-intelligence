# Railway Deployment Guide

This guide explains how to deploy MarketLens on Railway.

MarketLens is an isolated monorepo:

- `backend/` contains the FastAPI API service.
- `frontend/` contains the React + TypeScript frontend.
- Railway Postgres stores production data.

## Target Railway Setup

Create one Railway project with three services:

1. **Postgres** database service
2. **Backend** service from `backend/`
3. **Frontend** service from `frontend/`

## Step 1: Create the Railway Project

1. Go to Railway.
2. Create a new project.
3. Choose **Deploy from GitHub repo**.
4. Select `jpdiguisppe/marketlens-career-intelligence`.

## Step 2: Add Postgres

1. In the Railway project canvas, add a new **Postgres** database service.
2. Railway will create database connection variables for that service.
3. The backend service will use the Postgres `DATABASE_URL`.
4. Keep all Postgres connection strings private. Do not paste them into the frontend, README, screenshots, or browser.

## Step 3: Deploy Backend Service

Create or configure a backend service connected to this GitHub repo.

Recommended backend settings:

```text
Root Directory: /backend
Dockerfile Path: Dockerfile
Healthcheck Path: /health
```

Backend environment variables:

```text
DATABASE_URL=<Railway Postgres connection string>
ADMIN_API_KEY=<long random secret value>
```

`ADMIN_API_KEY` protects admin-only endpoints such as creating postings, importing CSV files, and deleting postings. Do not commit this key to GitHub and do not put it in the frontend.

After the frontend has a public Railway domain, also set:

```text
CORS_ALLOWED_ORIGINS=https://YOUR_FRONTEND_DOMAIN
```

The backend Dockerfile already respects Railway's `PORT` variable:

```text
python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

After deployment, generate a public Railway domain for the backend.

Example:

```text
https://marketlens-backend-production.up.railway.app
```

Test:

```text
https://YOUR_BACKEND_DOMAIN/health
https://YOUR_BACKEND_DOMAIN/docs
```

## Step 4: Deploy Frontend Service

Create or configure a frontend service connected to the same GitHub repo.

Recommended frontend settings:

```text
Root Directory: /frontend
Dockerfile Path: Dockerfile
```

Frontend environment variable:

```text
VITE_API_BASE_URL=https://YOUR_BACKEND_DOMAIN
```

This value is public because it only points the browser to the backend API. It is not a secret.

After deployment, generate a public Railway domain for the frontend.

Example:

```text
https://marketlens-production.up.railway.app
```

Then return to the backend service and set:

```text
CORS_ALLOWED_ORIGINS=https://YOUR_FRONTEND_DOMAIN
```

Redeploy the backend after changing `CORS_ALLOWED_ORIGINS`.

## Step 5: Smoke Test the Deployed App

1. Open the frontend Railway domain.
2. Open the backend docs at `/docs`.
3. Confirm public read endpoints still work, such as `GET /job-postings`.
4. To import `data/sample_job_postings.csv`, call `POST /job-postings/import-csv` with the `X-Admin-API-Key` header set to the backend `ADMIN_API_KEY` value.
5. Refresh the frontend.
6. Run Resume Gap Analysis.

## Notes

- Do not use SQLite for the deployed public version.
- Use Railway Postgres through `DATABASE_URL`.
- Keep `DATABASE_URL`, `DATABASE_PUBLIC_URL`, `ADMIN_API_KEY`, and other secrets private.
- The frontend and backend should be separate services.
- The frontend must use the backend's public URL, not `localhost`.
- Railway-generated domains use HTTPS automatically.
- The backend must allow the deployed frontend URL through `CORS_ALLOWED_ORIGINS`.
- Admin-only endpoints require the `X-Admin-API-Key` header.

## Current Production Hardening Still Needed

Before calling this a real public beta, add:

- real user accounts
- per-user saved postings/resumes
- database migrations
- stronger distributed rate limiting
- better structured error logging
- accessibility audit fixes
- dependency vulnerability scanning
