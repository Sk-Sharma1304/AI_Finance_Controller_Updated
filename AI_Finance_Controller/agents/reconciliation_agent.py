import os
import pandas as pd


class ReconciliationAgent:

    def __init__(self):
        self.name = "Reconciliation Agent"

    def reconcile(self, data):

        result = data.copy()

        # --------------------------------------------------
        # 1. Calculate financial difference
        # --------------------------------------------------
        #
        # Difference between what should have been settled
        # and what was actually settled.
        #
        result["settlement_difference"] = (
            result["expected_settlement"]
            - result["actual_settlement"]
        )

        # Absolute financial impact
        result["financial_impact"] = (
            result["settlement_difference"].abs()
        )

        # --------------------------------------------------
        # 2. Settlement Ratio
        # --------------------------------------------------
        #
        # How much of the expected settlement was actually
        # received?
        #
        # Example:
        #
        # expected = 1000
        # actual   = 900
        #
        # settlement_ratio = 0.90
        #
        result["settlement_ratio"] = (
            result["actual_settlement"]
            / result["expected_settlement"]
        )

        # Avoid infinite values
        result["settlement_ratio"] = (
            result["settlement_ratio"]
            .replace([float("inf"), -float("inf")], 0)
            .fillna(0)
        )

        # --------------------------------------------------
        # 3. Deviation Ratio
        # --------------------------------------------------
        #
        # Measures how far the actual settlement is from
        # the expected settlement.
        #
        # Example:
        #
        # expected = 1000
        # actual   = 900
        #
        # deviation = 100 / 1000 = 0.10
        #
        result["deviation_ratio"] = (
            result["settlement_difference"].abs()
            / result["expected_settlement"].abs()
        )

        result["deviation_ratio"] = (
            result["deviation_ratio"]
            .replace([float("inf"), -float("inf")], 0)
            .fillna(0)
        )

        # --------------------------------------------------
        # 4. Difference to Payment Ratio
        # --------------------------------------------------
        #
        # Measures the financial difference relative to
        # the original payment amount.
        #
        result["difference_to_payment_ratio"] = (
            result["settlement_difference"].abs()
            / result["amount"].abs()
        )

        result["difference_to_payment_ratio"] = (
            result["difference_to_payment_ratio"]
            .replace([float("inf"), -float("inf")], 0)
            .fillna(0)
        )

        # --------------------------------------------------
        # 5. Reconciliation Status
        # --------------------------------------------------

        result["reconciliation_status"] = "RECONCILED"

        result.loc[
            result["financial_impact"] > 0,
            "reconciliation_status"
        ] = "DISCREPANCY"

        # --------------------------------------------------
        # 6. Missing settlement
        # --------------------------------------------------

        result.loc[
            result["actual_settlement"].isna(),
            "reconciliation_status"
        ] = "MISSING_SETTLEMENT"

        # --------------------------------------------------
        # 7. Reconciliation severity
        # --------------------------------------------------

        result["reconciliation_severity"] = "LOW"

        result.loc[
            result["deviation_ratio"] >= 0.05,
            "reconciliation_severity"
        ] = "MEDIUM"

        result.loc[
            result["deviation_ratio"] >= 0.20,
            "reconciliation_severity"
        ] = "HIGH"

        result.loc[
            result["deviation_ratio"] >= 0.50,
            "reconciliation_severity"
        ] = "CRITICAL"

        return result


def run_reconciliation_agent(data):

    agent = ReconciliationAgent()

    return agent.reconcile(data)


def main():

    print("\n========================================")
    print("AI FINANCE CONTROLLER")
    print("RECONCILIATION AGENT")
    print("========================================")

    # --------------------------------------------------
    # Load transaction data + ground truth
    # --------------------------------------------------

    transactions = pd.read_csv(
        "data/finance_controller_dataset.csv"
    )

    ground_truth = pd.read_csv(
        "data/ground_truth.csv"
    )

    data = transactions.merge(
        ground_truth,
        on="payment_id"
    )

    data["amount"] = data["payment_amount"]

    # --------------------------------------------------
    # Run reconciliation
    # --------------------------------------------------

    agent = ReconciliationAgent()

    result = agent.reconcile(data)

    # --------------------------------------------------
    # Save output
    # --------------------------------------------------

    os.makedirs("outputs", exist_ok=True)

    result.to_csv(
        "outputs/reconciliation_results.csv",
        index=False
    )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    print(
        f"Total transactions : {len(result)}"
    )

    print("\nReconciliation status:")

    print(
        result[
            "reconciliation_status"
        ].value_counts()
    )

    print("\n========================================")
    print("RECONCILIATION RESULTS")
    print("========================================")

    columns = [
        "payment_id",
        "scenario",
        "expected_settlement",
        "actual_settlement",
        "financial_impact",
        "settlement_ratio",
        "deviation_ratio",
        "difference_to_payment_ratio",
        "reconciliation_status",
        "reconciliation_severity"
    ]

    # Only display columns that actually exist
    available_columns = [
        column
        for column in columns
        if column in result.columns
    ]

    print(
        result[
            available_columns
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()