"""Alert records derived from persisted YOLO + ByteTrack interaction analysis."""

from __future__ import annotations

import math

from app.video_processing import CPA_MAX_DISTANCE_PX, TTC_MAX_SECONDS, qualifies_near_miss

HIGH_RISK_THRESHOLD = 0.60


def evaluate_video_alert(analysis: object) -> dict:
    """Return the highest valid saved risk result for one selected video analysis."""
    if analysis is None:
        return {"status": "Analysis Required", "event": None}
    if not isinstance(analysis, dict):
        return {"status": "Insufficient Data", "event": None}

    events = analysis.get("events")
    if not isinstance(events, list):
        return {"status": "Insufficient Data", "event": None}

    valid_events = []
    for event in events:
        if not isinstance(event, dict):
            continue
        score = event.get("risk_score")
        timestamp = event.get("time_seconds")
        event_id = event.get("event_id")
        pedestrian_id = event.get("pedestrian_track_id")
        vehicle_id = event.get("vehicle_track_id")
        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not math.isfinite(score)
            or not 0 <= score <= 1
            or not isinstance(timestamp, (int, float))
            or isinstance(timestamp, bool)
            or not math.isfinite(timestamp)
            or not isinstance(event_id, str)
            or not event_id.strip()
            or pedestrian_id is None
            or vehicle_id is None
        ):
            continue
        valid_events.append(event)

    if not valid_events:
        return {"status": "Insufficient Data", "event": None}

    highest_risk_event = max(valid_events, key=lambda event: event["risk_score"])
    return {
        "status": (
            "ALERT TRIGGERED"
            if highest_risk_event["risk_score"] >= HIGH_RISK_THRESHOLD
            else "No High-Risk Alert"
        ),
        "event": highest_risk_event,
    }


def consecutive_candidate_observations(event: dict) -> int:
    """Count consecutive synchronized saved samples satisfying the existing CPA rule."""
    pedestrian_path = event.get("pedestrian_path")
    vehicle_path = event.get("vehicle_path")
    if not isinstance(pedestrian_path, list) or not isinstance(vehicle_path, list):
        return 0
    vehicle_by_time = {
        point[0]: point
        for point in vehicle_path
        if isinstance(point, list)
        and len(point) >= 3
        and all(isinstance(value, (int, float)) and math.isfinite(value) for value in point[:3])
    }
    synchronized = [
        (point, vehicle_by_time[point[0]])
        for point in pedestrian_path
        if isinstance(point, list)
        and len(point) >= 3
        and all(isinstance(value, (int, float)) and math.isfinite(value) for value in point[:3])
        and point[0] in vehicle_by_time
    ]
    if len(synchronized) < 2:
        return 0

    longest_streak = streak = 0
    for index, (pedestrian, vehicle) in enumerate(synchronized):
        before_index = max(0, index - 1)
        after_index = min(len(synchronized) - 1, index + 1)
        if before_index == after_index:
            streak = 0
            continue
        before_time = synchronized[before_index][0][0]
        after_time = synchronized[after_index][0][0]
        duration = after_time - before_time
        if duration <= 0:
            streak = 0
            continue

        pedestrian_before, vehicle_before = synchronized[before_index]
        pedestrian_after, vehicle_after = synchronized[after_index]
        pedestrian_velocity = (
            (pedestrian_after[1] - pedestrian_before[1]) / duration,
            (pedestrian_after[2] - pedestrian_before[2]) / duration,
        )
        vehicle_velocity = (
            (vehicle_after[1] - vehicle_before[1]) / duration,
            (vehicle_after[2] - vehicle_before[2]) / duration,
        )
        relative_x = pedestrian[1] - vehicle[1]
        relative_y = pedestrian[2] - vehicle[2]
        relative_vx = pedestrian_velocity[0] - vehicle_velocity[0]
        relative_vy = pedestrian_velocity[1] - vehicle_velocity[1]
        speed_squared = relative_vx**2 + relative_vy**2
        if speed_squared <= 0:
            streak = 0
            continue

        projection = relative_x * relative_vx + relative_y * relative_vy
        t_cpa = -projection / speed_squared
        distance = math.hypot(relative_x, relative_y)
        closing_rate = -projection / max(distance, 1e-9)
        d_cpa = math.hypot(
            relative_x + relative_vx * t_cpa,
            relative_y + relative_vy * t_cpa,
        )
        if (
            0 < t_cpa <= TTC_MAX_SECONDS
            and d_cpa <= CPA_MAX_DISTANCE_PX
            and closing_rate > 0
        ):
            streak += 1
            longest_streak = max(longest_streak, streak)
        else:
            streak = 0
    return longest_streak


def alert_severity(score: float, settings: dict) -> str:
    if score >= settings["high_threshold"]:
        return "High"
    if score >= settings["medium_threshold"]:
        return "Medium"
    return "Low"


def build_alert_records(
    videos: list[dict],
    settings: dict,
    reviews: dict[tuple[str, str], str],
) -> list[dict]:
    """Project the saved event records into alert rows, preserving review status."""
    alerts = []
    for video in videos:
        video_id = video["video_id"]
        analysis = video.get("analysis") or {}
        events = analysis.get("events", [])
        if not isinstance(events, list):
            continue
        for event in events:
            score = event.get("risk_score")
            if (
                not isinstance(score, (int, float))
                or not math.isfinite(score)
                or any(event.get(field) is None for field in ("t_cpa", "d_cpa", "closing_rate"))
                or not qualifies_near_miss(event)
                or event.get("time_seconds") is None
            ):
                continue
            consecutive = consecutive_candidate_observations(event)
            required = settings["min_consecutive_observations"]
            if consecutive < required:
                continue
            alerts.append(
                {
                    "video_id": video_id,
                    "video_name": video.get("original_name", video_id),
                    "processed_at": video.get("processed_at", ""),
                    "event": event,
                    "event_id": event["event_id"],
                    "interaction": event["interaction"],
                    "time_seconds": float(event["time_seconds"]),
                    "risk_score": float(score),
                    "risk_level": alert_severity(float(score), settings),
                    "consecutive_observations": consecutive,
                    "trigger_reason": (
                        f"CPA rule: 0 < tCPA ≤ {TTC_MAX_SECONDS:.1f}s, "
                        f"dCPA ≤ {CPA_MAX_DISTANCE_PX:.0f}px, closing speed > 0; "
                        f"{consecutive} consecutive saved observations"
                    ),
                    "status": reviews.get((video_id, event["event_id"]), "New"),
                }
            )

    alerts.sort(key=lambda alert: (alert["time_seconds"], alert["video_id"], alert["event_id"]))
    if settings["duplicate_suppression"]:
        filtered = []
        last_seen: dict[tuple[str, str], float] = {}
        window = float(settings["duplicate_window_seconds"])
        for alert in alerts:
            key = (alert["video_id"], alert["interaction"])
            previous_time = last_seen.get(key)
            if previous_time is not None and abs(alert["time_seconds"] - previous_time) <= window:
                continue
            filtered.append(alert)
            last_seen[key] = alert["time_seconds"]
        alerts = filtered
    return alerts
