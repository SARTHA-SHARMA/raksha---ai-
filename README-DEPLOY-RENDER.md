# RAKSHA AI — Render Deployment

## Recommended deployment
Use Render **Web Service + Docker**. Render supports Docker-based web services and gives the service a public `onrender.com` URL. The service must listen on `0.0.0.0` and the port supplied by the `PORT` environment variable.

## 1. Put the project on GitHub
Create a new GitHub repository, then upload the contents of this folder. The repository root should contain:

- `Dockerfile`
- `backend/`
- `frontend/`
- `docker-compose.yml`

## 2. Create the Render service
In Render:

1. **New → Web Service**
2. Connect the GitHub repository.
3. Runtime/Language: **Docker**
4. Use the repository-root `Dockerfile`.
5. Deploy.

The included Dockerfile starts FastAPI with `--host 0.0.0.0 --port ${PORT}`.

## 3. Environment variables
Set:

`CORS_ORIGINS=*`

For a real production deployment, replace `*` with your exact allowed frontend origin(s).

## 4. Database note
This project currently uses SQLite. The application supports `RAKSHA_DB_PATH` so a persistent disk can be mounted later.

For a demo deployment, SQLite may reset if the service is rebuilt/recreated. For production, move the database to PostgreSQL or attach appropriate persistent storage.

## 5. Verify
After deployment, open the Render URL:

`https://<your-service>.onrender.com/`

API health:

`https://<your-service>.onrender.com/health`

API docs:

`https://<your-service>.onrender.com/docs`

## Important
The deployed RAKSHA AI remains an AI risk-estimation/decision-support prototype. Do not present its output as an officially validated emergency warning system until the model, data feeds, alerting, and operational procedures have been independently validated and authorized.
