"""
Evaluates two models against the reconciliation feature set:

1. IsolationForest (unsupervised) — trained without labels, the
   kind of model you can deploy on day one before you have any
   confirmed exception history. Good for catching *novel* problem
   patterns; not tuned to any specific known scenario.

2. RandomForestClassifier (supervised) — trained on the injected
   scenario labels. Higher precision/recall on the exception types
   we already have examples of, but can't generalize to a brand
   new failure mode the way the unsupervised model can.

The pipeline itself only uses the unsupervised model (see
agents/anomaly_agent.py) so it works on unlabeled, real production
data. This script exists to show both approaches were evaluated
and to justify that choice with numbers, and to demonstrate the
label-quality issue documented in evaluation/labels.py.
"""

import pandas as pd

from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    confusion_matrix,
    classification_report,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score
)

from labels import is_exception


# ==================================================
# 1. LOAD FEATURE DATASET
# ==================================================

data = pd.read_csv(
    "data/reconciliation_features.csv"
)


# ==================================================
# 2. FEATURES
# ==================================================

features = [
    "settlement_ratio",
    "deviation_ratio",
    "is_missing_settlement",
    "is_over_settlement",
    "is_under_settlement",
    "difference_to_payment_ratio"
]


# ==================================================
# 3. GROUND-TRUTH LABEL (see evaluation/labels.py)
# ==================================================

data["actual_label"] = is_exception(
    data["scenario"]
)


# ==================================================
# 4. TRAIN / TEST SPLIT (stratified, so both classes
#    are represented in both splits regardless of the
#    row order in the CSV)
# ==================================================

X_train, X_test, y_train, y_test = train_test_split(
    data[features],
    data["actual_label"],
    test_size=0.30,
    stratify=data["actual_label"],
    random_state=42
)


def report(name, y_pred, y_score):

    print(f"\n--- {name} ---")

    print(
        confusion_matrix(y_test, y_pred)
    )

    print(
        f"Precision : "
        f"{precision_score(y_test, y_pred, zero_division=0):.4f}"
    )

    print(
        f"Recall    : "
        f"{recall_score(y_test, y_pred, zero_division=0):.4f}"
    )

    print(
        f"F1 Score  : "
        f"{f1_score(y_test, y_pred, zero_division=0):.4f}"
    )

    try:
        print(
            f"ROC-AUC   : {roc_auc_score(y_test, y_score):.4f}"
        )
    except ValueError:
        print("ROC-AUC   : could not be calculated")

    print(
        classification_report(
            y_test,
            y_pred,
            target_names=["NORMAL", "EXCEPTION"],
            zero_division=0
        )
    )


print("=" * 50)
print("RECONCILIATION MODEL EVALUATION")
print("=" * 50)
print(f"Train size : {len(X_train)}   Test size : {len(X_test)}")

# ==================================================
# 5. UNSUPERVISED — IsolationForest
# ==================================================

iso_model = IsolationForest(
    n_estimators=300,
    contamination=0.30,
    random_state=42
)

iso_model.fit(X_train)

iso_pred = (
    iso_model.predict(X_test) == -1
).astype(int)

iso_score = -iso_model.decision_function(X_test)

report("IsolationForest (unsupervised)", iso_pred, iso_score)

# ==================================================
# 6. SUPERVISED — RandomForestClassifier
# ==================================================

rf_model = RandomForestClassifier(
    n_estimators=200,
    class_weight="balanced",
    random_state=42
)

rf_model.fit(X_train, y_train)

rf_pred = rf_model.predict(X_test)

rf_score = rf_model.predict_proba(X_test)[:, 1]

report("RandomForestClassifier (supervised)", rf_pred, rf_score)

print("\nFeature importance (RandomForest):")

importance = pd.Series(
    rf_model.feature_importances_,
    index=features
).sort_values(ascending=False)

print(importance)
