# Plan Deployment KIPK-ML ke Vercel

> Dokumen ini berisi analisis kesiapan, perubahan kode yang diperlukan, dan
> langkah deployment terukur berdasarkan audit codebase + limit Vercel (Nov 2026).

---

## 1. Arsitektur Target

```
                        ┌─────────────────────────────────────┐
                        │            VERCEL                   │
                        │                                     │
  User ──HTTPS──►       │  Project 1: kipk-frontend (static)  │
                        │    Root Directory: frontend/        │
                        │    Vite build → dist/ → CDN         │
                        │         │                            │
                        │         │ VITE_API_URL (env)        │
                        │         ▼                            │
                        │  Project 2: kipk-api (Python)       │
                        │    Root Directory: backend/         │
                        │    FastAPI → Vercel Function        │
                        │    entrypoint: main.py (app)        │
                        │         │                            │
                        └─────────┼───────────────────────────┘
                                  │ DATABASE_URL (env)
                                  ▼
                        ┌──────────────────┐
                        │ Neon (Postgres)  │  ← menggantikan SQLite
                        │ free tier        │
                        └──────────────────┘
```

**2 Vercel project dari 1 repository** (monorepo) — pola paling stabil.
Alternatif single-domain: fitur *Vercel Services* (lihat §10).

---

## 2. Hasil Audit: Limit Vercel vs Kondisi Nyata

### 2.1 Limit Vercel (Fluid Compute, per Nov 2026)

| Limit | Hobby (free) | Kondisi KIPK-ML |
|---|---|---|
| Bundle function (Python) | **500 MB** uncompressed (5 GB dgn Large Functions beta) | ⚠️ Terukur ~795 MB tanpa optimasi → **GAGAL**; ~300 MB setelah optimasi → ✅ |
| Durasi request | 300 s default = max | ✅ prediksi 829 baris = **2,4 s** (warm) |
| Memori | 2 GB / 1 vCPU | ✅ prediksi + SHAP jauh di bawah 2 GB |
| Body request (upload) | **4,5 MB** | ✅ 829 baris = 68 KB → ~54.000 baris masih aman |
| Body response | **4,5 MB** (streaming dikecualikan) | ⚠️ 829 baris = **1,89 MB** → batas ~**1.975 baris**/respons |
| Build time | 45 menit | ✅ install deps ~3–5 menit |
| Deployments | 100/hari | ✅ |
| Active CPU | 4 CPU-jam/bulan | ✅ ribuan prediksi/bulan |
| Region | 1 region (default `iad1`) | ⚠️ pindah ke **`sin1` (Singapore)** untuk Indonesia |

### 2.2 Pengukuran Bundle (site-packages terpasang)

| Paket | Ukuran | Status di Vercel |
|---|---|---|
| xgboost (full, termasuk dependensi `nvidia-nccl-cu12` di Linux) | 138 MB + **~250 MB NCCL** | ❌ GANTI → `xgboost-cpu==3.2.0` = **5,3 MB wheel (~20 MB)** |
| scipy | 111 MB | ✅ wajib (dependensi xgboost) |
| llvmlite + numba + shap | **139 MB** | ❌ HAPUS — SHAP kini memakai TreeSHAP native XGBoost (sudah dipatch) |
| pandas | 52 MB | ✅ wajib |
| numpy | 28 MB | ✅ wajib |
| scikit-learn | 37 MB | ✅ wajib (`LabelEncoder` di pickle) |
| fastapi, sqlalchemy, openpyxl, dll | ~40 MB | ✅ wajib |
| imbalanced-learn | ~10 MB | ❌ HAPUS dari runtime (hanya untuk `train.py`) |
| Model `.pkl` | 0,3 MB | ✅ wajib |
| `backend/venv/` (jika ikut terbundel) | 487 MB | ❌ **wajib di-`excludeFiles`** |
| `backend/kipk_ml.db` | 10 MB | ❌ wajib di-exclude |
| **TOTAL setelah optimasi** | **~300 MB** | ✅ < 500 MB |
| **TOTAL tanpa optimasi** | **~795 MB** | ❌ build gagal |

---

## 3. Bloker Kritis (wajib diselesaikan)

| # | Bloker | Dampak | Solusi |
|---|---|---|---|
| B1 | **Filesystem read-only** (kecuali `/tmp`) → SQLite `kipk_ml.db` gagal ditulis | 500 saat startup/predict, data hilang | **Pindah ke Neon Postgres** (SQLAlchemy) |
| B2 | `clean_raw_kipk_data()` menulis `data/Cleaned_Dataset.csv` | 500 saat upload mode raw | Hapus/bungkus dengan try-except |
| B3 | `import shap` di top-level `shap_utils.py` (139 MB) | bundle meledak / import error jika shap dihapus | Jadikan **import lazy** di fallback saja |
| B4 | `api.js` hardcode `http://localhost:8000` | frontend produksi tidak bisa memanggil API | Env `VITE_API_URL` |
| B5 | `History.jsx` buka `http://localhost:8000/export/...` | export Excel mati di produksi | Pakai base URL dari env |
| B6 | Secret hardcode (`SECRET_KEY`, password admin) | keamanan | Env variables |
| B7 | File model di-load via path dinamis (`os.path.join(...)`) | Vercel tidak bisa trace → pkl tidak ikut terbundel | `includeFiles: "model/*.pkl"` di `vercel.json` |
| B8 | Pickle dilatih dengan **sklearn 1.8.0 + xgboost 3.2.0** | error/load-unsupported di versi lain | Pin versi identik di requirements |
| B9 | Response `/predict/batch` 1,89 MB / 829 baris | 413 di >~1.975 baris | Lihat §7 (opsional untuk MVP) |

---

## 4. Fase 1 — Perubahan Kode Backend

### 4.1 `backend/database.py` → dukung SQLite (lokal) & Postgres (Vercel)

```python
# Ganti baris pembuatan engine:
def _resolve_database_url() -> str:
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if url:
        # Vercel/Neon memberi postgres:// → SQLAlchemy 2 butuh skema driver
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        return url
    # fallback lokal tetap SQLite
    return f"sqlite:///{os.path.join(DB_DIR, 'kipk_ml.db')}"

DATABASE_URL = _resolve_database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    echo=False,
)
```

> `create_all()` saat startup otomatis membuat tabel di Neon (aman di-race).

### 4.2 `backend/utils/preprocess.py` → jangan tulis file

```python
# Hapus atau bungkus (sekitar baris 207-209):
#   os.makedirs("data", exist_ok=True)
#   df.to_csv("data/Cleaned_Dataset.csv", index=False, sep=";")
```

### 4.3 `backend/utils/shap_utils.py` → import shap lazy

```python
# Hapus `import shap` di top-level; pindahkan ke dalam Path 2:
    # --- Path 2: shap.TreeExplainer (fallback, opsional) ---
    try:
        import shap
    except ImportError:
        raise RuntimeError(
            "SHAP fallback tidak tersedia; pastikan model XGBoost agar "
            "TreeSHAP native dipakai."
        )
    explainer = shap.TreeExplainer(model)
    ...
```

### 4.4 `backend/main.py` → konfigurasi via env

```python
SECRET_KEY = os.environ.get("SECRET_KEY", "kipk-ml-secret-key-2024-admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")  # hash saat startup
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4.5 Requirements

**`backend/requirements.txt`** (runtime — dipakai Vercel):

```text
fastapi
uvicorn
pandas
openpyxl
xgboost-cpu==3.2.0        # 5,3 MB vs 131 MB + NCCL 250 MB
scikit-learn==1.8.0       # cocokkan versi pickle
joblib
python-multipart
sqlalchemy
psycopg[binary]           # driver Neon Postgres
```

**`backend/requirements-train.txt`** (lokal saja, tidak di-deploy):

```text
-r requirements.txt
imbalanced-learn
shap                      # opsional; fallback TreeExplainer
```

> Catatan: `uvicorn` tetap dipertahankan agar `RUN.ps1`/dev lokal tetap jalan.

---

## 5. Fase 2 — Perubahan Kode Frontend

### 5.1 `frontend/src/services/api.js`

```javascript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

### 5.2 `frontend/src/pages/History.jsx` (baris ~42)

```javascript
// Sebelum: window.open(`http://localhost:8000/export/${sessionId}/excel`, '_blank');
import api from '../services/api';
// Sesudah: buka lewat base URL yang sama
window.open(`${api.defaults.baseURL}/export/${sessionId}/excel`, '_blank');
```

### 5.3 Environment variables (build-time!)

| Name | Nilai (contoh) | Untuk |
|---|---|---|
| `VITE_API_URL` | `https://kipk-api-xxxx.vercel.app` | build frontend |
| `SECRET_KEY` | string acak 32+ char | backend |
| `ADMIN_PASSWORD` | password admin baru | backend |
| `DATABASE_URL` / `POSTGRES_URL` | dari integrasi Neon | backend |
| `ALLOWED_ORIGINS` | `https://kipk-frontend-xxxx.vercel.app` | backend CORS |

> ⚠️ `VITE_API_URL` **harus ada sebelum build** (di-inline saat kompilasi Vite).

---

## 6. Fase 3 — Konfigurasi Vercel

### 6.1 `backend/vercel.json`

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "main.py": {
      "maxDuration": 120,
      "includeFiles": "model/*.pkl",
      "excludeFiles": "{venv/**,__pycache__/**,data/**,*.db,*.csv,scripts/**,tests/**}"
    }
  }
}
```

- **`includeFiles: model/*.pkl`** → memaksa 3 file model ikut terbundel (B7).
- **`excludeFiles`** → mencegah `venv/` (487 MB), DB, dan CSV ikut terbundel.
- **`maxDuration: 120`** → ruang untuk cold start + prediksi besar (max Hobby = 300).

### 6.2 `backend/.python-version`

```text
3.12
```

(Vercel mendukung 3.12/3.13/3.14; pickle sklearn 1.8.0 & xgboost 3.2.0 kompatibel.)

### 6.3 Setting project di dashboard

| Setting | kipk-frontend | kipk-api |
|---|---|---|
| Root Directory | `frontend` | `backend` |
| Framework Preset | Vite (auto) | Python (auto-deteksi `fastapi` di requirements) |
| Build Command | `npm run build` (auto) | — (auto) |
| Output | `dist/` (auto) | — |
| Region | — | **Singapore (`sin1`)** |
| Env vars | `VITE_API_URL` | lihat §5.3 |

### 6.4 Entrypoint

Vercel memuat `main.py` → variabel `app` ✅ (sudah sesuai konvensi Vercel:
file `main.py` di root project berisi objek `app`).

---

## 7. Fase 4 — Batas Payload (opsional, rekomendasi)

**Masalah:** respons `/predict/batch` ~2,28 KB/baris → limit 4,5 MB ≈ **1.975 baris**.

**Untuk MVP (data KIPK ≤ ~1.500 baris):** cukup dokumentasikan batas ini.

**Jika perlu >2.000 baris**, pilih salah satu:

1. **Slim response (termudah, ~60% lebih kecil):**
   buang `narrative` + `data_asli` dari respons list — cukup kirim `rank, nim,
   nama, skor, kategori, prediksi, keputusan_final, dalam_kuota`; detail SHAP
   & narasi sudah tersedia di endpoint `/predict/result/{sid}/{nim}`.
2. **Pagination:** `/predict/batch` hanya mengembalikan `session_id + stats`;
   frontend memanggil `/predict/result/{sid}?offset=0&limit=200` bertahap.
3. **Streaming:** respons stream dikecualikan dari limit 4,5 MB (lebih kompleks).

**Upload:** 4,5 MB ≈ 54.000 baris Excel — sangat cukup untuk kasus KIPK.
Untuk file raksasa (di luar kasus ini): Vercel Blob *client upload*.

---

## 8. Fase 5 — Migrasi Data Lama (opsional)

Database lokal punya 2 sesi prediksi lama (`b7c89479`, `a1d384e8`).
Pilih salah satu:

- **A (termudah):** mulai dari kosong, upload ulang file sumber.
- **B:** skrip migrasi SQLite → Neon — iterasi tabel
  `selection_sessions`, `student_predictions`, `activity_logs` dengan session
  SQLite lokal, `insert` ke engine baru dari `DATABASE_URL`. (~30 baris, letakkan
  di `backend/scripts/migrate_sqlite_to_pg.py`, jalankan sekali dari lokal).

---

## 9. Fase 6 — Langkah Deployment

```bash
# 0. Prasyarat
npm i -g vercel          # Vercel CLI
vercel login

# 1. Pastikan perubahan Fase 1–2 sudah di-commit & push ke GitHub

# 2. Deploy frontend
cd frontend
vercel --prod            # → set VITE_API_URL dulu di dashboard, lalu redeploy

# 3. Deploy backend
cd ../backend
vercel --prod            # → set env vars (§5.3) sebelumnya, pilih region sin1

# 4. Integrasi database
#    Dashboard → kipk-api → Storage → Neon (Postgres) → attach
#    (env POSTGRES_URL terisi otomatis)

# 5. Verifikasi
curl https://kipk-api-xxxx.vercel.app/
curl -X POST https://kipk-api-xxxx.vercel.app/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"<ADMIN_PASSWORD>"}'
```

### Checklist smoke test (setelah deploy)

- [ ] `GET /` → 200 JSON (versi + docs)
- [ ] `POST /auth/login` → token
- [ ] `GET /dashboard/stats` → daftar sesi
- [ ] `GET /export/template` → unduh template
- [ ] `POST /upload/validate` → valid
- [ ] `POST /predict/batch` (file training) → 200, `shap_factors` terisi, < 60 dtk
- [ ] `GET /predict/result/{id}` → ukuran < 4,5 MB
- [ ] `POST .../kuota`, `PUT .../override`, `GET /activity-log`
- [ ] `GET /export/{id}/excel` → unduhan berhasil
- [ ] Frontend: login → dashboard → upload → ranking → detail → riwayat → logout
- [ ] DevTools: tidak ada panggilan ke `localhost:8000`
- [ ] Restart project (redeploy) → data sesi **masih ada** (bukti DB eksternal OK)

---

## 10. Alternatif & Keputusan

| Keputusan | Pilihan | Alasan |
|---|---|---|
| Database | **Neon (Vercel Postgres)** ← rekomendasi | integrasi first-party, SQLite tidak bisa di serverless |
| | Turso (libSQL) | jika ingin perubahan kode minimum (tetap dialect SQLite), tapi bukan integrasi Vercel native |
| Struktur | **2 project Vercel** ← rekomendasi | pola teruji, build terpisah, mudah debug |
| | 1 project + Vercel Services | dapat 1 domain bersama, fitur lebih baru |
| | Frontend Vercel + backend Railway/Render | jika tidak mau serverless (SQLite tetap dipakai, tanpa cold start) — di luar scope "deployment via Vercel" |
| xgboost | **`xgboost-cpu==3.2.0`** | 20 MB vs ~390 MB; model memang dilatih di CPU |
| SHAP | **TreeSHAP native XGBoost** (sudah dipatch) | hemat 139 MB; algoritma identik |

### Catatan plan Hobby

- Plan Hobby = **non-commercial personal use**. Jika ini untuk institusi/produksi
  → gunakan **Pro** (durasi 800 s, multi-region, support).
- Cold start estimasi **+3–8 detik** (import scipy/xgboost + load model) — normal
  untuk ML serverless; `maxDuration: 120` memberi ruang aman.

---

## 11. Estimasi Effort

| Fase | Isi | Estimasi |
|---|---|---|
| 1 | Perubahan backend (DB env, lazy shap, hapus CSV write, env secret, requirements) | 1–2 jam |
| 2 | Perubahan frontend (`VITE_API_URL`, History export) | 30 menit |
| 3 | Konfigurasi Vercel (2 project, env, region, vercel.json) | 30–45 menit |
| 4 | Payload (opsional, hanya jika >1.500 baris) | 1 jam |
| 5 | Migrasi data (opsional) | 30 menit |
| 6 | Deploy + smoke test | 45–60 menit |
| **Total** | | **~4–6 jam** |
