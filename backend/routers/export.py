"""
Export router - handles Excel and PDF export.
Now reads from database instead of in-memory sessions.
"""

import os
from io import BytesIO
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from database import get_db, load_session_from_db

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/{session_id}/excel")
async def export_excel(session_id: str, db=Depends(get_db)):
    """Export prediction results to Excel."""
    session = load_session_from_db(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")

    results = session["results"]

    # Build export DataFrame
    export_data = []
    for r in results:
        row = {
            "Ranking": r["rank"],
            "NIM": r["nim"],
            "Nama": r["nama"],
            "Skor Kelayakan (%)": r["skor"],
            "Kategori": r["kategori"],
            "Prediksi Model": r["prediksi"],
            "Keputusan Final": r.get("keputusan_final", r["prediksi"]),
            "Alasan Override": r.get("alasan_override", ""),
            "Dalam Kuota": "Ya" if r.get("dalam_kuota", False) else "Tidak",
        }

        # Add original data
        data_asli = r.get("data_asli", {})
        row.update({
            "Jenis Kelamin": data_asli.get("jenis_kelamin", ""),
            "Status DTKS": data_asli.get("status_dtks", ""),
            "Status P3KE": data_asli.get("status_p3ke", ""),
            "Pekerjaan Ayah": data_asli.get("pekerjaan_ayah", ""),
            "Penghasilan Ayah": data_asli.get("penghasilan_ayah", 0),
            "Status Ayah": data_asli.get("status_ayah", ""),
            "Pekerjaan Ibu": data_asli.get("pekerjaan_ibu", ""),
            "Penghasilan Ibu": data_asli.get("penghasilan_ibu", 0),
            "Status Ibu": data_asli.get("status_ibu", ""),
            "Total Penghasilan": data_asli.get("total_penghasilan", 0),
            "Jumlah Tanggungan": data_asli.get("jumlah_tanggungan", 0),
        })

        # Add top 3 SHAP factors
        for i, factor in enumerate(r.get("shap_factors", [])[:3]):
            row[f"Faktor SHAP {i+1}"] = f"{factor['label']} ({factor['shap_value']:+.4f})"

        export_data.append(row)

    df = pd.DataFrame(export_data)

    # Write to Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Hasil Seleksi", index=False)

        # Add stats sheet
        stats = session["stats"]
        stats_df = pd.DataFrame([
            {"Metrik": "Total Pendaftar", "Nilai": stats.get("total", 0)},
            {"Metrik": "Sangat Layak", "Nilai": stats.get("sangat_layak", 0)},
            {"Metrik": "Layak", "Nilai": stats.get("layak", 0)},
            {"Metrik": "Kurang Layak", "Nilai": stats.get("kurang_layak", 0)},
            {"Metrik": "Tidak Layak", "Nilai": stats.get("tidak_layak", 0)},
            {"Metrik": "Rata-rata Skor (%)", "Nilai": stats.get("avg_skor", 0)},
            {"Metrik": "Diterima (Model)", "Nilai": stats.get("diterima_model", 0)},
            {"Metrik": "Kuota", "Nilai": session.get("kuota", "Belum diset")},
        ])
        stats_df.to_excel(writer, sheet_name="Statistik", index=False)

    output.seek(0)

    filename = f"Hasil_Seleksi_KIPK_{session_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/template")
async def download_template():
    """Download Excel template for admin."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from utils.preprocess import generate_template_data

    df = generate_template_data()

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Data Pendaftar", index=False)

        # Add sheet with valid values info
        valid_info = pd.DataFrame([
            {"Kolom": "Jenis Kelamin", "Nilai Valid": "L, P"},
            {"Kolom": "Status DTKS", "Nilai Valid": "Terdata, Belum Terdata"},
            {"Kolom": "Status P3KE", "Nilai Valid": "Belum Terdata, Terdata: Desil 1-7"},
            {"Kolom": "Pekerjaan Ayah", "Nilai Valid": "Petani, Nelayan, Lainnya, Wirausaha, TIDAK BEKERJA, PNS, Peg. Swasta"},
            {"Kolom": "Status Ayah", "Nilai Valid": "Hidup, Wafat, Bercerai"},
            {"Kolom": "Pekerjaan Ibu", "Nilai Valid": "Lainnya, Petani, TIDAK BEKERJA, Wirausaha, Peg. Swasta, PNS"},
            {"Kolom": "Status Ibu", "Nilai Valid": "Hidup, Wafat"},
            {"Kolom": "Penghasilan Ayah", "Nilai Valid": "Angka dalam rupiah (contoh: 1500000)"},
            {"Kolom": "Penghasilan Ibu", "Nilai Valid": "Angka dalam rupiah (contoh: 0)"},
            {"Kolom": "Jumlah Tanggungan", "Nilai Valid": "Format angka atau teks (contoh: 3, atau 3 Orang)"},
        ])
        valid_info.to_excel(writer, sheet_name="Panduan Pengisian", index=False)

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Template_KIPK_Upload.xlsx"},
    )
