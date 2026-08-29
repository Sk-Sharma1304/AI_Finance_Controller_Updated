import pandas as pd
import pytest

from data_loader import DataValidationError, prepare_dataframe


def test_missing_required_columns_raises():
    with pytest.raises(DataValidationError) as exc:
        prepare_dataframe(pd.DataFrame({"payment_amount": [100]}))
    assert "payment_id" in exc.value.errors[0]
    assert "actual_settlement" in exc.value.errors[0]


def test_empty_file_raises():
    with pytest.raises(DataValidationError) as exc:
        prepare_dataframe(pd.DataFrame({
            "payment_id": [], "payment_amount": [], "actual_settlement": [],
        }))
    assert any("no data rows" in e for e in exc.value.errors)


def test_duplicate_payment_id_raises():
    df = pd.DataFrame({
        "payment_id": ["a", "a"],
        "payment_amount": [100, 200],
        "actual_settlement": [95, 190],
    })
    with pytest.raises(DataValidationError) as exc:
        prepare_dataframe(df)
    assert "duplicate payment_id" in exc.value.errors[0]


def test_non_numeric_amount_raises():
    df = pd.DataFrame({
        "payment_id": ["a"],
        "payment_amount": ["not_a_number"],
        "actual_settlement": [95],
    })
    with pytest.raises(DataValidationError) as exc:
        prepare_dataframe(df)
    assert "payment_amount" in exc.value.errors[0]


def test_non_positive_amount_raises():
    df = pd.DataFrame({
        "payment_id": ["a", "b"],
        "payment_amount": [100, 0],
        "actual_settlement": [95, 0],
    })
    with pytest.raises(DataValidationError) as exc:
        prepare_dataframe(df)
    assert "non-positive" in exc.value.errors[0]


def test_expected_settlement_is_computed_not_required(minimal_valid_df):
    # payment_amount - fee - tax - refund + adjustment, with all
    # optional columns defaulting to 0
    assert minimal_valid_df.loc[0, "expected_settlement"] == 1000.0
    assert minimal_valid_df.loc[1, "expected_settlement"] == 500.0


def test_optional_columns_default_to_zero(minimal_valid_df):
    for col in ["fee", "tax", "refund", "adjustment"]:
        assert col in minimal_valid_df.columns
        assert (minimal_valid_df[col] == 0).all()


def test_expected_settlement_formula_matches_ground_truth():
    """The core discovery this whole rewrite is built on: expected
    settlement is a deterministic function of the raw fields, not
    something that needs a separate ground-truth lookup file."""
    transactions = pd.read_csv("data/finance_controller_dataset.csv")
    ground_truth = pd.read_csv("data/ground_truth.csv")
    merged = transactions.merge(ground_truth, on="payment_id")

    computed = prepare_dataframe(
        transactions[[
            "payment_id", "payment_amount", "fee", "tax", "refund",
            "adjustment", "actual_settlement",
        ]]
    )

    merged = merged.sort_values("payment_id").reset_index(drop=True)
    computed = computed.sort_values("payment_id").reset_index(drop=True)

    diff = (merged["expected_settlement"] - computed["expected_settlement"]).abs()
    assert (diff < 0.01).all()


def test_formula_injection_is_neutralized():
    df = pd.DataFrame({
        "payment_id": ["=cmd|'/c calc'!A1", "safe_id"],
        "payment_amount": [100, 200],
        "actual_settlement": [95, 190],
    })
    result = prepare_dataframe(df)
    assert result.loc[0, "payment_id"].startswith("'=")
    assert result.loc[1, "payment_id"] == "safe_id"


def test_row_limit_enforced():
    big = pd.DataFrame({
        "payment_id": [f"p{i}" for i in range(50_001)],
        "payment_amount": [100.0] * 50_001,
        "actual_settlement": [95.0] * 50_001,
    })
    with pytest.raises(DataValidationError) as exc:
        prepare_dataframe(big)
    assert any("exceeds the 50000-row limit" in e for e in exc.value.errors)


def test_scenario_column_carried_through_but_not_required():
    """A scenario column, if present, should not break anything --
    but its absence (the realistic case) must not either."""
    df = pd.DataFrame({
        "payment_id": ["a"],
        "payment_amount": [100],
        "actual_settlement": [95],
        "scenario": ["normal"],
    })
    result = prepare_dataframe(df)
    assert result.loc[0, "scenario"] == "normal"
