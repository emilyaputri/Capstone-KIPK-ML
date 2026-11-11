# KIPK-ML System

Sistem Pendukung Keputusan Seleksi KIP Kuliah (KIP-K) berbasis Machine Learning.
Admin dashboard untuk upload data pendaftar, prediksi kelayakan (XGBoost + SHAP),
ranking, penetapan kuota, override keputusan, dan export Excel.

## Arsitektur

```
kipk-ml-system/
├── backend/                 FastAPI (Python 3.10)
│   ├── main.py              Entry point: auth (JWT sederhana), CORS, dashboard stats
│   ├── database.py          SQLAlchemy + SQLite (kipk_ml.db)
│   ├── routers/
│   │   ├── upload.py        POST /upload/validate      - validasi Excel/CSV
│   │   ├── predict.py       POST /predict/batch        - prediksi batch + SHAP
│   │   │                    GET  /predict/sessions
│   │   │                    GET  /predict/result/{sid}
│   │   │                    GET  /predict/result/{sid}/{nim}
│   │   │                    POST /predict/result/{sid}/kuota
│   │   │                    PUT  /predict/result/{sid}/{nim}/override
│   │   │                    DELETE /predict/session/{sid}
│   │   └── export.py        GET /export/{sid}/excel, GET /export/template
│   ├── utils/
│   │   ├── preprocess.py    Validasi kolom, encoding, cleaning data raw
│   │   └── shap_utils.py    TreeExplainer + narasi Indonesia
│   ├── model/
│   │   ├── train.py         Training XGBoost + SMOTE
│   │   ├── xgboost_kipk.pkl Model terlatih
│   │   ├── label_encoders.pkl
│   │   └── feature_names.pkl
│   └── requirements.txt
│
├── frontend/                React 19 + Vite + Tailwind 4
│   └── src/
│       ├── pages/           Login, Dashboard, Upload, History, Ranking, Detail
│       ├── components/      Layout (sidebar)
│       └── services/api.js  Axios -> http://localhost:8000
│
├── data/
│   └── KIPK_2024_training.xlsx   Dataset training
│
└── RUN.ps1                  Script menjalankan backend + frontend sekaligus
```

## Prasyarat

- Python 3.10+
- Node.js 18+ (diketahui jalan di v24)
- Windows PowerShell (untuk `RUN.ps1`), atau shell biasa

## Setup

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Frontend

```powershell
cd frontend
npm install
```

## Menjalankan

### Cara cepat (keduanya sekaligus)

```powershell
.\RUN.ps1
```

### Manual - dua terminal

Terminal 1 (backend, port 8000):
```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2 (frontend, port 5173):
```powershell
cd frontend
npm run dev
```

## Login

| Field    | Value     |
|----------|-----------|
| Username | `admin`   |
| Password | `admin123`|

## URL

- Frontend: http://localhost:5173
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

## Alur Kerja Aplikasi

1. **Login** sebagai admin.
2. **Upload Data** — unggah Excel/CSV pendaftar.
   - Mode *Raw* membersihkan kolom otomatis (rename, normalisasi income).
   - Mode non-raw memakai format template (`GET /export/template`).
3. **Prediksi** — model XGBoost menghitung probabilitas kelayakan.
   - Threshold `0.45` untuk prediksi Diterima/Tidak Diterima.
   - Kategori: Sangat Layak (≥75), Layak (≥50), Kurang Layak (≥25), Tidak Layak (<25).
   - SHAP TreeExplainer memberi faktor penjelas per mahasiswa.
4. **Ranking** — daftar peringkat, set kuota (garis cutoff), export Excel.
5. **Detail** — lihat SHAP individual, override keputusan admin dengan alasan.
6. **Riwayat** — daftar sesi prediksi, hapus sesi.

## Model

- Algorithm: XGBoost Classifier (n_estimators=200, max_depth=4, lr=0.05)
- Imbalance handling: SMOTE + `scale_pos_weight`
- 11 fitur: 7 kategorikal (label-encoded) + 4 numerik
- Training data: `data/KIPK_2024_training.xlsx`

Retraining (opsional):
```powershell
cd backend
.\venv\Scripts\python.exe model\train.py
```

## Storage

- SQLite: `backend/kipk_ml.db`
- Tabel: `selection_sessions`, `student_predictions`, `activity_logs`

## Troubleshooting

### SHAP `ValueError: could not convert string to float: '[7.424657E-1]'`

**Gejala:** `POST /predict/batch` mengembalikan HTTP 500 dengan error di
`shap.TreeExplainer` → `XGBTreeModelLoader`.

**Penyebab:** Bug kompatibilitas upstream antara `shap` dan `xgboost >= 3.x`.
XGBoost 3.x menyimpan `base_score` sebagai vektor (`[7.424657E-1]`), sedangkan
loader SHAP 0.49.1 mengharapkan float tunggal. Ini terjadi bahkan pada model
yang baru dilatih — bukan karena file model.

**Penyelesaian (sudah diterapkan):** `backend/utils/shap_utils.py` →
`compute_shap_values()` kini memakai TreeSHAP native bawaan XGBoost
(`booster.predict(DMatrix, pred_contribs=True)`), yang algoritmanya identik
dengan `shap.TreeExplainer` (additivity error ~1e-6). `shap.TreeExplainer`
tetap dipertahankan sebagai fallback untuk model non-XGBoost.

### Warning `InconsistentVersionWarning` saat startup

Model di-pickle dengan scikit-learn 1.8.0, environment memakai 1.7.2.
Hanya warning — `LabelEncoder` kompatibel dan prediksi tetap valid.
Untuk menghilangkan: `pip install scikit-learn==1.8.0` (opsional).

### Health check `/health` mengembalikan 404

Endpoint `/health` tidak didefinisikan di API ini. Gunakan `GET /` atau
`GET /docs` untuk memverifikasi server hidup.
# Capstone-KIPK-ML
