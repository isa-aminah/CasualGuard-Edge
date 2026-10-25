"""YOLO person/vehicle detection with persistent ByteTrack IDs."""

from __future__ import annotations

import os
import math
import subprocess
import threading
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import streamlit as st

from video_library import videos_directory

MODEL_WEIGHTS = os.environ.get("CAUSALGUARD_YOLO_MODEL", "yolo26n.pt")
PERSON_CLASS_ID = 0
VEHICLE_CLASS_IDS = {2, 3, 5, 7}
TRACKED_CLASS_IDS = [PERSON_CLASS_ID, *sorted(VEHICLE_CLASS_IDS)]
_TRACKING_LOCK = threading.Lock()
ANALYSIS_VERSION = 3
TTC_MAX_SECONDS = 3.0
CPA_MAX_DISTANCE_PX = 80.0
RISK_DISTANCE_SCALE_PX = 8.0


@dataclass(frozen=True)
class VideoAnalysis:
    analysis_version: int
    processed_filename: str
    model_name: str
    video_codec: str
    frames_processed: int
    pedestrian_tracks: int
    vehicle_tracks: int
    pedestrian_detections: int
    vehicle_detections: int
    video_width: int
    video_height: int
    events: list[dict]


@st.cache_resource(show_spinner=False)
def _load_model(weights: str):
    from ultralytics import YOLO

    return YOLO(weights)


def _track_video(model, source: Path, confidence: float):
    with _TRACKING_LOCK:
        yield from model.track(
            source=str(source),
            stream=True,
            persist=False,
            tracker="bytetrack.yaml",
            classes=TRACKED_CLASS_IDS,
            conf=confidence,
            verbose=False,
        )


def _velocity_at(
    path: list[list[float]],
    index: int,
    window_seconds: float = 0.5,
) -> tuple[float, float] | None:
    """Fit local image-plane velocity around one synchronized track sample."""
    timestamp = path[index][0]
    half_window = window_seconds / 2
    start = index
    while start > 0 and timestamp - path[start - 1][0] <= half_window:
        start -= 1
    stop = index + 1
    while stop < len(path) and path[stop][0] - timestamp <= half_window:
        stop += 1
    points = path[start:stop]
    if len(points) < 2:
        points = path[max(0, index - 1):min(len(path), index + 2)]
    if len(points) < 2:
        return None

    mean_time = sum(point[0] for point in points) / len(points)
    time_variance = sum((point[0] - mean_time) ** 2 for point in points)
    if time_variance <= 0:
        return None
    mean_x = sum(point[1] for point in points) / len(points)
    mean_y = sum(point[2] for point in points) / len(points)
    velocity_x = sum(
        (point[0] - mean_time) * (point[1] - mean_x) for point in points
    ) / time_variance
    velocity_y = sum(
        (point[0] - mean_time) * (point[2] - mean_y) for point in points
    ) / time_variance
    return velocity_x, velocity_y


def calculate_cpa_metrics(
    pedestrian_path: list[list[float]],
    vehicle_path: list[list[float]],
) -> dict | None:
    """Calculate CPA, TTC, and risk from synchronized image-plane trajectories."""
    vehicle_by_time = {point[0]: point for point in vehicle_path}
    synchronized = [
        (point, vehicle_by_time[point[0]])
        for point in pedestrian_path
        if point[0] in vehicle_by_time
    ]
    if len(synchronized) < 2:
        return None

    pedestrian_synced = [pair[0] for pair in synchronized]
    vehicle_synced = [pair[1] for pair in synchronized]
    candidates = []
    for index, (pedestrian, vehicle) in enumerate(synchronized):
        pedestrian_velocity = _velocity_at(pedestrian_synced, index)
        vehicle_velocity = _velocity_at(vehicle_synced, index)
        if pedestrian_velocity is None or vehicle_velocity is None:
            continue

        relative_x = pedestrian[1] - vehicle[1]
        relative_y = pedestrian[2] - vehicle[2]
        relative_vx = pedestrian_velocity[0] - vehicle_velocity[0]
        relative_vy = pedestrian_velocity[1] - vehicle_velocity[1]
        relative_speed_squared = relative_vx**2 + relative_vy**2
        if relative_speed_squared <= 0:
            continue

        projection = relative_x * relative_vx + relative_y * relative_vy
        t_cpa = -projection / relative_speed_squared
        if t_cpa <= 0:
            continue

        d_cpa = math.hypot(
            relative_x + relative_vx * t_cpa,
            relative_y + relative_vy * t_cpa,
        )
        distance = math.hypot(relative_x, relative_y)
        closing_rate = -projection / max(distance, 1e-9)
        if closing_rate <= 0:
            continue

        ttc = distance / closing_rate
        time_risk = max(0.0, min(1.0, 1.0 - t_cpa / TTC_MAX_SECONDS))
        distance_risk = max(0.0, min(1.0, 1.0 - d_cpa / RISK_DISTANCE_SCALE_PX))
        candidates.append({
            "frame_time": pedestrian[0],
            "t_cpa": t_cpa,
            "d_cpa": d_cpa,
            "pedestrian_cpa": [
                pedestrian[1] + pedestrian_velocity[0] * t_cpa,
                pedestrian[2] + pedestrian_velocity[1] * t_cpa,
            ],
            "vehicle_cpa": [
                vehicle[1] + vehicle_velocity[0] * t_cpa,
                vehicle[2] + vehicle_velocity[1] * t_cpa,
            ],
            "distance": distance,
            "closing_rate": closing_rate,
            "ttc": ttc,
            "time_risk": time_risk,
            "distance_risk": distance_risk,
            "risk_score": 0.5 * time_risk + 0.5 * distance_risk,
        })

    if not candidates:
        return None
    return min(candidates, key=lambda item: (item["d_cpa"], item["t_cpa"]))


def _circle_occupancy_intervals(
    path: list[list[float]],
    center: tuple[float, float],
    radius: float,
) -> list[tuple[float, float]]:
    """Find contiguous time intervals where a track center occupies a circular zone."""
    if len(path) < 2 or radius <= 0:
        return []

    intervals: list[tuple[float, float]] = []
    for before, after in zip(path, path[1:]):
        duration = after[0] - before[0]
        if duration <= 0:
            continue
        x0, y0 = before[1] - center[0], before[2] - center[1]
        dx, dy = after[1] - before[1], after[2] - before[2]
        a = dx * dx + dy * dy
        if a <= 0:
            if x0 * x0 + y0 * y0 <= radius * radius:
                intervals.append((before[0], after[0]))
            continue

        b = 2 * (x0 * dx + y0 * dy)
        c = x0 * x0 + y0 * y0 - radius * radius
        discriminant = b * b - 4 * a * c
        breakpoints = [0.0, 1.0]
        if discriminant >= 0:
            root = math.sqrt(discriminant)
            breakpoints.extend(
                value
                for value in ((-b - root) / (2 * a), (-b + root) / (2 * a))
                if 0.0 < value < 1.0
            )
        breakpoints.sort()

        for start, stop in zip(breakpoints, breakpoints[1:]):
            midpoint = (start + stop) / 2
            midpoint_x = x0 + dx * midpoint
            midpoint_y = y0 + dy * midpoint
            if midpoint_x * midpoint_x + midpoint_y * midpoint_y <= radius * radius:
                interval = (
                    before[0] + duration * start,
                    before[0] + duration * stop,
                )
                if intervals and interval[0] <= intervals[-1][1] + 1e-9:
                    intervals[-1] = (intervals[-1][0], interval[1])
                else:
                    intervals.append(interval)
    return intervals



def calculate_pet(
    pedestrian_path: list[list[float]],
    vehicle_path: list[list[float]],
    conflict_center: tuple[float, float],
    conflict_radius: float,
) -> float | None:
    """Calculate signed PET from both tracks' occupancy of one estimated zone."""
    if len(pedestrian_path) < 2 or len(vehicle_path) < 2:
        return None

    pedestrian_intervals = _circle_occupancy_intervals(
        pedestrian_path, conflict_center, conflict_radius
    )
    vehicle_intervals = _circle_occupancy_intervals(
        vehicle_path, conflict_center, conflict_radius
    )

    if len(pedestrian_intervals) != 1 or len(vehicle_intervals) != 1:
        return None

    first, second = sorted(
        (pedestrian_intervals[0], vehicle_intervals[0]),
        key=lambda interval: interval[1],
    )
    return round(second[0] - first[1], 3)


def risk_level(score: float) -> str:
    if score < 0.30:
        return "Low"
    if score < 0.60:
        return "Medium"
    return "High"


def qualifies_near_miss(metrics: dict) -> bool:
    return (
        0 < metrics["t_cpa"] <= TTC_MAX_SECONDS
        and metrics["d_cpa"] <= CPA_MAX_DISTANCE_PX
        and metrics["closing_rate"] > 0
    )


def estimate_ttc(
    pedestrian_path: list[list[float]],
    vehicle_path: list[list[float]],
) -> float | None:
    """Return TTC for the closest future approach in synchronized tracks."""
    metrics = calculate_cpa_metrics(pedestrian_path, vehicle_path)
    return round(metrics["ttc"], 2) if metrics else None


def analyze_video(
    video_path: Path,
    video_id: str,
    confidence: float = 0.25,
    progress_callback: Callable[[float, str], None] | None = None,
) -> dict:
    """Track the complete clip, save an annotated MP4, and return aggregate counts."""
    import cv2

    source = Path(video_path)
    if not source.is_file():
        raise FileNotFoundError(f"Saved video was not found: {source}")
    if not 0.0 < confidence < 1.0:
        raise ValueError("Confidence must be greater than 0 and less than 1.")

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        capture.release()
        raise ValueError("OpenCV could not open this video. Check that the file is a valid, supported video.")
    reported_frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    capture.release()
    frame_count = reported_frame_count if reported_frame_count > 0 else None
    if not math.isfinite(fps) or fps <= 0:
        fps = 25.0

    model = _load_model(MODEL_WEIGHTS)
    output_directory = videos_directory()
    output_directory.mkdir(parents=True, exist_ok=True)
    processed_filename = f"{video_id}_tracked.mp4"
    output_path = output_directory / processed_filename
    temporary_path = output_directory / f".{uuid.uuid4().hex}_raw.mp4"
    encoded_path = output_directory / f".{uuid.uuid4().hex}_h264.mp4"
    writer = None
    frames_processed = 0
    person_tracks: set[int] = set()
    vehicle_tracks: set[int] = set()
    pedestrian_detections = 0
    vehicle_detections = 0
    tracked_objects: dict[int, dict] = {}
    video_width = 0
    video_height = 0
    update_interval = max(1, (frame_count or 100) // 100)

    try:
        for result in _track_video(model, source, confidence):
            frame = result.plot()
            if writer is None:
                height, width = frame.shape[:2]
                video_width, video_height = width, height
                writer = cv2.VideoWriter(
                    str(temporary_path),
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    fps,
                    (width, height),
                )
                if not writer.isOpened():
                    raise RuntimeError("OpenCV could not create an annotated MP4 output.")
            writer.write(frame)
            frames_processed += 1

            boxes = result.boxes
            if boxes is not None and len(boxes):
                class_ids = boxes.cls.int().cpu().tolist()
                track_ids = boxes.id.int().cpu().tolist() if boxes.id is not None else [None] * len(class_ids)
                coordinates = boxes.xyxy.cpu().tolist()
                for class_id, track_id, box in zip(class_ids, track_ids, coordinates):
                    if track_id is None:
                        continue
                    x1, y1, x2, y2 = (float(value) for value in box)
                    observation = {
                        "frame": frames_processed - 1,
                        "time": (frames_processed - 1) / fps,
                        "x": (x1 + x2) / 2,
                        "y": (y1 + y2) / 2,
                        "box": [x1, y1, x2, y2],
                    }
                    if class_id == PERSON_CLASS_ID:
                        pedestrian_detections += 1
                        person_tracks.add(track_id)
                        tracked_objects.setdefault(track_id, {"kind": "pedestrian", "observations": []})[
                            "observations"
                        ].append(observation)
                    elif class_id in VEHICLE_CLASS_IDS:
                        vehicle_detections += 1
                        vehicle_tracks.add(track_id)
                        tracked_objects.setdefault(track_id, {"kind": "vehicle", "observations": []})[
                            "observations"
                        ].append(observation)

            if progress_callback and (
                frames_processed % update_interval == 0
                or (frame_count is not None and frames_processed == frame_count)
            ):
                progress = (
                    min(frames_processed / frame_count, 0.99)
                    if frame_count is not None
                    else min(frames_processed / (frames_processed + 100), 0.99)
                )
                total = f"of {frame_count:,}" if frame_count is not None else "(total unknown)"
                progress_callback(
                    progress,
                    f"Tracking frame {frames_processed:,} {total}",
                )

        if writer is None or frames_processed == 0:
            raise ValueError("No video frames were decoded. Try re-encoding the clip as MP4.")
        writer.release()
        writer = None
        if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
            raise RuntimeError("Video processing completed without producing an output file.")
        _encode_browser_mp4(temporary_path, encoded_path, source_audio=source)
        os.replace(encoded_path, output_path)
        temporary_path.unlink()
        events = _build_interaction_events(
            tracked_objects,
            video_id=video_id,
            fps=fps,
        )
        if progress_callback:
            progress_callback(1.0, "Detection and ByteTrack analysis complete.")

        return asdict(
            VideoAnalysis(
                analysis_version=ANALYSIS_VERSION,
                processed_filename=processed_filename,
                model_name=MODEL_WEIGHTS,
                video_codec="h264",
                frames_processed=frames_processed,
                pedestrian_tracks=len(person_tracks),
                vehicle_tracks=len(vehicle_tracks),
                pedestrian_detections=pedestrian_detections,
                vehicle_detections=vehicle_detections,
                video_width=video_width,
                video_height=video_height,
                events=events,
            )
        )
    finally:
        if writer is not None:
            writer.release()
        for temporary_file in (temporary_path, encoded_path):
            if temporary_file.exists():
                temporary_file.unlink()


def _encode_browser_mp4(
    source_path: Path,
    output_path: Path,
    source_audio: Path | None = None,
) -> None:
    """Transcode the OpenCV MPEG-4 intermediate to browser-compatible H.264."""
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError(
            "H.264 video support is unavailable. Install project dependencies with "
            "`python -m pip install -r requirements.txt`."
        ) from exc

    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source_path),
    ]
    if source_audio is not None:
        command.extend(["-i", str(source_audio)])
    command.extend([
        "-map",
        "0:v:0",
    ])
    if source_audio is not None:
        command.extend(["-map", "1:a:0?"])
    else:
        command.append("-an")
    command.extend([
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
    ])
    if source_audio is not None:
        command.extend(["-c:a", "aac", "-shortest"])
    command.extend([
        "-movflags",
        "+faststart",
        str(output_path),
    ])
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=3600,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Could not encode the annotated clip as browser-compatible H.264: {exc}") from exc
    if completed.returncode != 0:
        message = completed.stderr.strip() or "FFmpeg returned an unknown encoding error."
        raise RuntimeError(f"Could not encode the annotated clip as browser-compatible H.264: {message}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("H.264 encoding completed without producing a video file.")


def _build_interaction_events(
    tracked_objects: dict[int, dict],
    video_id: str,
    fps: float,
) -> list[dict]:
    """Find CPA-qualified pedestrian/vehicle pairs and calculate image-plane risk."""
    pedestrians = {
        track_id: data
        for track_id, data in tracked_objects.items()
        if data["kind"] == "pedestrian"
    }
    vehicles = {
        track_id: data
        for track_id, data in tracked_objects.items()
        if data["kind"] == "vehicle"
    }
    events = []

    for pedestrian_id, pedestrian in pedestrians.items():
        pedestrian_by_frame = {
            item["frame"]: item for item in pedestrian["observations"]
        }
        for vehicle_id, vehicle in vehicles.items():
            vehicle_by_frame = {item["frame"]: item for item in vehicle["observations"]}
            common_frames = sorted(pedestrian_by_frame.keys() & vehicle_by_frame.keys())
            if not common_frames:
                continue
            shared_observation_duration = (
                common_frames[-1] - common_frames[0]
            ) / fps

            if not common_frames:
                continue

            pedestrian_path_all = [
                [
                    pedestrian_by_frame[frame]["time"],
                    pedestrian_by_frame[frame]["x"],
                    pedestrian_by_frame[frame]["y"],
                ]
                for frame in common_frames
            ]
            vehicle_path_all = [
                [
                    vehicle_by_frame[frame]["time"],
                    vehicle_by_frame[frame]["x"],
                    vehicle_by_frame[frame]["y"],
                ]
                for frame in common_frames
            ]
            cpa = calculate_cpa_metrics(pedestrian_path_all, vehicle_path_all)
            if cpa is None or not qualifies_near_miss(cpa):
                continue

            if len(common_frames) > 1:
                first_frame, last_frame = common_frames[0], common_frames[-1]
                elapsed = (last_frame - first_frame) / fps
                if elapsed > 0:
                    first_ped, first_vehicle = (
                        pedestrian_by_frame[first_frame],
                        vehicle_by_frame[first_frame],
                    )
                    last_ped, last_vehicle = (
                        pedestrian_by_frame[last_frame],
                        vehicle_by_frame[last_frame],
                    )
                    rx0, ry0 = first_ped["x"] - first_vehicle["x"], first_ped["y"] - first_vehicle["y"]
                    rx1, ry1 = last_ped["x"] - last_vehicle["x"], last_ped["y"] - last_vehicle["y"]
                    relative_vx, relative_vy = (rx1 - rx0) / elapsed, (ry1 - ry0) / elapsed
                    relative_speed = math.hypot(relative_vx, relative_vy)
                    duration = elapsed
                    pedestrian_speed = math.hypot(
                        last_ped["x"] - first_ped["x"], last_ped["y"] - first_ped["y"]
                    ) / duration
                    vehicle_speed = math.hypot(
                        last_vehicle["x"] - first_vehicle["x"],
                        last_vehicle["y"] - first_vehicle["y"],
                    ) / duration
                else:
                    relative_speed = pedestrian_speed = vehicle_speed = 0.0
            else:
                relative_speed = pedestrian_speed = vehicle_speed = 0.0
            risk_score = round(cpa["risk_score"], 3)
            event_number = len(events) + 1
            pedestrian_observations = pedestrian["observations"]
            vehicle_observations = vehicle["observations"]

            def make_track_path(observations: list[dict]) -> list[list[float]]:
                stride = max(1, len(observations) // 300)
                sampled = observations[::stride]
                if sampled[-1] is not observations[-1]:
                    sampled.append(observations[-1])
                return [
                    [
                        round(item["time"], 3),
                        round(item["x"], 1),
                        round(item["y"], 1),
                    ]
                    for item in sampled
                ]

            pedestrian_path = make_track_path(pedestrian_observations)
            vehicle_path = make_track_path(vehicle_observations)
            conflict_center = (
                (cpa["pedestrian_cpa"][0] + cpa["vehicle_cpa"][0]) / 2,
                (cpa["pedestrian_cpa"][1] + cpa["vehicle_cpa"][1]) / 2,
            )

            def median_detection_radius(observations: list[dict]) -> float:
                radii = [
                    math.hypot(item["box"][2] - item["box"][0], item["box"][3] - item["box"][1]) / 2
                    for item in observations
                ]
                return sorted(radii)[len(radii) // 2]

            conflict_radius = max(
                (median_detection_radius(pedestrian_observations)
                 + median_detection_radius(vehicle_observations)) / 2,
                cpa["d_cpa"] / 2,
                1.0,
            )
            pet = calculate_pet(
                pedestrian_path,
                vehicle_path,
                conflict_center,
                conflict_radius,
            )
            closest_frame = round(cpa["frame_time"] * fps)
            events.append(
                {
                    "event_id": f"{video_id[:6].upper()}-{event_number:03}",
                    "interaction": f"P{pedestrian_id:02} - V{vehicle_id:02}",
                    "pedestrian_track_id": pedestrian_id,
                    "vehicle_track_id": vehicle_id,
                    "time": f"{closest_frame / fps:.2f}",
                    "time_seconds": round(closest_frame / fps, 3),
                    "distance": round(cpa["d_cpa"], 1),
                    "distance_unit": "px",
                    "relative_motion": "Closing",
                    "ttc": round(cpa["ttc"], 2),
                    "t_cpa": round(cpa["t_cpa"], 3),
                    "d_cpa": round(cpa["d_cpa"], 1),
                    "closing_rate": round(cpa["closing_rate"], 1),
                    "risk_time_component": round(cpa["time_risk"], 3),
                    "risk_distance_component": round(cpa["distance_risk"], 3),
                    "pet": pet,
                    "shared_observation_duration_s": round(shared_observation_duration, 3),
                    "trajectory_coverage_warning": (
                        shared_observation_duration < 1.0
                    ),
                    "conflict_zone": {
                        "center": [round(conflict_center[0], 1), round(conflict_center[1], 1)],
                        "radius": round(conflict_radius, 1),
                        "definition": "CPA midpoint with radius estimated from median detection-box sizes",
                    },
                    "pedestrian_speed": round(pedestrian_speed, 1),
                    "vehicle_speed": round(vehicle_speed, 1),
                    "speed_unit": "px/s",
                    "relative_speed": round(relative_speed, 1),
                    "risk_score": risk_score,
                    "risk_level": risk_level(risk_score),
                    "location": "Uncalibrated image coordinates",
                    "calibrated": False,
                    "pedestrian_path": pedestrian_path,
                    "vehicle_path": vehicle_path,
                }
            )
    return sorted(events, key=lambda event: (event["time_seconds"], -event["risk_score"]))
