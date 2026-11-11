"""
Training script for XGBoost + SMOTE model for KIP-K eligibility prediction.
Based on the thesis: "Fair and Explainable Ensemble ML for Student Financial Aid Eligibility"

Tuned version with better hyperparameters to improve Recall and ROC-AUC.
"""

import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    classification_report,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)
from imblearn.over_sampling import SMOTE
import xgboost as xgb
import joblib

# Path configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, "..", "..", "data", "KIPK_2024_training.xlsx")
MODEL_OUTPUT = os.path.join(SCRIPT_DIR, "xgboost_kipk.pkl")
ENCODERS_OUTPUT = os.path.join(SCRIPT_DIR, "label_encoders.pkl")
FEATURE_NAMES_OUTPUT = os.path.join(SCRIPT_DIR, "feature_names.pkl")


def load_and_preprocess(filepath):
    """Load dataset and preprocess for training."""
    print(f"[1/5] Loading dataset from: {filepath}")
    df = pd.read_excel(filepath)
    print(f"  Dataset shape: {df.shape}")

    # Clean Jumlah Tanggungan: extract number from "X Orang"
    df["Jumlah Tanggungan"] = (
        df["Jumlah Tanggungan"].astype(str).str.extract(r"(\d+)").astype(int)
    )

    # Target variable
    target_col = "Diterima/Tidak Diterima"
    df["target"] = (df[target_col] == "Diterima").astype(int)
    print(f"  Target distribution:\n{df['target'].value_counts()}")

    # Features used for model (matching thesis)
    categorical_features = [
        "Status DTKS",
        "Status P3KE",
        "Jenis Kelamin",
        "Pekerjaan Ayah",
        "Status Ayah",
        "Pekerjaan Ibu",
        "Status Ibu",
    ]

    numerical_features = [
        "Penghasilan Ayah",
        "Penghasilan Ibu",
        "Total Penghasilan",
        "Jumlah Tanggungan",
    ]

    feature_cols = categorical_features + numerical_features

    # Label encoding for categorical features
    print("\n[2/5] Encoding categorical features...")
    label_encoders = {}
    for col in categorical_features:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        label_encoders[col] = le
        print(f"  {col}: {list(le.classes_)}")

    X = df[feature_cols].copy()
    y = df["target"].copy()

    return X, y, label_encoders, feature_cols


def train_model(X, y):
    """Train XGBoost with SMOTE - tuned for better recall."""
    print("\n[3/5] Splitting data and applying SMOTE...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"  Train shape: {X_train.shape}, Test shape: {X_test.shape}")

    # Apply SMOTE on training data only
    smote = SMOTE(random_state=42, k_neighbors=3)
    X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
    print(f"  After SMOTE - Train shape: {X_train_res.shape}")

    # Calculate scale_pos_weight for additional class balancing
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_weight = neg_count / pos_count

    # Train XGBoost with tuned hyperparameters for better recall
    print("\n[4/5] Training XGBoost model (tuned)...")
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        min_child_weight=2,
        gamma=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_weight,
        random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_train_res, y_train_res)

    # Evaluate
    print("\n[5/5] Evaluating model...")
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    # Use a lower threshold to improve recall
    threshold = 0.45
    y_pred = (y_pred_proba >= threshold).astype(int)

    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba)

    print(f"\n{'='*50}")
    print(f"MODEL EVALUATION RESULTS")
    print(f"{'='*50}")
    print(f"  Threshold: {threshold}")
    print(f"  Recall:   {recall:.4f} (target >= 0.38)")
    print(f"  F1-Score: {f1:.4f}")
    print(f"  ROC-AUC:  {roc_auc:.4f} (target >= 0.62)")
    print(f"\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Tidak Diterima", "Diterima"]))
    print(f"Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Feature importance
    importance = model.feature_importances_
    feature_imp = sorted(
        zip(X.columns, importance), key=lambda x: x[1], reverse=True
    )
    print(f"\nFeature Importance (Top 5):")
    for feat, imp in feature_imp[:5]:
        print(f"  {feat}: {imp:.4f}")

    return model, X_test, y_test


def main():
    X, y, label_encoders, feature_names = load_and_preprocess(DATA_PATH)
    model, X_test, y_test = train_model(X, y)

    print(f"\nSaving model to: {MODEL_OUTPUT}")
    joblib.dump(model, MODEL_OUTPUT)

    print(f"Saving label encoders to: {ENCODERS_OUTPUT}")
    joblib.dump(label_encoders, ENCODERS_OUTPUT)

    print(f"Saving feature names to: {FEATURE_NAMES_OUTPUT}")
    joblib.dump(feature_names, FEATURE_NAMES_OUTPUT)

    print(f"\n{'='*50}")
    print("Training complete! Model files saved.")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
