"""
Regression pin: if the trained model, feature set, or scoring
weights change, this is the test that should force you to
consciously update the expected numbers below rather than silently
drift. It runs the exact CLI/API code path (data_loader ->
orchestrator.run_pipeline) against the bundled demo dataset.
"""

from data_loader import load_from_path
from orchestrator.finance_orchestrator import run_pipeline


def test_demo_dataset_decision_distribution_is_stable():
    df = load_from_path(
        "data/finance_controller_dataset.csv",
        "data/ground_truth.csv",
    )
    result = run_pipeline(df, llm_max_calls=0)

    assert len(result) == 100

    risk_counts = result["risk_level"].value_counts().to_dict()
    # Exact counts observed with the current trained model +
    # scoring weights. If this fails after an intentional change
    # (retraining, reweighting), update these numbers deliberately
    # -- don't just delete the assertion.
    assert risk_counts.get("LOW", 0) == 75
    assert risk_counts.get("CRITICAL", 0) == 11
    assert risk_counts.get("MEDIUM", 0) == 8
    assert risk_counts.get("HIGH", 0) == 6

    decision_counts = result["final_decision"].value_counts().to_dict()
    assert decision_counts.get("NORMAL", 0) == 75
    assert decision_counts.get("CONFIRMED_HIGH_PRIORITY", 0) == 17
    assert decision_counts.get("FINANCIAL_EXCEPTION", 0) == 8

    # Model version should be a real trained artifact, not the
    # untrained-batch-fit fallback -- if this fails, the model
    # registry (ml/models/) is missing or wasn't picked up.
    assert result["anomaly_model_version"].iloc[0] != "untrained-batch-fit"
