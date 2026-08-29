"""
Evaluates the unsupervised IsolationForest (the model actually
used in the live pipeline, see agents/anomaly_agent.py) trained
only on "normal-like" transactions — i.e. transactions that were
correctly and fully reconciled, whether or not a refund or
adjustment was involved.

See evaluation/labels.py for why refund/adjustment are treated as
normal-like rather than as anomalies.
"""

import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score
)

from labels import is_exception


# ==================================================
# 1. LOAD DATA
# ==================================================

transactions = pd.read_csv(
    "data/finance_controller_dataset.csv"
)

ground_truth = pd.read_csv(
    "data/ground_truth.csv"
)


# ==================================================
# 2. MERGE DATA
# ==================================================

data = transactions.merge(
    ground_truth,
    on="payment_id"
)


# ==================================================
# 3. CREATE FEATURES
# ==================================================

data["settlement_difference"] = (
    data["actual_settlement"]
    - data["expected_settlement"]
)


features = [
    "payment_amount",
    "fee",
    "tax",
    "refund",
    "adjustment",
    "actual_settlement",
    "settlement_difference"
]


# ==================================================
# 4. GROUND-TRUTH LABEL (see evaluation/labels.py)
# ==================================================

data["true_label"] = is_exception(
    data["scenario"]
)


# ==================================================
# 5. SPLIT NORMAL-LIKE DATA
# ==================================================
#
# "Normal-like" = normal, refund, adjustment — anything that
# was NOT flagged as a genuine reconciliation exception. Refunds
# and adjustments settle exactly as expected, so a model that
# never sees them in training should still classify them as
# normal at test time, and it should be graded that way.

normal_like = data[
    data["true_label"] == 0
].copy()


normal_train, normal_test = train_test_split(
    normal_like,
    test_size=0.20,
    random_state=42
)


# ==================================================
# 6. ALL EXCEPTION DATA
# ==================================================

exception_data = data[
    data["true_label"] == 1
].copy()


# ==================================================
# 7. TRAINING DATA
# ==================================================

X_train = normal_train[features]


# ==================================================
# 8. TEST DATA
# ==================================================

test_data = pd.concat(
    [
        normal_test,
        exception_data
    ],
    ignore_index=True
)


X_test = test_data[features]

y_test = test_data["true_label"]


# ==================================================
# 9. TRAIN ISOLATION FOREST
# ==================================================

model = IsolationForest(
    n_estimators=200,
    contamination="auto",
    random_state=42
)


model.fit(X_train)


# ==================================================
# 10. PREDICTION
# ==================================================

predictions = model.predict(X_test)


# Isolation Forest:
# -1 = anomaly
# +1 = normal

y_pred = (
    predictions == -1
).astype(int)


# ==================================================
# 11. ANOMALY SCORE
# ==================================================

scores = -model.decision_function(
    X_test
)


# ==================================================
# 12. EVALUATION
# ==================================================

print("\n========================================")
print("ANOMALY MODEL EVALUATION")
print("========================================")

print(
    f"Training normal-like transactions : "
    f"{len(normal_train)}"
)

print(
    f"Testing normal-like transactions  : "
    f"{len(normal_test)}"
)

print(
    f"Testing exceptions                : "
    f"{len(exception_data)}"
)

print(
    f"Total test transactions           : "
    f"{len(test_data)}"
)


# ==================================================
# 13. CONFUSION MATRIX
# ==================================================

print("\n========================================")
print("CONFUSION MATRIX")
print("========================================")

cm = confusion_matrix(
    y_test,
    y_pred
)

print(cm)


# ==================================================
# 14-16. PRECISION / RECALL / F1
# ==================================================

precision = precision_score(y_test, y_pred, zero_division=0)
recall = recall_score(y_test, y_pred, zero_division=0)
f1 = f1_score(y_test, y_pred, zero_division=0)

print(f"\nPrecision : {precision:.4f}")
print(f"Recall    : {recall:.4f}")
print(f"F1 Score  : {f1:.4f}")


# ==================================================
# 17. ROC-AUC
# ==================================================

try:

    auc = roc_auc_score(y_test, scores)

    print(f"ROC-AUC   : {auc:.4f}")

except ValueError:

    print("ROC-AUC   : Could not be calculated")


# ==================================================
# 18. CLASSIFICATION REPORT
# ==================================================

print("\n========================================")
print("CLASSIFICATION REPORT")
print("========================================")

print(
    classification_report(
        y_test,
        y_pred,
        target_names=["NORMAL", "EXCEPTION"],
        zero_division=0
    )
)
