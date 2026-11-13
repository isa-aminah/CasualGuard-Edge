import pandas as pd
from pathlib import Path

BASE = Path("training/tracking_batch")

KEYS = ["video", "person_track_id"]

corrected = pd.read_csv(
    BASE / "person_classification_corrected.csv"
)

visual = pd.read_csv(
    BASE / "occupant_visual_review_labels_v2.csv"
)

reference = pd.read_csv(
    BASE / "person_track_review_reference.csv"
)

print("\n========== CAUSALGUARD ANNOTATION AUDIT ==========")

# 1. Check duplicate annotation records
print("\n1. DUPLICATE RECORDS")

for name, df in [
    ("Corrected", corrected),
    ("Visual", visual),
    ("Reference", reference)
]:
    duplicates = df.duplicated(KEYS).sum()
    print(f"{name}: {duplicates}")

# 2. Compare visual and reference labels
print("\n2. VISUAL VS REFERENCE")

comparison = visual[
    KEYS + ["manual_label"]
].merge(
    reference[KEYS + ["review_label"]],
    on=KEYS,
    how="outer",
    indicator=True
)

conflicts = comparison[
    (comparison["_merge"] == "both") &
    (comparison["manual_label"] != comparison["review_label"])
]

print("Matched records:", (comparison["_merge"] == "both").sum())
print("Label disagreements:", len(conflicts))

# 3. Compare corrected classifications
print("\n3. CORRECTED CLASSIFICATION VS REFERENCE")

status_map = {
    "REVIEWED_OCCUPANT": "OCCUPANT",
    "REVIEWED_PEDESTRIAN": "PEDESTRIAN",
    "REVIEWED_UNCERTAIN": "UNCERTAIN"
}

reviewed = corrected[
    corrected["classification_status"].isin(status_map)
].copy()

reviewed["corrected_label"] = (
    reviewed["classification_status"].map(status_map)
)

comparison2 = reference.merge(
    reviewed[KEYS + ["corrected_label"]],
    on=KEYS,
    how="inner"
)

disagreements = comparison2[
    comparison2["review_label"] !=
    comparison2["corrected_label"]
]

print("Compared records:", len(comparison2))
print("Disagreements:", len(disagreements))

if not disagreements.empty:
    print("\nUNRESOLVED RECORDS:")
    print(disagreements.to_string(index=False))

# 4. Video coverage
print("\n4. VIDEO COVERAGE")

tracking = pd.read_csv(
    BASE / "all_training_tracks.csv",
    usecols=["video"]
)

interactions = pd.read_csv(
    BASE / "pedestrian_vehicle_interactions.csv",
    usecols=["video"]
)

episodes = pd.read_csv(
    BASE / "interaction_episode_candidates.csv",
    usecols=["video"]
)

tracking_videos = set(tracking["video"].unique())
interaction_videos = set(interactions["video"].unique())
episode_videos = set(episodes["video"].unique())

print("Tracking videos:", len(tracking_videos))
print("Interaction videos:", len(interaction_videos))
print("Episode videos:", len(episode_videos))

print("Videos without interactions:",
      sorted(tracking_videos - interaction_videos))

print("Interaction videos without episodes:",
      sorted(interaction_videos - episode_videos))

# 5. Summary
print("\n========== AUDIT SUMMARY ==========")
print("Visual/reference disagreements:", len(conflicts))
print("Corrected/reference disagreements:", len(disagreements))
print("Duplicate annotation records: 0 expected")
print("Audit completed successfully.")

