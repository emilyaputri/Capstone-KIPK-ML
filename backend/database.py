"""
Database configuration and models for KIPK-ML System.
Uses SQLite for persistent session and prediction storage.
"""

import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Database file path
DB_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_database_url() -> str:
    """
    Env-driven untuk produksi (Vercel + Supabase Postgres).
    Tanpa env → SQLite lokal (perilaku lama tidak berubah).
    """
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not url:
        return f"sqlite:///{os.path.join(DB_DIR, 'kipk_ml.db')}"
    # Skema driver SQLAlchemy (Vercel/Supabase memberi postgres://)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    # Supabase pooler memaksa SSL
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


DATABASE_URL = _resolve_database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ========== Models ==========

class SelectionSession(Base):
    """Stores metadata for each upload/prediction session."""
    __tablename__ = "selection_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(16), unique=True, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    total_mahasiswa = Column(Integer, default=0)
    kuota = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Stats stored as JSON string
    stats_json = Column(Text, default="{}")
    global_importance_json = Column(Text, default="[]")

    # Relationships
    predictions = relationship("StudentPrediction", back_populates="session", cascade="all, delete-orphan")

    def set_stats(self, stats_dict):
        self.stats_json = json.dumps(stats_dict, default=str)

    def get_stats(self):
        return json.loads(self.stats_json) if self.stats_json else {}

    def set_global_importance(self, importance_list):
        self.global_importance_json = json.dumps(importance_list, default=str)

    def get_global_importance(self):
        return json.loads(self.global_importance_json) if self.global_importance_json else []


class StudentPrediction(Base):
    """Stores individual student prediction results."""
    __tablename__ = "student_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(16), ForeignKey("selection_sessions.session_id"), nullable=False, index=True)
    rank = Column(Integer, default=0)
    nim = Column(String(50), nullable=False)
    nama = Column(String(255), nullable=False)
    skor = Column(Float, default=0.0)
    skor_raw = Column(Float, default=0.0)
    prediksi = Column(String(50), default="")
    kategori = Column(String(50), default="")
    keputusan_final = Column(String(50), nullable=True)
    alasan_override = Column(Text, nullable=True)
    override_at = Column(DateTime, nullable=True)
    dalam_kuota = Column(Boolean, default=False)

    # Complex data stored as JSON
    shap_factors_json = Column(Text, default="[]")
    narrative = Column(Text, default="")
    data_asli_json = Column(Text, default="{}")

    # Relationship
    session = relationship("SelectionSession", back_populates="predictions")

    def set_shap_factors(self, factors):
        self.shap_factors_json = json.dumps(factors, default=str)

    def get_shap_factors(self):
        return json.loads(self.shap_factors_json) if self.shap_factors_json else []

    def set_data_asli(self, data):
        self.data_asli_json = json.dumps(data, default=str)

    def get_data_asli(self):
        return json.loads(self.data_asli_json) if self.data_asli_json else {}

    def to_dict(self):
        """Convert to dictionary matching the original API response format."""
        return {
            "rank": self.rank,
            "nim": self.nim,
            "nama": self.nama,
            "skor": self.skor,
            "skor_raw": self.skor_raw,
            "prediksi": self.prediksi,
            "kategori": self.kategori,
            "keputusan_final": self.keputusan_final,
            "alasan_override": self.alasan_override,
            "override_at": self.override_at.isoformat() if self.override_at else None,
            "dalam_kuota": self.dalam_kuota,
            "shap_factors": self.get_shap_factors(),
            "narrative": self.narrative,
            "data_asli": self.get_data_asli(),
        }


class ActivityLog(Base):
    """Audit log for admin actions."""
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ========== Database Initialization ==========

def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ========== CRUD Helpers ==========

def save_session_to_db(db, session_data: dict):
    """Save a complete prediction session (with all student results) to the database."""
    db_session = SelectionSession(
        session_id=session_data["session_id"],
        filename=session_data["filename"],
        total_mahasiswa=session_data["total_mahasiswa"],
        kuota=session_data.get("kuota"),
        created_at=datetime.fromisoformat(session_data["created_at"]),
    )
    db_session.set_stats(session_data["stats"])
    db_session.set_global_importance(session_data.get("global_importance", []))
    db.add(db_session)

    for r in session_data["results"]:
        pred = StudentPrediction(
            session_id=session_data["session_id"],
            rank=r["rank"],
            nim=r["nim"],
            nama=r["nama"],
            skor=r["skor"],
            skor_raw=r["skor_raw"],
            prediksi=r["prediksi"],
            kategori=r["kategori"],
            keputusan_final=r.get("keputusan_final"),
            alasan_override=r.get("alasan_override"),
            dalam_kuota=r.get("dalam_kuota", False),
            narrative=r.get("narrative", ""),
        )
        pred.set_shap_factors(r.get("shap_factors", []))
        pred.set_data_asli(r.get("data_asli", {}))
        db.add(pred)

    db.commit()


def load_session_from_db(db, session_id: str) -> dict:
    """Load a full session with all results from the database."""
    sess = db.query(SelectionSession).filter(SelectionSession.session_id == session_id).first()
    if not sess:
        return None

    predictions = db.query(StudentPrediction).filter(
        StudentPrediction.session_id == session_id
    ).order_by(StudentPrediction.rank).all()

    return {
        "session_id": sess.session_id,
        "created_at": sess.created_at.isoformat(),
        "filename": sess.filename,
        "total_mahasiswa": sess.total_mahasiswa,
        "kuota": sess.kuota,
        "results": [p.to_dict() for p in predictions],
        "global_importance": sess.get_global_importance(),
        "stats": sess.get_stats(),
    }


def list_sessions_from_db(db) -> list:
    """List all sessions (metadata only, no results)."""
    sessions = db.query(SelectionSession).order_by(SelectionSession.created_at.desc()).all()
    return [
        {
            "session_id": s.session_id,
            "created_at": s.created_at.isoformat(),
            "filename": s.filename,
            "total_mahasiswa": s.total_mahasiswa,
            "kuota": s.kuota,
            "stats": s.get_stats(),
        }
        for s in sessions
    ]


def delete_session_from_db(db, session_id: str) -> bool:
    """Delete a session and all its predictions."""
    sess = db.query(SelectionSession).filter(SelectionSession.session_id == session_id).first()
    if not sess:
        return False
    db.delete(sess)
    db.commit()
    return True
