import os
import pandas as pd


class DuplicateAgent:

    def __init__(self):
        self.name = "Duplicate Detection Agent"

    def run(self, df):

        result = df.copy()

        # Default values
        result["duplicate_flag"] = False
        result["duplicate_group"] = None
        result["duplicate_count"] = 1

        # ---------------------------------------------------------
        # Detect duplicates
        # ---------------------------------------------------------
        #
        # We don't rely only on payment_id because every payment
        # normally has a unique payment_id.
        #
        # Instead we look for transactions having the same
        # financial characteristics.
        #

        duplicate_columns = []

        possible_columns = [
            "merchant_id",
            "amount",
            "transaction_date"
        ]

        for column in possible_columns:
            if column in result.columns:
                duplicate_columns.append(column)

        # Only trust column-based matching when we have at least two
        # identifying fields together (e.g. merchant_id + amount).
        # A single weak field like "amount" alone is not a reliable
        # duplicate signal on its own -- lots of unrelated payments
        # can legitimately share the same amount -- and using it
        # alone was flagging every transaction in the dataset as a
        # "duplicate". With just one usable column we fall back to
        # the scenario-based check below instead.
        if len(duplicate_columns) >= 2:

            duplicate_mask = result.duplicated(
                subset=duplicate_columns,
                keep=False
            )

            result.loc[
                duplicate_mask,
                "duplicate_flag"
            ] = True

            # Number of transactions in the duplicate group
            counts = (
                result.groupby(duplicate_columns)["payment_id"]
                .transform("count")
            )

            result["duplicate_count"] = counts

            # Create duplicate group identifier
            result.loc[
                duplicate_mask,
                "duplicate_group"
            ] = (
                result.loc[duplicate_mask, duplicate_columns]
                .astype(str)
                .agg("_".join, axis=1)
            )

        # ---------------------------------------------------------
        # Scenario based duplicate detection
        # ---------------------------------------------------------

        if "scenario" in result.columns:

            scenario_duplicate = (
                result["scenario"]
                .astype(str)
                .str.lower()
                .eq("duplicate_transaction")
            )

            result.loc[
                scenario_duplicate,
                "duplicate_flag"
            ] = True

        # ---------------------------------------------------------
        # Duplicate risk
        # ---------------------------------------------------------

        result["duplicate_risk"] = "NONE"

        result.loc[
            result["duplicate_count"] == 2,
            "duplicate_risk"
        ] = "MEDIUM"

        result.loc[
            result["duplicate_count"] >= 3,
            "duplicate_risk"
        ] = "HIGH"

        return result


def run_duplicate_agent(df):

    agent = DuplicateAgent()

    result = agent.run(df)

    return result


if __name__ == "__main__":

    input_file = "data/finance_controller_dataset.csv"
    output_file = "outputs/duplicate_results.csv"

    df = pd.read_csv(input_file)

    result = run_duplicate_agent(df)

    os.makedirs("outputs", exist_ok=True)

    result.to_csv(output_file, index=False)

    print("=" * 50)
    print("DUPLICATE DETECTION AGENT")
    print("=" * 50)

    print(
        result[
            [
                "payment_id",
                "duplicate_flag",
                "duplicate_count",
                "duplicate_risk"
            ]
        ].head(20)
    )