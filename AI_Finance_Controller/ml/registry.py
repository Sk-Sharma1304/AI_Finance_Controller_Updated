"""
Model registry — loads the trained anomaly model artifact produced
by ``train_anomaly_model.py``.

Deliberately simple (files on disk + a `latest.json` pointer)
rather than a full model registry service (MLflow, SageMaker Model
Registry, etc.) -- upgrade to one of those once you have more than
one model or need to serve across many machines without a shared
filesystem.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")


class ModelNotTrainedError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def load_latest_anomaly_model():
    """Returns (model, scaler, metadata). Cached for the life of
    the process -- restart the process (or call
    ``load_latest_anomaly_model.cache_clear()``) to pick up a newly
    trained model.
    """

    import joblib

    latest_path = os.path.join(MODEL_DIR, "latest.json")

    if not os.path.exists(latest_path):
        raise ModelNotTrainedError(
            "No trained anomaly model found. Run "
            "`python ml/train_anomaly_model.py` first, or the anomaly "
            "agent will fall back to fitting on each batch (see "
            "agents/anomaly_agent.py)."
        )

    with open(latest_path) as f:
        version = json.load(f)["version"]

    metadata_path = os.path.join(MODEL_DIR, f"metadata_{version}.json")
    with open(metadata_path) as f:
        metadata = json.load(f)

    model = joblib.load(os.path.join(MODEL_DIR, metadata["model_file"]))
    scaler = joblib.load(os.path.join(MODEL_DIR, metadata["scaler_file"]))

    return model, scaler, metadata
