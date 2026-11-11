"""
Upload router - handles file upload, validation, and template download.
"""

import os
import uuid
import tempfile
from datetime import datetime
from io import BytesIO

import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.preprocess import validate_dataframe, generate_template_data

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("/validate")
async def validate_upload(file: UploadFile = File(...), is_raw: str = Form("false")):
    """
    Upload and validate an Excel file.
    Returns validation status and data preview.
    """
    if not file.filename.endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(
            status_code=400,
            detail="Format file tidak didukung. Gunakan .xlsx, .xls, atau .csv",
        )

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
        raise HTTPException(
            status_code=400,
            detail=f"Gagal membaca file: {str(e)}",
        )

    # Validate
    is_raw_bool = is_raw.lower() == "true"
    is_valid, errors, cleaned_df = validate_dataframe(df, is_raw=is_raw_bool)

    # Generate session ID
    session_id = str(uuid.uuid4())[:8]

    # Preview data (first 10 rows)
    import math
    preview_records = cleaned_df.head(10).to_dict(orient="records")
    preview = []
    for row in preview_records:
        clean_row = {}
        for k, v in row.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                clean_row[k] = None
            else:
                clean_row[k] = v
        preview.append(clean_row)

    return {
        "session_id": session_id,
        "is_valid": is_valid,
        "errors": errors,
        "total_rows": len(cleaned_df),
        "columns": list(cleaned_df.columns),
        "preview": preview,
        "filename": file.filename,
        "uploaded_at": datetime.now().isoformat(),
    }
