from pathlib import Path
import time
import warnings

import numpy as np
import pandas as pd

from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
)

from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "training" / "algorithm_comparison"

BASELINE_FILE = BASE / "reviewed_track_feature_dataset.csv"
ENHANCED_FILE = (
    BASE / "experiment2_features" / "experiment2_feature_dataset.csv"
)
OUTPUT_DIR = BASE / "unified_binary_comparison"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CLASSES = ["PEDESTRIAN", "VEHICLE"]
KEYS = ["video", "track_id"]

BASELINE_FEATURES = [
    "track_observations",
    "duration_sec",
    "mean_confidence",
    "std_confidence",
    "mean_width",
    "std_width",
    "mean_height",
    "std_height",
    "mean_bbox_area",
    "mean_aspect_ratio",
    "std_center_x",
    "std_center_y",
    "path_length_px",
    "mean_speed_px_sec",
    "std_speed_px_sec",
    "max_speed_px_sec",
]

META_COLUMNS = {"video", "track_id", "target", "target_binary"}


def make_models():
    return {
        "logistic_regression": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(
                max_iter=5000, class_weight="balanced", random_state=42
            )),
        ]),
        "svm_rbf": Pipeline([
            ("scaler", StandardScaler()),
            ("model", SVC(
                kernel="rbf", C=1.0, gamma="scale",
                class_weight="balanced"
            )),
        ]),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "xgboost": XGBClassifier(
            n_estimators=100,
            max_depth=2,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        ),
        "lightgbm": LGBMClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.05,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
            verbosity=-1,
        ),
    }


def load_and_validate():
    for path in [BASELINE_FILE, ENHANCED_FILE]:
        if not path.exists():
            raise FileNotFoundError(f"Required dataset not found: {path}")

    baseline = pd.read_csv(BASELINE_FILE)
    enhanced = pd.read_csv(ENHANCED_FILE)

    for name, df in [("baseline", baseline), ("enhanced", enhanced)]:
        missing = set(KEYS + ["target"]) - set(df.columns)
        if missing:
            raise ValueError(f"{name} dataset missing columns: {sorted(missing)}")
        if df.duplicated(KEYS).any():
            dup = df.loc[df.duplicated(KEYS, keep=False), KEYS]
            raise ValueError(f"{name} dataset has duplicate video/track rows:\n{dup}")
        df["track_id"] = df["track_id"].astype(str)
        df["video"] = df["video"].astype(str)
        df["target_binary"] = df["target"].replace({"OCCUPANT": "VEHICLE"})
        unexpected = set(df["target_binary"].unique()) - set(CLASSES)
        if unexpected:
            raise ValueError(f"{name} dataset has unexpected labels: {unexpected}")

    # Ensure both experiments use exactly the same reviewed tracks and mapped labels.
    b = baseline[KEYS + ["target_binary"]].copy()
    e = enhanced[KEYS + ["target_binary"]].copy()
    check = b.merge(e, on=KEYS, how="outer", suffixes=("_baseline", "_enhanced"), indicator=True)

    if not (check["_merge"] == "both").all():
        counts = check["_merge"].value_counts().to_dict()
        raise ValueError(f"Datasets do not contain identical track keys: {counts}")

    mismatch = check[check["target_binary_baseline"] != check["target_binary_enhanced"]]
    if not mismatch.empty:
        raise ValueError(
            "Mapped labels differ between datasets:\n"
            + mismatch.to_string(index=False)
        )

    if len(baseline) != 54 or len(enhanced) != 54:
        raise ValueError(
            f"Expected 54 tracks in each dataset; found baseline={len(baseline)}, "
            f"enhanced={len(enhanced)}"
        )

    missing_baseline_features = [
        c for c in BASELINE_FEATURES if c not in baseline.columns
    ]
    if missing_baseline_features:
        raise ValueError(
            f"Baseline dataset missing original feature columns: {missing_baseline_features}"
        )

    # The enhanced dataset's 40 features are all numeric columns other than identifiers/labels.
    enhanced_features = [
        c for c in enhanced.columns if c not in META_COLUMNS
    ]
    if len(enhanced_features) != 40:
        raise ValueError(
            f"Expected 40 enhanced feature columns, found {len(enhanced_features)}: "
            f"{enhanced_features}"
        )

    print("DATASET AUDIT PASSED")
    print("Baseline tracks:", len(baseline))
    print("Enhanced tracks:", len(enhanced))
    print("Unique videos:", baseline["video"].nunique())
    print("Identical track keys and mapped labels: YES")
    print("Classes:")
    print(baseline["target_binary"].value_counts().to_string())
    print("Baseline feature count:", len(BASELINE_FEATURES))
    print("Enhanced feature count:", len(enhanced_features))

    return baseline, enhanced, enhanced_features


def run_one_configuration(config_name, df, feature_columns):
    X = df[feature_columns].apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan)
    if X.isna().any().any():
        bad = X.columns[X.isna().any()].tolist()
        raise ValueError(f"{config_name}: missing/non-numeric feature values: {bad}")

    y = df["target_binary"].astype(str).to_numpy()
    groups = df["video"].astype(str).to_numpy()

    if set(np.unique(y)) != set(CLASSES):
        raise ValueError(f"{config_name}: expected both classes {CLASSES}")

    splitter = LeaveOneGroupOut()
    summary_rows, class_rows, prediction_rows, fold_rows = [], [], [], []

    for model_name, model in make_models().items():
        print(f"\n[{config_name}] Running {model_name}")
        all_true, all_pred = [], []
        predict_ms_per_track = []
        fit_seconds = []

        for fold, (train_idx, test_idx) in enumerate(
            splitter.split(X, y, groups=groups), start=1
        ):
            y_train = y[train_idx]
            y_test = y[test_idx]
            if set(np.unique(y_train)) != set(CLASSES):
                raise ValueError(
                    f"{config_name}/{model_name}/fold {fold}: training split "
                    "does not contain both classes"
                )

            if model_name == "xgboost":
                label_to_int = {"PEDESTRIAN": 0, "VEHICLE": 1}
                int_to_label = {0: "PEDESTRIAN", 1: "VEHICLE"}
                y_fit = np.asarray([label_to_int[v] for v in y_train])
            else:
                int_to_label = None
                y_fit = y_train

            fit_start = time.perf_counter()
            model.fit(X.iloc[train_idx], y_fit)
            fit_seconds.append(time.perf_counter() - fit_start)

            pred_start = time.perf_counter()
            pred = model.predict(X.iloc[test_idx])
            elapsed_ms = (time.perf_counter() - pred_start) * 1000
            if model_name == "xgboost":
                pred = np.asarray([int_to_label[int(v)] for v in pred])

            predict_ms_per_track.append(elapsed_ms / len(test_idx))
            all_true.extend(y_test.tolist())
            all_pred.extend(np.asarray(pred).tolist())

            held_out_video = groups[test_idx[0]]
            fold_rows.append({
                "feature_configuration": config_name,
                "algorithm": model_name,
                "held_out_video": held_out_video,
                "test_tracks": len(test_idx),
                "fold_accuracy": accuracy_score(y_test, pred),
            })

            for idx, actual, predicted in zip(test_idx, y_test, pred):
                prediction_rows.append({
                    "feature_configuration": config_name,
                    "algorithm": model_name,
                    "video": groups[idx],
                    "track_id": df.iloc[idx]["track_id"],
                    "actual": actual,
                    "predicted": predicted,
                    "correct": bool(actual == predicted),
                })

        all_true = np.asarray(all_true)
        all_pred = np.asarray(all_pred)

        precision, recall, f1, support = precision_recall_fscore_support(
            all_true, all_pred, labels=CLASSES, zero_division=0
        )
        summary_rows.append({
            "feature_configuration": config_name,
            "algorithm": model_name,
            "tracks": len(all_true),
            "videos": len(np.unique(groups)),
            "features": len(feature_columns),
            "accuracy": accuracy_score(all_true, all_pred),
            "balanced_accuracy": balanced_accuracy_score(all_true, all_pred),
            "macro_precision": float(np.mean(precision)),
            "macro_recall": float(np.mean(recall)),
            "macro_f1": float(np.mean(f1)),
            "mean_prediction_ms_per_track": float(np.mean(predict_ms_per_track)),
            "total_fit_time_sec_across_folds": float(np.sum(fit_seconds)),
        })

        for i, class_name in enumerate(CLASSES):
            class_rows.append({
                "feature_configuration": config_name,
                "algorithm": model_name,
                "class": class_name,
                "precision": precision[i],
                "recall": recall[i],
                "f1": f1[i],
                "support": int(support[i]),
            })

        cm = confusion_matrix(all_true, all_pred, labels=CLASSES)
        pd.DataFrame(
            cm,
            index=[f"actual_{c}" for c in CLASSES],
            columns=[f"predicted_{c}" for c in CLASSES],
        ).to_csv(
            OUTPUT_DIR / f"{config_name}_{model_name}_confusion_matrix.csv"
        )

        print(
            f"  accuracy={summary_rows[-1]['accuracy']:.4f} | "
            f"balanced_accuracy={summary_rows[-1]['balanced_accuracy']:.4f} | "
            f"macro_f1={summary_rows[-1]['macro_f1']:.4f}"
        )

    return summary_rows, class_rows, prediction_rows, fold_rows


def main():
    baseline, enhanced, enhanced_features = load_and_validate()

    all_summary, all_classes, all_predictions, all_folds = [], [], [], []

    configs = [
        ("baseline_16_features", baseline, BASELINE_FEATURES),
        ("enhanced_40_features", enhanced, enhanced_features),
    ]

    for config_name, df, features in configs:
        results = run_one_configuration(config_name, df, features)
        all_summary.extend(results[0])
        all_classes.extend(results[1])
        all_predictions.extend(results[2])
        all_folds.extend(results[3])

    summary = pd.DataFrame(all_summary).sort_values(
        ["feature_configuration", "macro_f1"], ascending=[True, False]
    )
    class_df = pd.DataFrame(all_classes)
    predictions_df = pd.DataFrame(all_predictions)
    folds_df = pd.DataFrame(all_folds)

    summary.to_csv(OUTPUT_DIR / "unified_binary_summary.csv", index=False)
    class_df.to_csv(OUTPUT_DIR / "unified_binary_per_class.csv", index=False)
    predictions_df.to_csv(OUTPUT_DIR / "unified_binary_oof_predictions.csv", index=False)
    folds_df.to_csv(OUTPUT_DIR / "unified_binary_per_video_folds.csv", index=False)

    print("\n" + "=" * 95)
    print("UNIFIED TWO-CLASS COMPARISON — ALL EXPERIMENTS USE IDENTICAL TRACKS/LABELS/FOLDS")
    print("=" * 95)
    cols = [
        "feature_configuration", "algorithm", "features", "accuracy",
        "balanced_accuracy", "macro_f1", "mean_prediction_ms_per_track"
    ]
    print(summary[cols].to_string(index=False, formatters={
        "accuracy": "{:.4f}".format,
        "balanced_accuracy": "{:.4f}".format,
        "macro_f1": "{:.4f}".format,
        "mean_prediction_ms_per_track": "{:.3f}".format,
    }))
    print(f"\nSaved all unified results to:\n{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
