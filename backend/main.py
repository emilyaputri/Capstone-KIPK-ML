"""
KIPK-ML Admin Dashboard - FastAPI Backend
Entry point for the application.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# JWT handling
import hashlib
import json
import base64
import hmac
import time

# Database
from database import init_db, get_db, list_sessions_from_db, ActivityLog, IS_SQLITE

app = FastAPI(
    title="KIPK-ML Admin Dashboard API",
    description="Sistem Pendukung Keputusan Seleksi KIP-K berbasis Machine Learning",
    version="2.0.0",
)

# CORS
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def on_startup():
    init_db()
    print("[OK] Database initialized")


# ========== Simple JWT Implementation ==========
SECRET_KEY = os.environ.get("SECRET_KEY", "kipk-ml-secret-key-2024-admin")
ALGORITHM = "HS256"

# Default admin credentials (override via env ADMIN_PASSWORD di produksi)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
ADMIN_USERS = {
    "admin": {
        "password_hash": hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest(),
        "name": "Admin KIPK",
        "role": "admin",
    }
}

security = HTTPBearer(auto_error=False)


def create_token(data: dict, expires_hours: int = 24) -> str:
    """Create a simple JWT-like token."""
    payload = {
        **data,
        "exp": int(time.time()) + (expires_hours * 3600),
    }
    payload_json = json.dumps(payload, sort_keys=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    signature = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a token."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        expected_sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_json)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan")
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Token tidak valid atau sudah kadaluarsa")
    return payload


# ========== Auth Routes ==========

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/login")
async def login(request: LoginRequest):
    """Login admin with username and password."""
    user = ADMIN_USERS.get(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Username atau password salah")

    password_hash = hashlib.sha256(request.password.encode()).hexdigest()
    if password_hash != user["password_hash"]:
        raise HTTPException(status_code=401, detail="Username atau password salah")

    token = create_token({
        "username": request.username,
        "name": user["name"],
        "role": user["role"],
    })

    return {
        "token": token,
        "user": {
            "username": request.username,
            "name": user["name"],
            "role": user["role"],
        },
    }


@app.get("/auth/me")
async def get_me(user=Depends(get_current_user)):
    """Get current user info."""
    return {
        "username": user["username"],
        "name": user["name"],
        "role": user["role"],
    }


# ========== Dashboard Stats (from DB) ==========

@app.get("/dashboard/stats")
async def get_dashboard_stats(db=Depends(get_db)):
    """Get general dashboard statistics from database."""
    sessions = list_sessions_from_db(db)

    total_sessions = len(sessions)
    total_mahasiswa = sum(s.get("total_mahasiswa", 0) for s in sessions)

    return {
        "total_sessions": total_sessions,
        "total_mahasiswa_diproses": total_mahasiswa,
        "sessions": [
            {
                "session_id": s["session_id"],
                "created_at": s["created_at"],
                "filename": s["filename"],
                "total": s.get("total_mahasiswa", 0),
                "kuota": s.get("kuota"),
                "stats": s.get("stats", {}),
            }
            for s in sessions
        ],
    }


# ========== Activity Log ==========

@app.get("/activity-log")
async def get_activity_log(limit: int = Query(50, le=200), db=Depends(get_db)):
    """Get recent activity log entries."""
    logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "username": log.username,
            "action": log.action,
            "detail": log.detail,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


# ========== Include Routers ==========

from routers.upload import router as upload_router
from routers.predict import router as predict_router
from routers.export import router as export_router

app.include_router(upload_router)
app.include_router(predict_router)
app.include_router(export_router)


@app.get("/")
async def root():
    return {
        "message": "KIPK-ML Admin Dashboard API",
        "version": "2.0.0",
        "database": "SQLite (local)" if IS_SQLITE else "PostgreSQL (managed)",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
