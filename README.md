# RAKSHA AI v9 — Full-Stack Disaster Risk & Decision Support Prototype

RAKSHA AI v9 keeps the existing dashboard and adds a local FastAPI backend with:
- embedded XGBoost prototype model
- SQLite database
- hashed-password authentication
- admin/citizen roles
- server-side sessions
- prediction history per logged-in user
- backend-linked dashboard predictions

> Important: RAKSHA AI is a prototype risk-estimation and decision-support system, not a certified emergency-warning system.

## 1. Start backend (Windows)

Run `run_backend.bat`, or manually:

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend: `http://127.0.0.1:8000`
API docs: `http://127.0.0.1:8000/docs`

The first startup automatically creates `backend/raksha.db` and seeds development accounts:

- Admin: `admin / raksha123`
- Citizen: `citizen / citizen123`

Passwords are stored as PBKDF2-SHA256 hashes, not plaintext.

## 2. Start frontend

Run `run_frontend.bat`, or:

```bash
cd frontend
python -m http.server 5500
```

Open `http://127.0.0.1:5500`.

## 3. Main API endpoints

- `GET /health` — backend/model/database status
- `POST /auth/login` — authenticate a user and create a session token
- `POST /auth/logout` — invalidate the current session
- `GET /auth/me` — validate the current session
- `POST /predict` — calculate risk and save a prediction record
- `POST /predict-risk` — same prediction service
- `GET /predictions/history?limit=20` — retrieve history for the logged-in user

## 4. What is now real vs prototype

Real within this local application:
- FastAPI API communication
- XGBoost tree inference from the embedded exported model
- SQLite persistence
- password hashing
- server-side sessions
- user-specific prediction history

Still prototype/demo functionality:
- disaster labels and thresholds
- some environmental inputs and sensor feeds
- emergency agency integrations
- dispatch workflows
- official warning authority
- production-grade cloud deployment and security hardening

The next production phase should add validated datasets, official sensor/API integrations, stronger deployment security, audit logging, model monitoring, and authorized agency workflows.
