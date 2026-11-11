"""
Predict router - handles batch prediction and SHAP computation.
Now persists results to SQLite database.
"""

import os
import uuid
from datetime import datetime
from io import BytesIO
from typing import Optional

import pandas as pd
import numpy as np
import joblib
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Form, Depends

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.preprocess import validate_dataframe, prepare_for_prediction
from utils.shap_utils import (
    compute_shap_values,
    get_individual_shap,
    generate_narrative,
    get_global_feature_importance,
)
from database import get_db, save_session_to_db, load_session_from_db, list_sessions_from_db, delete_session_from_db, StudentPrediction, SelectionSession, ActivityLog

router = APIRouter(prefix="/predict", tags=["Predict"])

# Load model and encoders
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(SCRIPT_DIR, "..", "model")

model = joblib.load(os.path.join(MODEL_DIR, "xgboost_kipk.pkl"))
label_encoders = joblib.load(os.path.join(MODEL_DIR, "label_encoders.pkl"))
feature_names = joblib.load(os.path.join(MODEL_DIR, "feature_names.pkl"))


def classify_eligibility(score: float) -> str:
    """Classify eligibility based on probability score."""
    if score >= 0.75:
        return "Sangat Layak"
    elif score >= 0.50:
        return "Layak"
    elif score >= 0.25:
        return "Kurang Layak"
    else:
        return "Tidak Layak"


@router.post("/batch")
async def predict_batch(file: UploadFile = File(...), is_raw: str = Form("false"), db=Depends(get_db)):
    """
    Upload Excel and run batch prediction with SHAP.
    Returns ranked results with SHAP explanations.
    Results are persisted to the database.
    """
    try:
        contents = await file.read()
        if file.filename.endswith(".csv"):
            try:
                df = pd.read_csv(BytesIO(contents), sep=";")
                if len(df.columns) == 1:
                    df = pd.read_csv(BytesIO(contents), sep=",")
            except Exception:
                df = pd.read_csv(BytesIO(contents), sep=",")
        else:
            df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca file: {str(e)}")

    # Validate
    is_raw_bool = is_raw.lower() == "true"
    is_valid, errors, cleaned_df = validate_dataframe(df, is_raw=is_raw_bool)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={"message": "Data tidak valid", "errors": errors},
        )

    # Prepare features for prediction
    X = prepare_for_prediction(cleaned_df, label_encoders)

    # Run prediction
    probabilities = model.predict_proba(X)[:, 1]
    predictions = (probabilities >= 0.45).astype(int)

    # Compute SHAP values
    shap_values = compute_shap_values(model, X)

    # Build results
    session_id = str(uuid.uuid4())[:8]
    results = []

    for idx in range(len(cleaned_df)):
        row = cleaned_df.iloc[idx]
        score = float(probabilities[idx])
        kategori = classify_eligibility(score)

        # Get SHAP factors for this individual
        factors = get_individual_shap(
            shap_values, feature_names, idx,
            label_encoders=label_encoders,
            original_values=row,
        )

        # Generate narrative
        nim = str(row.get("NIM", f"MHS-{idx+1}"))
        nama = str(row.get("Nama_Mahasiswa", row.get("Nama Mahasiswa", f"Mahasiswa {idx+1}")))

        result = {
            "rank": 0,  # Will be set after sorting
            "nim": nim,
            "nama": nama,
            "skor": round(score * 100, 2),
            "skor_raw": score,
            "prediksi": "Diterima" if predictions[idx] == 1 else "Tidak Diterima",
            "kategori": kategori,
            "keputusan_final": None,
            "alasan_override": None,
            "shap_factors": factors[:7],  # Top 7 factors
            "narrative": generate_narrative(factors, nama),
            "data_asli": {
                "jenis_kelamin": str(row.get("Jenis Kelamin", "")),
                "status_dtks": str(row.get("Status DTKS", "")),
                "status_p3ke": str(row.get("Status P3KE", "")),
                "pekerjaan_ayah": str(row.get("Pekerjaan Ayah", "")),
                "status_ayah": str(row.get("Status Ayah", "")),
                "penghasilan_ayah": int(float(row.get("Penghasilan Ayah", 0)) if not pd.isna(row.get("Penghasilan Ayah")) else 0),
                "pekerjaan_ibu": str(row.get("Pekerjaan Ibu", "")),
                "status_ibu": str(row.get("Status Ibu", "")),
                "penghasilan_ibu": int(float(row.get("Penghasilan Ibu", 0)) if not pd.isna(row.get("Penghasilan Ibu")) else 0),
                "total_penghasilan": int(float(row.get("Total Penghasilan", 0)) if not pd.isna(row.get("Total Penghasilan")) else 0),
                "jumlah_tanggungan": str(row.get("Jumlah Tanggungan", "0")),
                "pilihan_prodi_1": str(row.get("Pilihan Prodi 1", "")),
                "pilihan_prodi_2": str(row.get("Pilihan Prodi 2", "")),
            },
        }
        results.append(result)

    # Sort by score (highest first) and assign ranks
    results.sort(key=lambda x: x["skor_raw"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    # Global feature importance
    global_importance = get_global_feature_importance(shap_values, feature_names)

    # Build session data
    session_data = {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "filename": file.filename,
        "total_mahasiswa": len(results),
        "kuota": None,
        "results": results,
        "global_importance": global_importance,
        "stats": {
            "total": len(results),
            "sangat_layak": len([r for r in results if r["kategori"] == "Sangat Layak"]),
            "layak": len([r for r in results if r["kategori"] == "Layak"]),
            "kurang_layak": len([r for r in results if r["kategori"] == "Kurang Layak"]),
            "tidak_layak": len([r for r in results if r["kategori"] == "Tidak Layak"]),
            "avg_skor": round(float(np.mean([r["skor"] for r in results])), 2) if results else 0.0,
            "diterima_model": len([r for r in results if r["prediksi"] == "Diterima"]),
        },
    }

    # ✅ PERSIST TO DATABASE
    save_session_to_db(db, session_data)

    # Log activity
    log = ActivityLog(username="admin", action="predict_batch", detail=f"File: {file.filename}, Total: {len(results)}")
    db.add(log)
    db.commit()

    return session_data


@router.get("/sessions")
async def list_sessions(db=Depends(get_db)):
    """List all prediction sessions from database."""
    return list_sessions_from_db(db)


@router.get("/result/{session_id}")
async def get_result(session_id: str, db=Depends(get_db)):
    """Get prediction results for a session from database."""
    session_data = load_session_from_db(db, session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")
    return session_data


@router.get("/result/{session_id}/{nim}")
async def get_detail(session_id: str, nim: str, db=Depends(get_db)):
    """Get detailed prediction + SHAP for a specific student."""
    session_data = load_session_from_db(db, session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")

    for r in session_data["results"]:
        if r["nim"] == nim:
            return r

    raise HTTPException(status_code=404, detail=f"Mahasiswa dengan NIM {nim} tidak ditemukan")


@router.post("/result/{session_id}/kuota")
async def set_kuota(session_id: str, kuota: int = Query(..., gt=0), db=Depends(get_db)):
    """Set quota for a session - highlight cutoff line."""
    sess = db.query(SelectionSession).filter(SelectionSession.session_id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")

    sess.kuota = kuota
    
    # Update all predictions' dalam_kuota status
    predictions = db.query(StudentPrediction).filter(
        StudentPrediction.session_id == session_id
    ).order_by(StudentPrediction.rank).all()

    for i, pred in enumerate(predictions):
        pred.dalam_kuota = i < kuota

    db.commit()

    return {
        "session_id": session_id,
        "kuota": kuota,
        "dalam_kuota": min(kuota, len(predictions)),
        "diluar_kuota": max(0, len(predictions) - kuota),
    }


@router.put("/result/{session_id}/{nim}/override")
async def override_decision(session_id: str, nim: str, keputusan: str, alasan: str = "", db=Depends(get_db)):
    """Admin override for a specific student's decision."""
    if keputusan not in ["Diterima", "Tidak Diterima"]:
        raise HTTPException(
            status_code=400,
            detail="Keputusan harus 'Diterima' atau 'Tidak Diterima'",
        )

    pred = db.query(StudentPrediction).filter(
        StudentPrediction.session_id == session_id,
        StudentPrediction.nim == nim,
    ).first()

    if not pred:
        raise HTTPException(status_code=404, detail=f"Mahasiswa dengan NIM {nim} tidak ditemukan")

    pred.keputusan_final = keputusan
    pred.alasan_override = alasan
    pred.override_at = datetime.now()

    # Log override
    log = ActivityLog(username="admin", action="override", detail=f"Session: {session_id}, NIM: {nim}, Keputusan: {keputusan}")
    db.add(log)
    db.commit()

    return pred.to_dict()


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, db=Depends(get_db)):
    """Delete a prediction session and all its data."""
    success = delete_session_from_db(db, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")

    log = ActivityLog(username="admin", action="delete_session", detail=f"Deleted session: {session_id}")
    db.add(log)
    db.commit()

    return {"message": f"Sesi {session_id} berhasil dihapus"}
