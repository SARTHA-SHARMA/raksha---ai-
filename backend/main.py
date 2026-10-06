import os
from pathlib import Path
import json, sqlite3, secrets, hashlib, hmac
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
MODEL = json.loads((BASE / 'model.json').read_text())
DB_PATH = Path(os.getenv('RAKSHA_DB_PATH', str(BASE / 'raksha.db')))

app = FastAPI(title='RAKSHA AI Full-Stack API', version='10.0')
_cors = os.getenv('CORS_ORIGINS', '*')
CORS_ORIGINS = [x.strip() for x in _cors.split(',') if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 210_000)
    return f'pbkdf2_sha256$210000${salt.hex()}${digest.hex()}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt_hex, digest_hex = encoded.split('$')
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def init_db():
    conn = db()
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','citizen')),
        name TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        region TEXT,
        rainfall_mm REAL NOT NULL,
        soil_moisture_pct REAL NOT NULL,
        population REAL NOT NULL,
        river_level REAL NOT NULL,
        slope_degree REAL NOT NULL,
        risk_score REAL NOT NULL,
        risk_level TEXT NOT NULL,
        raw_model_output REAL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    ''')
    users = [
        ('admin', 'raksha123', 'admin', 'Emergency Administrator'),
        ('citizen', 'citizen123', 'citizen', 'Citizen User'),
    ]
    for username, password, role, name in users:
        exists = conn.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
        if not exists:
            conn.execute('INSERT INTO users(username,password_hash,role,name,created_at) VALUES(?,?,?,?,?)',
                         (username, hash_password(password), role, name, now()))
    conn.commit(); conn.close()


def now():
    return datetime.now(timezone.utc).isoformat()


def user_from_token(token: Optional[str]):
    if not token:
        return None
    conn = db()
    row = conn.execute('''SELECT u.id,u.username,u.role,u.name FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?''', (token,)).fetchone()
    conn.close()
    return dict(row) if row else None


class LoginInput(BaseModel):
    username: str
    password: str
    role: str


class RiskInput(BaseModel):
    Rainfall_mm: float | None = Field(default=None, ge=0)
    Soil_Moisture_pct: float | None = Field(default=None, ge=0, le=100)
    Population: float | None = Field(default=None, ge=0)
    rainfall_mm: float | None = Field(default=None, ge=0)
    soil_moisture_pct: float | None = Field(default=None, ge=0, le=100)
    population: float | None = Field(default=None, ge=0)
    river_level: float | None = Field(default=None, ge=0)
    slope_degree: float | None = Field(default=None, ge=0)
    region: str | None = None

    def features(self):
        return {
            'Rainfall_mm': self.Rainfall_mm if self.Rainfall_mm is not None else self.rainfall_mm,
            'Soil_Moisture_pct': self.Soil_Moisture_pct if self.Soil_Moisture_pct is not None else self.soil_moisture_pct,
            'Population': self.Population if self.Population is not None else self.population,
        }


def tree_predict(tree, x):
    node = tree
    while 'leaf' not in node:
        feature = node['split']
        value = x.get(feature)
        if value is None:
            branch = node.get('missing', node['no'])
        elif value < node['split_condition']:
            branch = node['yes']
        else:
            branch = node['no']
        node = next(child for child in node['children'] if child['nodeid'] == branch)
    return node['leaf']


def predict(x):
    return MODEL['base'] + sum(tree_predict(t, x) for t in MODEL['trees'])


def calculate_risk(x, river_level=0.0, slope_degree=0.0):
    model_features = {'Rainfall_mm': min(92.0, x['Rainfall_mm'] / 2.0), 'Soil_Moisture_pct': x['Soil_Moisture_pct'], 'Population': x['Population']}
    raw = predict(model_features)
    ml_raw = max(0.0, min(68.0, raw))
    ml_score = max(0.0, min(100.0, (ml_raw / 68.0) * 100.0))
    rain = x['Rainfall_mm']
    environment = (min(rain / 200.0, 1.0) * 100.0 * 0.35) + (x['Soil_Moisture_pct'] * 0.25) + (min(river_level / 5.0, 1.0) * 100.0 * 0.20) + (slope_degree * 0.20)
    composite = (ml_score * 0.30) + (environment * 0.70)
    return max(1.0, min(99.0, composite)), raw, ml_score, environment


@app.on_event('startup')
def startup():
    init_db()


@app.get('/health')
def health():
    return {'status':'ok','model':'XGBoost Regressor','records':10010,'r2':0.621,'database':'sqlite','features':['Rainfall_mm','Soil_Moisture_pct','Population']}


@app.post('/auth/login')
def login(payload: LoginInput):
    conn = db()
    row = conn.execute('SELECT * FROM users WHERE username=?', (payload.username.strip().lower(),)).fetchone()
    if not row or row['role'] != payload.role or not verify_password(payload.password, row['password_hash']):
        conn.close()
        raise HTTPException(status_code=401, detail='Invalid username, password, or selected access role.')
    token = secrets.token_urlsafe(32)
    conn.execute('INSERT INTO sessions(token,user_id,created_at) VALUES(?,?,?)', (token, row['id'], now()))
    conn.commit(); conn.close()
    return {'token':token,'username':row['username'],'role':row['role'],'name':row['name']}


@app.post('/auth/logout')
def logout(authorization: Optional[str] = Header(default=None)):
    token = authorization.replace('Bearer ', '', 1) if authorization else None
    if token:
        conn=db(); conn.execute('DELETE FROM sessions WHERE token=?',(token,)); conn.commit(); conn.close()
    return {'status':'logged_out'}


@app.get('/auth/me')
def me(authorization: Optional[str] = Header(default=None)):
    token = authorization.replace('Bearer ', '', 1) if authorization else None
    user = user_from_token(token)
    if not user: raise HTTPException(status_code=401, detail='Session expired or invalid')
    return user


@app.post('/predict-risk')
def predict_risk(payload: RiskInput, authorization: Optional[str] = Header(default=None)):
    x = payload.features()
    if any(v is None for v in x.values()):
        raise HTTPException(status_code=422, detail='Rainfall, soil moisture and population are required')
    score, raw, ml_score, environment = calculate_risk(x, payload.river_level or 0.0, payload.slope_degree or 0.0)
    level = 'LOW' if score < 40 else 'MODERATE' if score < 70 else 'HIGH' if score < 85 else 'CRITICAL'
    user = user_from_token(authorization.replace('Bearer ', '', 1)) if authorization else None
    conn = db()
    conn.execute('''INSERT INTO predictions(user_id,region,rainfall_mm,soil_moisture_pct,population,river_level,slope_degree,risk_score,risk_level,raw_model_output,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)''', (user['id'] if user else None, payload.region, x['Rainfall_mm'], x['Soil_Moisture_pct'], x['Population'], payload.river_level or 0.0, payload.slope_degree or 0.0, round(score,2), level, round(raw,4), now()))
    conn.commit(); conn.close()
    return {'risk_score':round(score,2),'risk_level':level,'raw_model_output':round(raw,4),'ml_score':round(ml_score,2),'environment_score':round(environment,2),'model':'XGBoost Regressor','warning':'Prototype risk estimate; not a certified emergency warning.'}


@app.post('/predict')
def predict_legacy(payload: RiskInput, authorization: Optional[str] = Header(default=None)):
    return predict_risk(payload, authorization)


@app.get('/predictions/history')
def prediction_history(limit: int = 20, authorization: Optional[str] = Header(default=None)):
    token = authorization.replace('Bearer ', '', 1) if authorization else None
    user = user_from_token(token)
    if not user: raise HTTPException(status_code=401, detail='Login required')
    limit = max(1, min(limit, 100))
    conn=db()
    rows=conn.execute('''SELECT id,region,rainfall_mm,soil_moisture_pct,population,river_level,slope_degree,risk_score,risk_level,created_at
                         FROM predictions WHERE user_id=? ORDER BY id DESC LIMIT ?''',(user['id'],limit)).fetchall()
    conn.close()
    return {'count':len(rows),'items':[dict(r) for r in rows]}


# Serve the existing RAKSHA AI frontend from the same FastAPI service.
# API routes are defined above, so this catch-all mount only handles frontend assets/pages.
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
