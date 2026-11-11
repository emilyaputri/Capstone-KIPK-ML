"""
Preprocessing utilities for KIP-K data.
Handles validation, encoding, and data transformation.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

# Required columns for upload validation
REQUIRED_COLUMNS = [
    "NIM",
    "Nama_Mahasiswa",
    "Jenis_Kelamin",
    "Status_DTKS",
    "Status_P3KE",
    "Pekerjaan_Ayah",
    "Status_Ayah",
    "Penghasilan_Ayah",
    "Pekerjaan_Ibu",
    "Status_Ibu",
    "Penghasilan_Ibu",
    "Jumlah_Tanggungan",
]

# Column mapping from upload format to model format
COLUMN_MAPPING = {
    "NIM": "NIM",
    "Nama_Mahasiswa": "Nama_Mahasiswa",
    "Jenis_Kelamin": "Jenis Kelamin",
    "Kab_Kota_Sekolah": "Kab/Kota Sekolah",
    "Status_DTKS": "Status DTKS",
    "Status_P3KE": "Status P3KE",
    "Pekerjaan_Ayah": "Pekerjaan Ayah",
    "Status_Ayah": "Status Ayah",
    "Penghasilan_Ayah": "Penghasilan Ayah",
    "Pekerjaan_Ibu": "Pekerjaan Ibu",
    "Status_Ibu": "Status Ibu",
    "Penghasilan_Ibu": "Penghasilan Ibu",
    "Jumlah_Tanggungan": "Jumlah Tanggungan",
    "Pilihan_Prodi_1": "Pilihan Prodi 1",
    "Pilihan_Prodi_2": "Pilihan Prodi 2",
}

# Valid values for categorical columns
VALID_VALUES = {
    "Jenis Kelamin": ["L", "P"],
    "Status DTKS": ["Terdata", "Belum Terdata"],
    "Status P3KE": [
        "Belum Terdata",
        "Terdata: Desil 1",
        "Terdata: Desil 2",
        "Terdata: Desil 3",
        "Terdata: Desil 4",
        "Terdata: Desil 5",
        "Terdata: Desil 6",
        "Terdata: Desil 7",
    ],
    "Pekerjaan Ayah": [
        "Petani",
        "Nelayan",
        "Lainnya",
        "Wirausaha",
        "TIDAK BEKERJA",
        "PNS",
        "Peg. Swasta",
    ],
    "Status Ayah": ["Hidup", "Wafat", "Bercerai"],
    "Pekerjaan Ibu": [
        "Lainnya",
        "Petani",
        "TIDAK BEKERJA",
        "Wirausaha",
        "Peg. Swasta",
        "PNS",
    ],
    "Status Ibu": ["Hidup", "Wafat"],
}


def clean_raw_kipk_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans raw KIP-K data (e.g. 44 columns) to match the ML model format.
    Performs Data Selection, Cleaning, Transformation, Feature Engineering.
    """
    df = df.copy()

    # 0. FIX HEADERS IF EXPORT HAS A TITLE ROW
    # If the first row is actually the header (e.g. university raw export)
    if any("Unnamed" in str(c) for c in df.columns) or len([c for c in df.columns if "DATA SISWA" in str(c)]) > 0:
        if len(df) > 0 and any("Nama Siswa" in str(val) for val in df.iloc[0].values):
            df.columns = [str(c).strip() for c in df.iloc[0].values]
            df = df.iloc[1:].reset_index(drop=True)

    # 1. DATA SELECTION
    # If "Nama Siswa" exists, rename it to "Nama_Mahasiswa"
    if "Nama Siswa" in df.columns and "Nama_Mahasiswa" not in df.columns:
        df = df.rename(columns={"Nama Siswa": "Nama_Mahasiswa"})
    elif "Nama Lengkap" in df.columns and "Nama_Mahasiswa" not in df.columns:
        df = df.rename(columns={"Nama Lengkap": "Nama_Mahasiswa"})
    elif "Nama" in df.columns and "Nama_Mahasiswa" not in df.columns:
        df = df.rename(columns={"Nama": "Nama_Mahasiswa"})

    # Rename known raw columns to target columns if needed
    raw_col_map = {
        "Status DTKS": "Status DTKS",
        "Status P3KE": "Status P3KE",
        "Kab/Kota Sekolah": "Kab/Kota Sekolah",
        "Jenis Kelamin": "Jenis Kelamin",
        "Pekerjaan Ayah": "Pekerjaan Ayah",
        "Penghasilan Ayah": "Penghasilan Ayah",
        "Status Ayah": "Status Ayah",
        "Pekerjaan Ibu": "Pekerjaan Ibu",
        "Penghasilan Ibu": "Penghasilan Ibu",
        "Status Ibu": "Status Ibu",
        "Jumlah Tanggungan": "Jumlah Tanggungan",
        "Pilihan Prodi 1": "Pilihan Prodi 1",
        "Pilihan Prodi 2": "Pilihan Prodi 2",
        "Diterima/Tidak Diterima": "Diterima/Tidak Diterima"
    }

    # Apply renames for variations
    for raw_name, target in raw_col_map.items():
        if raw_name not in df.columns and raw_name.replace(" ", "_") in df.columns:
            df = df.rename(columns={raw_name.replace(" ", "_"): raw_name})

    # 2. DATA CLEANING
    # Standarisasi "Jumlah Tanggungan" (e.g., "03 Orang" -> "3 Orang")
    if "Jumlah Tanggungan" in df.columns:
        df["Jumlah Tanggungan"] = df["Jumlah Tanggungan"].astype(str).str.replace(r"^0+", "", regex=True)
        # Ensure it has "Orang" suffix if it's just a number
        df["Jumlah Tanggungan"] = df["Jumlah Tanggungan"].apply(
            lambda x: f"{x} Orang" if x.isdigit() else x
        )

    # 3. DATA TRANSFORMATION
    def transform_income(val):
        if pd.isna(val):
            return 0
        val_str = str(val).strip()
        if val_str in ["-", "Tidak Berpenghasilan", "", "0"]:
            return 0
        
        # If it's already a number, return it
        if val_str.isdigit():
            return int(val_str)

        # Mapping dict based on user requirements
        income_map = {
            "< Rp. 250.000": 125000,
            "Rp. 250.001 - Rp. 500.000": 375000,
            "Rp. 500.001 - Rp. 750.000": 625000,
            "Rp. 750.001 - Rp. 1.000.000": 875000,
            "Rp. 1.000.001 - Rp. 1.250.000": 1125000,
            "Rp. 1.250.001 - Rp. 1.500.000": 1375000,
            "Rp. 1.500.001 - Rp. 1.750.000": 1625000,
            "Rp. 1.750.001 - Rp. 2.000.000": 1875000,
            "Rp. 2.000.001 - Rp. 2.250.000": 2125000,
            "Rp. 2.250.001 - Rp. 2.500.000": 2375000,
            "Rp. 2.500.001 - Rp. 2.750.000": 2625000,
            "Rp. 2.750.001 - Rp. 3.000.000": 2875000
        }
        
        # Try exact match
        if val_str in income_map:
            return income_map[val_str]
            
        # Try cleaning the string for robust matching
        import re
        # Remove Rp, dots, spaces, formatting to just get the numbers
        nums = re.findall(r'\d+', val_str.replace('.', ''))
        if len(nums) == 2:
            return (int(nums[0]) + int(nums[1])) // 2
        elif len(nums) == 1 and "<" in val_str:
            return int(nums[0]) // 2
            
        return 0

    if "Penghasilan Ayah" in df.columns:
        df["Penghasilan Ayah"] = df["Penghasilan Ayah"].apply(transform_income)
    if "Penghasilan Ibu" in df.columns:
        df["Penghasilan Ibu"] = df["Penghasilan Ibu"].apply(transform_income)

    # 4. FEATURE ENGINEERING
    if "Penghasilan Ayah" in df.columns and "Penghasilan Ibu" in df.columns:
        df["Total Penghasilan"] = df["Penghasilan Ayah"] + df["Penghasilan Ibu"]

    # 5. DATA FORMATTING
    # Susun ulang kolom target
    target_columns = [
        "Nama_Mahasiswa", "Status DTKS", "Status P3KE", "Kab/Kota Sekolah", 
        "Jenis Kelamin", "Pekerjaan Ayah", "Penghasilan Ayah", "Status Ayah", 
        "Pekerjaan Ibu", "Penghasilan Ibu", "Status Ibu", "Total Penghasilan", 
        "Jumlah Tanggungan", "Pilihan Prodi 1", "Pilihan Prodi 2"
    ]
    if "Diterima/Tidak Diterima" in df.columns:
        target_columns.append("Diterima/Tidak Diterima")
        
    # Reorder if columns exist
    existing_target_cols = [col for col in target_columns if col in df.columns]
    other_cols = [col for col in df.columns if col not in existing_target_cols]
    
    # Prioritize our target columns first, then others
    df = df[existing_target_cols + other_cols]
    
    # Simpan CSV (lokal saja) — di serverless filesystem read-only, abaikan
    try:
        import os
        os.makedirs("data", exist_ok=True)
        df.to_csv("data/Cleaned_Dataset.csv", index=False, sep=";")
    except (OSError, PermissionError):
        pass

    return df


def validate_dataframe(df: pd.DataFrame, is_raw: bool = False) -> Tuple[bool, List[str], pd.DataFrame]:
    """
    Validate uploaded DataFrame for required columns and data types.
    Returns: (is_valid, errors, cleaned_df)
    """
    errors = []

    # Apply Auto-Cleaning and Transformation if requested
    if is_raw:
        df = clean_raw_kipk_data(df)

    # Normalize column names (replace spaces with underscores for flexibility)
    df.columns = [c.strip() for c in df.columns]

    # Auto-generate NIM and Nama_Mahasiswa if missing (for research datasets)
    if "NIM" not in df.columns and "NIM".replace("_", " ") not in df.columns:
        df["NIM"] = [f"MHS{str(i).zfill(4)}" for i in range(1, len(df) + 1)]
    if "Nama_Mahasiswa" not in df.columns and "Nama_Mahasiswa".replace("_", " ") not in df.columns:
        df["Nama_Mahasiswa"] = [f"Mahasiswa {i}" for i in range(1, len(df) + 1)]

    # Check required columns
    missing_cols = []
    for col in REQUIRED_COLUMNS:
        # Check both underscore and space variants
        if col not in df.columns and col.replace("_", " ") not in df.columns:
            missing_cols.append(col)

    if missing_cols:
        errors.append(f"Kolom yang hilang: {', '.join(missing_cols)}")
        return False, errors, df

    # Rename columns to model format
    rename_map = {}
    for col in df.columns:
        for upload_name, model_name in COLUMN_MAPPING.items():
            if col == upload_name or col == upload_name.replace("_", " "):
                rename_map[col] = model_name
                break

    df = df.rename(columns=rename_map)

    # Validate data types and values
    for col, valid_vals in VALID_VALUES.items():
        if col in df.columns:
            invalid = df[~df[col].astype(str).isin(valid_vals)]
            if len(invalid) > 0:
                invalid_vals = invalid[col].unique()[:5]
                errors.append(
                    f"Kolom '{col}' memiliki nilai tidak valid: {list(invalid_vals)}. "
                    f"Nilai yang dibolehkan: {valid_vals}"
                )

    # Validate numeric columns
    for col in ["Penghasilan Ayah", "Penghasilan Ibu"]:
        if col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
            except Exception:
                errors.append(f"Kolom '{col}' harus berisi angka")

    # Handle Jumlah Tanggungan (might be "X Orang" format)
    if "Jumlah Tanggungan" in df.columns:
        df["Jumlah Tanggungan"] = (
            df["Jumlah Tanggungan"]
            .astype(str)
            .str.extract(r"(\d+)")
            .fillna(0)
            .astype(float)
        )

    # Calculate Total Penghasilan
    if "Penghasilan Ayah" in df.columns and "Penghasilan Ibu" in df.columns:
        df["Total Penghasilan"] = df["Penghasilan Ayah"].fillna(0) + df["Penghasilan Ibu"].fillna(0)

    is_valid = len(errors) == 0
    return is_valid, errors, df


def prepare_for_prediction(df: pd.DataFrame, label_encoders: Dict) -> pd.DataFrame:
    """
    Prepare DataFrame for model prediction by encoding categorical features.
    """
    feature_cols = [
        "Status DTKS",
        "Status P3KE",
        "Jenis Kelamin",
        "Pekerjaan Ayah",
        "Status Ayah",
        "Pekerjaan Ibu",
        "Status Ibu",
        "Penghasilan Ayah",
        "Penghasilan Ibu",
        "Total Penghasilan",
        "Jumlah Tanggungan",
    ]

    df_encoded = df.copy()

    # Apply label encoding
    for col, le in label_encoders.items():
        if col in df_encoded.columns:
            # Handle unseen labels by mapping to closest known label
            known_classes = set(le.classes_)
            df_encoded[col] = df_encoded[col].apply(
                lambda x: x if x in known_classes else le.classes_[0]
            )
            df_encoded[col] = le.transform(df_encoded[col].astype(str))

    return df_encoded[feature_cols]


def generate_template_data() -> pd.DataFrame:
    """Generate an empty template DataFrame for admin to fill."""
    template_cols = [
        "NIM",
        "Nama Mahasiswa",
        "Jenis Kelamin",
        "Kab/Kota Sekolah",
        "Status DTKS",
        "Status P3KE",
        "Pekerjaan Ayah",
        "Status Ayah",
        "Penghasilan Ayah",
        "Pekerjaan Ibu",
        "Status Ibu",
        "Penghasilan Ibu",
        "Jumlah Tanggungan",
        "Pilihan Prodi 1",
        "Pilihan Prodi 2",
    ]

    # Create template with one sample row
    sample_data = {
        "NIM": ["2024001"],
        "Nama Mahasiswa": ["Contoh Mahasiswa"],
        "Jenis Kelamin": ["P"],
        "Kab/Kota Sekolah": ["Kab. Agam"],
        "Status DTKS": ["Terdata"],
        "Status P3KE": ["Terdata: Desil 1"],
        "Pekerjaan Ayah": ["Petani"],
        "Status Ayah": ["Hidup"],
        "Penghasilan Ayah": [1500000],
        "Pekerjaan Ibu": ["TIDAK BEKERJA"],
        "Status Ibu": ["Hidup"],
        "Penghasilan Ibu": [0],
        "Jumlah Tanggungan": ["3 Orang"],
        "Pilihan Prodi 1": ["S1 PGSD"],
        "Pilihan Prodi 2": ["S1 Gizi"],
    }

    return pd.DataFrame(sample_data, columns=template_cols)
