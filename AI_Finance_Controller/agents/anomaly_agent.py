import logging
import os
import sys

import pandas as pd
from sklearn.ensemble import IsolationForest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.registry import ModelNotTrainedError, load_latest_anomaly_model  # noqa: E402

logger = logging.getLogger(__name__)

FEATURES = [
    "settlement_ratio",
    "deviation_ratio",
    "difference_to_payment_ratio",
]


class AnomalyAgent:
    """
    Flags transactions as ML anomalies.

    Preferred path: load the trained, versioned IsolationForest
    produced by ``ml/train_anomaly_model.py`` (see that file for
    why a fixed, offline-trained model beats fitting fresh on every
    request -- stable thresholds, reproducibility, auditability).

    Fallback path: if no trained model artifact exists yet (fresh
    clone, before anyone has run the training script), fit on the
    current batch as before, so the pipeline still works out of the
    box. This is clearly logged and surfaced in the output
    (``model_version`` = "untrained-batch-fit") so it's visible in
    the UI/audit trail whenever it happens -- it should not go
    unnoticed in a real deployment.
    """

    def __init__(self):
        self.model = None
        self.scaler = None
        self.model_version = "untrained-batch-fit"

        try:
            self.model, self.scaler, metadata = load_latest_anomaly_model()
            self.model_version = metadata["version"]
        except ModelNotTrainedError as exc:
            logger.warning(str(exc))

    def detect(self, data):

        data = data.copy()

        X = data[FEATURES]

        if self.model is not None:
            X_scaled = self.scaler.transform(X)
            predictions = self.model.predict(X_scaled)
        else:
            # Fallback: fit-on-batch, same behaviour as before a
            # trained model exists. Not reproducible across
            # differently-sized batches -- see class docstring.
            fallback_model = IsolationForest(
                contamination=0.25,
                random_state=42,
            )
            predictions = fallback_model.fit_predict(X)

        data["ml_anomaly"] = predictions

        data["anomaly_status"] = data["ml_anomaly"].apply(
            lambda x: "ANOMALY" if x == -1 else "NORMAL"
        )

        data["anomaly_model_version"] = self.model_version

        return data


def run_anomaly_agent(data):

    agent = AnomalyAgent()

    return agent.detect(data)


def main():

    print("\n========================================")
    print("AI FINANCE CONTROLLER")
    print("ANOMALY AGENT")
    print("========================================")

    from data_loader import load_from_path
    from agents.reconciliation_agent import run_reconciliation_agent

    data = load_from_path(
        "data/finance_controller_dataset.csv",
        "data/ground_truth.csv",
    )
    data = run_reconciliation_agent(data)

    result = run_anomaly_agent(data)

    anomalies = result[
        result["anomaly_status"] == "ANOMALY"
    ]

    print(f"Model version      : {result['anomaly_model_version'].iloc[0]}")
    print(f"Total transactions : {len(result)}")
    print(f"ML anomalies       : {len(anomalies)}")

    print("\n========================================")
    print("DETECTED ANOMALIES")
    print("========================================")

    columns = [
        c for c in [
            "payment_id",
            "scenario",
            "settlement_ratio",
            "deviation_ratio",
            "difference_to_payment_ratio",
            "anomaly_status",
        ] if c in anomalies.columns
    ]

    print(
        anomalies[columns].to_string(index=False)
    )


if __name__ == "__main__":
    main()
