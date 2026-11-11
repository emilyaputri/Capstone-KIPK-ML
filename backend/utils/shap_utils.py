"""
SHAP utilities for explainable predictions.
Computes SHAP values and generates human-readable explanations.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any


# Human-readable feature names (Indonesian)
FEATURE_LABELS = {
    "Status DTKS": "Status DTKS (Data Terpadu Kesejahteraan Sosial)",
    "Status P3KE": "Status P3KE (Penghapusan Kemiskinan Ekstrem)",
    "Jenis Kelamin": "Jenis Kelamin",
    "Pekerjaan Ayah": "Pekerjaan Ayah",
    "Status Ayah": "Status Ayah",
    "Pekerjaan Ibu": "Pekerjaan Ibu",
    "Status Ibu": "Status Ibu",
    "Penghasilan Ayah": "Penghasilan Ayah (Rp)",
    "Penghasilan Ibu": "Penghasilan Ibu (Rp)",
    "Total Penghasilan": "Total Penghasilan Orang Tua (Rp)",
    "Jumlah Tanggungan": "Jumlah Tanggungan Keluarga",
}


def compute_shap_values(model, X: pd.DataFrame) -> np.ndarray:
    """
    Compute SHAP values for all predictions using TreeSHAP.
    Returns SHAP values array of shape (n_samples, n_features).

    Primary path uses XGBoost's built-in TreeSHAP (pred_contribs=True), which
    implements the same algorithm as shap.TreeExplainer but without the
    shap<->xgboost version-coupled raw-model loader (shap 0.49.1 cannot parse
    the vector base_score format written by xgboost >= 3.x).
    Falls back to shap.TreeExplainer for non-XGBoost models or older xgboost.
    """
    # --- Path 1: native XGBoost TreeSHAP ---
    try:
        import xgboost as xgb

        booster = model.get_booster() if hasattr(model, "get_booster") else model
        dmat = xgb.DMatrix(X)
        # pred_contribs returns (n_samples, n_features + 1):
        # last column is the expected-value (bias) term, not a feature.
        contribs = np.asarray(booster.predict(dmat, pred_contribs=True))
        if contribs.ndim == 2 and contribs.shape[1] == X.shape[1] + 1:
            return contribs[:, :-1]
    except Exception:
        pass  # fall through to shap.TreeExplainer

    # --- Path 2: shap.TreeExplainer (fallback lokal, butuh package `shap`) ---
    import shap

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    # For binary classification, shap_values might be a list [neg_class, pos_class]
    if isinstance(shap_values, list):
        shap_values = shap_values[1]  # Use positive class SHAP values

    return shap_values


def get_individual_shap(
    shap_values: np.ndarray,
    feature_names: List[str],
    index: int,
    label_encoders: Dict = None,
    original_values: pd.Series = None,
) -> List[Dict[str, Any]]:
    """
    Get SHAP breakdown for a single individual.
    Returns list of {feature, value, shap_value, direction, label}.
    """
    individual_shap = shap_values[index]

    factors = []
    for i, (feat_name, shap_val) in enumerate(zip(feature_names, individual_shap)):
        original_val = None
        if original_values is not None and feat_name in original_values.index:
            original_val = original_values[feat_name]

        # Determine direction
        direction = "positif" if shap_val > 0 else "negatif" if shap_val < 0 else "netral"

        factors.append({
            "feature": feat_name,
            "label": FEATURE_LABELS.get(feat_name, feat_name),
            "shap_value": float(shap_val),
            "direction": direction,
            "original_value": str(original_val) if original_val is not None else None,
            "abs_shap": abs(float(shap_val)),
        })

    # Sort by absolute SHAP value (most important first)
    factors.sort(key=lambda x: x["abs_shap"], reverse=True)

    return factors


def generate_narrative(factors: List[Dict], name: str = "Mahasiswa") -> str:
    """
    Generate a human-readable narrative explanation from SHAP factors.
    """
    positive = [f for f in factors if f["direction"] == "positif"]
    negative = [f for f in factors if f["direction"] == "negatif"]

    narrative = f"Analisis kelayakan {name}:\n\n"

    if positive:
        narrative += "Faktor PENDUKUNG kelayakan:\n"
        for f in positive[:3]:
            narrative += (
                f"  • {f['label']}: berkontribusi positif "
                f"(+{f['shap_value']:.4f})\n"
            )

    if negative:
        narrative += "\nFaktor PENGURANG kelayakan:\n"
        for f in negative[:3]:
            narrative += (
                f"  • {f['label']}: berkontribusi negatif "
                f"({f['shap_value']:.4f})\n"
            )

    return narrative


def get_global_feature_importance(
    shap_values: np.ndarray, feature_names: List[str]
) -> List[Dict[str, Any]]:
    """
    Compute global feature importance from SHAP values.
    Returns sorted list of {feature, label, mean_abs_shap}.
    """
    mean_abs_shap = np.abs(shap_values).mean(axis=0)

    importance = []
    for feat_name, mean_val in zip(feature_names, mean_abs_shap):
        importance.append({
            "feature": feat_name,
            "label": FEATURE_LABELS.get(feat_name, feat_name),
            "mean_abs_shap": float(mean_val),
        })

    importance.sort(key=lambda x: x["mean_abs_shap"], reverse=True)
    return importance
