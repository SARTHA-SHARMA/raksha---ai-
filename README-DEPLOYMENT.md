# RAKSHA AI — Deployment Guide

## Local single-server mode

The FastAPI backend can now serve the existing frontend too. After installing dependencies:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. API documentation is at `/docs`. FastAPI supports serving the application this way; production deployment should use a proper process/container setup and HTTPS.

## Docker

```bash
docker compose up --build
```

Then open `http://127.0.0.1:8000`.

The SQLite database is stored in the Docker volume `raksha_data`. For a real multi-instance production deployment, migrate the application database to PostgreSQL or another managed database.

## Production checklist

- Set a restricted `CORS_ORIGINS` value instead of `*`.
- Put HTTPS/TLS in front of the API.
- Use a managed database for production.
- Replace demo credentials with administrator-created accounts.
- Rotate any alert/API credentials and move secrets to environment variables.
- Connect only authorized disaster-management/sensor feeds.
- Validate and monitor the ML model before treating its output as an operational warning.

## Live data

The frontend already consumes public Open-Meteo weather/soil and air-quality feeds. River gauges, official disaster feeds, and emergency dispatch integrations remain separate integrations and should only be labeled live after an authorized source is connected.
