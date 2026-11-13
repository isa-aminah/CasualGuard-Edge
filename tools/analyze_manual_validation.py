
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# --------------------------------------------------
# PATHS
# --------------------------------------------------

INPUT = Path(
    "training/test_track_review/test_track_review_manifest_FINAL.xlsx"
)

OUTPUT = Path("training/test_track_review/validation_results")
OUTPUT.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# LOAD AND VALIDATE DATA
# --------------------------------------------------

df = pd.read_excel(INPUT)

required = [
    "review_id",
    "weighted_track_class",
    "review_decision",
    "review_group",
    "observations",
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

df["review_decision"] = (
    df["review_decision"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.upper()
)

df["weighted_track_class"] = (
    df["weighted_track_class"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
)

valid_decisions = {
    "PEDESTRIAN",
    "VEHICLE",
    "OCCUPANT",
    "AMBIGUOUS",
    "NOT_VISIBLE",
}

invalid = set(df["review_decision"]) - valid_decisions

if invalid:
    raise ValueError(f"Invalid review decisions: {invalid}")

if len(df) != 60:
    raise ValueError(f"Expected 60 records, found {len(df)}")

if df["review_id"].duplicated().any():
    raise ValueError("Duplicate review IDs found")

if (df["review_decision"] == "").any():
    raise ValueError("Some review decisions are empty")

# --------------------------------------------------
# 1. MANUAL REVIEW DISTRIBUTION
# --------------------------------------------------

manual_counts = (
    df["review_decision"]
    .value_counts()
    .reindex(sorted(valid_decisions), fill_value=0)
    .rename_axis("manual_decision")
    .reset_index(name="count")
)

manual_counts.to_csv(
    OUTPUT / "manual_decision_distribution.csv",
    index=False
)

# --------------------------------------------------
# 2. AI VS MANUAL CROSS-TABULATION
# --------------------------------------------------

comparison = pd.crosstab(
    df["weighted_track_class"],
    df["review_decision"],
    margins=True,
)

comparison.to_csv(
    OUTPUT / "ai_manual_confusion_matrix.csv"
)

# --------------------------------------------------
# 3. DEFINITIVE PEDESTRIAN / VEHICLE AUDIT
# --------------------------------------------------

# Occupants, ambiguous and not-visible cases are
# reported separately, not silently treated as errors.

definitive = df[
    df["review_decision"].isin(["PEDESTRIAN", "VEHICLE"])
].copy()

definitive["manual_binary"] = (
    definitive["review_decision"].str.lower()
)

decisive_predictions = definitive[
    definitive["weighted_track_class"].isin(
        ["pedestrian", "vehicle"]
    )
].copy()

decisive_predictions["prediction_correct"] = (
    decisive_predictions["weighted_track_class"]
    == decisive_predictions["manual_binary"]
)

eligible_count = len(definitive)
decisive_count = len(decisive_predictions)
correct_count = int(
    decisive_predictions["prediction_correct"].sum()
)

coverage = (
    decisive_count / eligible_count
    if eligible_count else 0
)

selective_agreement = (
    correct_count / decisive_count
    if decisive_count else 0
)

overall_agreement_with_abstentions = (
    correct_count / eligible_count
    if eligible_count else 0
)

binary_matrix = pd.crosstab(
    definitive["manual_binary"],
    definitive["weighted_track_class"],
)

binary_matrix.to_csv(
    OUTPUT / "definitive_pedestrian_vehicle_comparison.csv"
)

# --------------------------------------------------
# 4. OCCUPANT ANALYSIS
# --------------------------------------------------

occupants = df[
    df["review_decision"] == "OCCUPANT"
]

occupant_analysis = (
    occupants.groupby("weighted_track_class")
    .size()
    .rename("count")
    .reset_index()
)

occupant_analysis.to_csv(
    OUTPUT / "occupant_confusion_analysis.csv",
    index=False
)

# --------------------------------------------------
# 5. UNCERTAIN PREDICTION ANALYSIS
# --------------------------------------------------

uncertain = df[
    df["weighted_track_class"] == "uncertain"
]

uncertain_analysis = (
    uncertain["review_decision"]
    .value_counts()
    .rename_axis("manual_decision")
    .reset_index(name="count")
)

uncertain_analysis.to_csv(
    OUTPUT / "uncertain_track_analysis.csv",
    index=False
)

# --------------------------------------------------
# 6. CLASSIFICATION AGREEMENT BY AI GROUP
# --------------------------------------------------

group_analysis = (
    df.groupby(
        ["review_group", "weighted_track_class", "review_decision"]
    )
    .size()
    .reset_index(name="count")
)

group_analysis.to_csv(
    OUTPUT / "group_level_comparison.csv",
    index=False
)

# --------------------------------------------------
# 7. CHARTS
# --------------------------------------------------

plt.figure(figsize=(9, 5))
plt.bar(
    manual_counts["manual_decision"],
    manual_counts["count"]
)
plt.title("Manual Review Decision Distribution")
plt.xlabel("Manual decision")
plt.ylabel("Number of tracks")
plt.xticks(rotation=25, ha="right")
plt.tight_layout()
plt.savefig(
    OUTPUT / "manual_decision_distribution.png",
    dpi=200
)
plt.close()

plt.figure(figsize=(10, 6))
plt.imshow(comparison.iloc[:-1, :-1], aspect="auto")
plt.colorbar(label="Number of tracks")
plt.xticks(
    range(len(comparison.columns) - 1),
    comparison.columns[:-1],
    rotation=30,
    ha="right",
)
plt.yticks(
    range(len(comparison.index) - 1),
    comparison.index[:-1],
)
plt.title("AI Classification vs Manual Visual Review")
plt.xlabel("Manual decision")
plt.ylabel("AI classification")
plt.tight_layout()
plt.savefig(
    OUTPUT / "ai_manual_confusion_matrix.png",
    dpi=200
)
plt.close()

# --------------------------------------------------
# 8. GENERATE REPORT
# --------------------------------------------------

report = f"""# CAUSALGUARD-EDGE
# Test-Set Track Classification Manual Validation

## 1. Audit overview

- Reviewed tracks: {len(df)}
- Manual visual decisions: {df['review_decision'].notna().sum()}
- AI classification groups: {df['weighted_track_class'].nunique()}

## 2. Manual decision distribution

{manual_counts.to_string(index=False)}

## 3. AI versus manual comparison

{comparison.to_string()}

## 4. Definitive pedestrian/vehicle subset

- Eligible manual pedestrian/vehicle tracks: {eligible_count}
- AI decisive predictions: {decisive_count}
- Correct decisive predictions: {correct_count}
- Prediction coverage: {coverage:.2%}
- Agreement among decisive predictions: {selective_agreement:.2%}
- Correct predictions divided by all eligible tracks: {overall_agreement_with_abstentions:.2%}

Uncertain AI predictions are treated as abstentions, not silently counted as correct.

## 5. Occupant analysis

{occupant_analysis.to_string(index=False)}

## 6. Uncertain prediction analysis

{uncertain_analysis.to_string(index=False)}

## 7. Methodological limitations

- This is a manually reviewed sample of 60 tracks from the test split.
- The sample was deliberately stratified by AI classification group.
- It is not a random representative sample of all test tracks.
- Results must not be presented as overall test-set accuracy.
- Manual decisions are based on visual contact sheets, not independent
  ground-truth annotations across every frame.
- Short tracks and uncertain visual evidence limit interpretation.
- Occupants are reported separately from pedestrians and vehicles.
- The analysis does not establish detection accuracy, tracking accuracy,
  near-miss detection accuracy, or real-world safety performance.

## 8. Interpretation

These findings are preliminary evidence about track-level role
classification. They can guide improvements and further validation,
but should not be generalized to the complete test dataset.
"""

(OUTPUT / "MANUAL_VALIDATION_REPORT.md").write_text(
    report,
    encoding="utf-8"
)

print("\nMANUAL VALIDATION ANALYSIS COMPLETE")
print("Reviewed tracks:", len(df))
print("Definitive pedestrian/vehicle subset:", eligible_count)
print("AI decisive predictions:", decisive_count)
print("Correct decisive predictions:", correct_count)
print("Prediction coverage:", f"{coverage:.2%}")
print("Selective agreement:", f"{selective_agreement:.2%}")

print("\nOUTPUT FOLDER:", OUTPUT)
print("\nGenerated files:")
for path in sorted(OUTPUT.iterdir()):
    print("-", path.name)
