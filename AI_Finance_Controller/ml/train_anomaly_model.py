"""
Offline training for the anomaly detection model
====================================================

Why this exists: the original ``anomaly_agent.py`` fit a fresh
IsolationForest inside every single pipeline run, on whatever batch
of transactions it happened to be given. That means:

  - Thresholds shift batch-to-batch (a transaction flagged ANOMALY
    in a batch of 100 might not be flagged in a batch of 5 -- the
    model has no stable notion of "normal" independent of what
    else is in the request).
  - Results aren't reproducible: re-run the same file twice and
    scikit-learn's IsolationForest can (depending on version/seed
    handling) behave differently.
  - You can't audit "which model version made this decision" --
    there's no artifact to point to.

This script fits the model ONCE on a representative training set,
serializes it (model + scaler + metadata) to ``ml/models/``, and
``agents/anomaly_agent.py`` loads that fixed artifact at inference
time instead of retraining per request.

IMPORTANT: this training set is the bundled 100-row synthetic demo
dataset, because that's the only labeled-ish data available in this
repo. That is NOT sufficient for a real production model. Before
relying on this in production, retrain on a large sample of your
actual historical settlement data (thousands+ of real transactions,
spanning normal operation and known-good incident examples) using
this same script structure. The training set is the single biggest
lever on model quality here -- more so than any hyperparameter.

Usage:
    python ml/train_anomaly_model.py [--input path/to/transactions.csv]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_loader import load_from_path  # noqa: E402
from agents.reconciliation_agent import run_reconciliation_agent  # noqa: E402

FEATURES = [
    "settlement_ratio",
    "deviation_ratio",
    "difference_to_payment_ratio",
]

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
CONTAMINATION = 0.25
RANDOM_STATE = 42


def build_training_features(transactions_csv: str, ground_truth_csv: str | None) -> pd.DataFrame:
    df = load_from_path(transactions_csv, ground_truth_csv)
    df = run_reconciliation_agent(df)
    return df


def train(df: pd.DataFrame, version: str) -> dict:
    X = df[FEATURES]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
        n_estimators=200,
    )
    model.fit(X_scaled)

    os.makedirs(MODEL_DIR, exist_ok=True)

    model_path = os.path.join(MODEL_DIR, f"anomaly_model_{version}.joblib")
    scaler_path = os.path.join(MODEL_DIR, f"anomaly_scaler_{version}.joblib")

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    metadata = {
        "version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "features": FEATURES,
        "contamination": CONTAMINATION,
        "random_state": RANDOM_STATE,
        "n_estimators": 200,
        "training_rows": len(df),
        "model_file": os.path.basename(model_path),
        "scaler_file": os.path.basename(scaler_path),
        "training_data_note": (
            "Trained on the bundled synthetic demo dataset. Retrain on "
            "real historical transactions before production use."
        ),
    }

    metadata_path = os.path.join(MODEL_DIR, f"metadata_{version}.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # "latest" pointer so the serving code doesn't need to know the
    # version string -- retraining just updates this file.
    latest_path = os.path.join(MODEL_DIR, "latest.json")
    with open(latest_path, "w") as f:
        json.dump({"version": version}, f, indent=2)

    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="data/finance_controller_dataset.csv",
        help="Path to a transactions CSV to train on.",
    )
    parser.add_argument(
        "--ground-truth",
        default="data/ground_truth.csv",
        help="Optional ground-truth CSV (demo dataset only; not required for real data).",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Version tag for this model (default: timestamp-based).",
    )
    args = parser.parse_args()

    version = args.version or datetime.now(timezone.utc).strftime("v%Y%m%d%H%M%S")

    ground_truth = args.ground_truth if os.path.exists(args.ground_truth) else None

    df = build_training_features(args.input, ground_truth)
    metadata = train(df, version)

    print("Trained and saved anomaly model:")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
