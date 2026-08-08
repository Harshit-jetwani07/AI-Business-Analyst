import numpy as np
import pandas as pd


def evaluate_dataset_quality(df: pd.DataFrame) -> dict:
    rows, cols = df.shape
    total_cells = max(rows * cols, 1)
    missing_cells = int(df.isnull().sum().sum())
    duplicate_rows = int(df.duplicated().sum())
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    date_cols = df.select_dtypes(include=["datetime", "datetime64"]).columns.tolist()

    missing_pct = round((missing_cells / total_cells) * 100, 2)
    duplicate_pct = round((duplicate_rows / max(rows, 1)) * 100, 2)

    score = 100
    score -= min(35, missing_pct * 1.2)
    score -= min(20, duplicate_pct * 1.5)
    if not numeric_cols:
        score -= 20
    if not date_cols:
        score -= 8
    if rows < 10:
        score -= 10
    if cols < 3:
        score -= 6

    score = int(max(0, min(100, round(score))))
    if score >= 80:
        grade = "Good"
    elif score >= 60:
        grade = "Needs Cleaning"
    else:
        grade = "Risky"

    issues = []
    if missing_pct > 0:
        issues.append(f"{missing_pct}% cells are missing")
    if duplicate_rows:
        issues.append(f"{duplicate_rows} duplicate rows detected")
    if not numeric_cols:
        issues.append("No numeric KPI columns detected")
    if not date_cols:
        issues.append("No reliable date column detected")
    if rows < 10:
        issues.append("Very small dataset for trend analysis")

    return {
        "score": score,
        "grade": grade,
        "rows": rows,
        "cols": cols,
        "missing_pct": missing_pct,
        "duplicate_rows": duplicate_rows,
        "duplicate_pct": duplicate_pct,
        "numeric_cols": numeric_cols,
        "date_cols": date_cols,
        "issues": issues or ["No major data quality issues detected"],
    }


def detect_anomalies(df: pd.DataFrame, max_rows: int = 50) -> tuple[pd.DataFrame, str]:
    numeric_df = df.select_dtypes(include=[np.number]).copy()
    numeric_df = numeric_df.dropna(axis=1, how="all")

    if numeric_df.shape[1] == 0 or len(numeric_df) < 8:
        return pd.DataFrame(), "Anomaly detection needs at least 8 rows and one numeric column."

    try:
        from sklearn.ensemble import IsolationForest

        filled = numeric_df.fillna(numeric_df.median(numeric_only=True)).fillna(0)
        contamination = min(0.12, max(0.03, 8 / max(len(filled), 1)))
        model = IsolationForest(contamination=contamination, random_state=42)
        labels = model.fit_predict(filled)
        scores = model.decision_function(filled)

        outliers = df.loc[labels == -1].copy()
        outliers["Anomaly_Score"] = np.round(scores[labels == -1], 4)
        return outliers.sort_values("Anomaly_Score").head(max_rows), ""
    except Exception as exc:
        return pd.DataFrame(), f"Anomaly detection failed: {exc}"
