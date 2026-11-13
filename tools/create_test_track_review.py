
from pathlib import Path
import re

import cv2
import numpy as np
import pandas as pd

# --------------------------------------------------
# Paths
# --------------------------------------------------

VIDEO_DIR = Path(r"E:\download\Video Datasets")

TRACKING_CSV = Path(
    "training/test_tracking_batch/all_test_tracks.csv"
)

CLASSIFICATION_CSV = Path(
    "training/classification_comparison/track_classification_details.csv"
)

OUTPUT_DIR = Path("training/test_track_review")
SHEETS_DIR = OUTPUT_DIR / "review_sheets"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SHEETS_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# Load existing results
# --------------------------------------------------

tracks = pd.read_csv(CLASSIFICATION_CSV)
detections = pd.read_csv(TRACKING_CSV)

tracks["track_id"] = tracks["track_id"].astype(int)
detections["track_id"] = detections["track_id"].astype(int)

tracks["raw_class_labels"] = (
    tracks["raw_class_labels"].fillna("").astype(str)
)

# --------------------------------------------------
# Select reproducible review sample
# --------------------------------------------------

def select(group, count, seed):
    if len(group) < count:
        raise ValueError(
            f"Requested {count} tracks, only {len(group)} available"
        )
    return group.sample(n=count, random_state=seed)


pedestrians = select(
    tracks[tracks["weighted_track_class"] == "pedestrian"],
    20, 42
)

vehicles = select(
    tracks[tracks["weighted_track_class"] == "vehicle"],
    20, 43
)

uncertain = tracks[
    tracks["weighted_track_class"] == "uncertain"
]

person_only = uncertain[
    (uncertain["raw_class_labels"].str.strip() == "Person")
    & (uncertain["observations"] >= 2)
]

mixed = uncertain[
    uncertain["raw_class_labels"].apply(
        lambda s: "Person" in s.split("|")
        and any(
            c in s.split("|")
            for c in ("Car", "Motorcycle", "Bus", "Truck")
        )
    )
]

groups = [
    ("pedestrian", pedestrians),
    ("vehicle", vehicles),
    ("uncertain_person_only", select(person_only, 10, 44)),
    ("uncertain_mixed", select(mixed, 10, 45)),
]

selected = pd.concat(
    [
        group.assign(review_group=name)
        for name, group in groups
    ],
    ignore_index=True
)

selected = selected.sort_values(
    ["review_group", "video", "track_id"]
).reset_index(drop=True)

selected["review_id"] = [
    f"TRK-{i:03d}" for i in range(1, len(selected) + 1)
]

selected["review_decision"] = "UNREVIEWED"
selected["review_notes"] = ""
selected["review_sheet"] = ""
selected["sheet_status"] = "PENDING"

# --------------------------------------------------
# Generate contact sheets
# --------------------------------------------------

def safe_filename(name):
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def make_sheet(video_name, track_id, review_id):
    video_path = VIDEO_DIR / video_name

    if not video_path.is_file():
        return None, "VIDEO_MISSING"

    rows = detections[
        (detections["video"] == video_name)
        & (detections["track_id"] == track_id)
    ].sort_values("frame")

    if rows.empty:
        return None, "TRACK_MISSING"

    unique_frames = rows["frame"].drop_duplicates().tolist()

    indices = np.linspace(
        0,
        len(unique_frames) - 1,
        min(5, len(unique_frames)),
        dtype=int,
    )

    chosen_frames = [unique_frames[i] for i in indices]

    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        return None, "VIDEO_OPEN_FAILED"

    panels = []

    for frame_no in chosen_frames:
        # Existing CSV frame numbering is assumed zero-based.
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_no) - 1)
        ok, frame = cap.read()

        if not ok:
            continue

        frame_rows = rows[rows["frame"] == frame_no]

        for detection in frame_rows.itertuples(index=False):
            x1, y1, x2, y2 = map(
                int,
                [detection.x1, detection.y1,
                 detection.x2, detection.y2],
            )

            cv2.rectangle(
                frame, (x1, y1), (x2, y2),
                (0, 0, 255), 3
            )

            cv2.putText(
                frame,
                f"ID {track_id} | {detection.class_name}",
                (max(5, x1), max(25, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65, (0, 0, 255), 2,
            )

        frame = cv2.resize(frame, (640, 360))

        cv2.rectangle(
            frame, (0, 0), (640, 38),
            (20, 20, 20), -1
        )

        cv2.putText(
            frame,
            f"{review_id} | FRAME {frame_no}",
            (12, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65, (255, 255, 255), 2,
        )

        panels.append(frame)

    cap.release()

    if not panels:
        return None, "NO_READABLE_FRAMES"

    while len(panels) < 5:
        panels.append(np.zeros((360, 640, 3), dtype=np.uint8))

    blank = np.zeros((360, 640, 3), dtype=np.uint8)

    sheet = np.vstack([
        np.hstack(panels[:3]),
        np.hstack([panels[3], panels[4], blank]),
    ])

    filename = (
        f"{review_id}_"
        f"{safe_filename(Path(video_name).stem)}_"
        f"track_{track_id}.jpg"
    )

    output_path = SHEETS_DIR / filename

    if not cv2.imwrite(str(output_path), sheet):
        return None, "IMAGE_WRITE_FAILED"

    return str(output_path), "SUCCESS"


for idx, record in selected.iterrows():
    path, status = make_sheet(
        record["video"],
        int(record["track_id"]),
        record["review_id"],
    )

    selected.at[idx, "review_sheet"] = path or ""
    selected.at[idx, "sheet_status"] = status

    print(
        f"{record['review_id']} | "
        f"{record['review_group']} | "
        f"{status}"
    )

# --------------------------------------------------
# Save review manifest
# --------------------------------------------------

output_csv = OUTPUT_DIR / "test_track_review_manifest.csv"

selected.to_csv(output_csv, index=False)

print("\nREVIEW PACKAGE COMPLETE")
print("Selected tracks:", len(selected))
print("Successful sheets:",
      (selected["sheet_status"] == "SUCCESS").sum())
print("Review CSV:", output_csv)
print("Contact sheets:", SHEETS_DIR)
print("\nCategory counts:")
print(selected["review_group"].value_counts().to_string())
