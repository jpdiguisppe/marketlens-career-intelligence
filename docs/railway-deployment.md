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
DATABASE_URL=<Railway Postgres DATABASE_URL>
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

Frontend environment variable / build argument:

```text
VITE_API_BASE_URL=https://YOUR_BACKEND_DOMAIN
```

Important: this value is built into the React app at build time. If the backend domain changes, update `VITE_API_BASE_URL` and redeploy the frontend.

After deployment, generate a public Railway domain for the frontend.

Example:

```text
https://marketlens-production.up.railway.app
```

## Step 5: Smoke Test the Deployed App

1. Open the frontend Railway domain.
2. Open the backend docs at `/docs`.
3. Import `data/sample_job_postings.csv` through `POST /job-postings/import-csv`.
4. Refresh the frontend.
5. Run Resume Gap Analysis.

## Notes

- Do not use SQLite for the deployed public version.
- Use Railway Postgres through `DATABASE_URL`.
- The frontend and backend should be separate services.
- The frontend must use the backend's public URL, not `localhost`.
- Railway-generated domains use HTTPS automatically.

## Current Production Hardening Still Needed

Before calling this a real public beta, add:

- user accounts
- per-user saved postings/resumes
- input size limits
- CORS restriction to the deployed frontend domain
- rate limiting
- better error logging
- database migrations
