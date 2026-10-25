"""Persistent server-side storage for uploaded video clips and analysis results."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Iterator

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
MAX_VIDEO_BYTES = 500 * 1024 * 1024
DEFAULT_DATA_DIRECTORY = Path(__file__).resolve().parent / "data"
DEFAULT_ALERT_SETTINGS = {
    "medium_threshold": 0.30,
    "high_threshold": 0.60,
    "min_consecutive_observations": 1,
    "duplicate_suppression": True,
    "duplicate_window_seconds": 5.0,
    "sound_notifications": False,
    "show_low": False,
    "show_medium": True,
    "show_high": True,
}
ALERT_STATUSES = {"New", "Acknowledged", "Resolved"}


class VideoLibraryError(ValueError):
    """An upload or library operation failed with a user-correctable problem."""


def storage_directory() -> Path:
    configured = os.environ.get("CAUSALGUARD_DATA_DIR")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DATA_DIRECTORY


def videos_directory() -> Path:
    return storage_directory() / "videos"


def database_path() -> Path:
    return storage_directory() / "causalguard.sqlite3"


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                original_name TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL,
                processed_filename TEXT,
                processed_at TEXT,
                model_name TEXT,
                frames_processed INTEGER,
                pedestrian_tracks INTEGER,
                vehicle_tracks INTEGER,
                pedestrian_detections INTEGER,
                vehicle_detections INTEGER
            )
            """
        )
        existing_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(videos)")
        }
        if "analysis_json" not in existing_columns:
            connection.execute("ALTER TABLE videos ADD COLUMN analysis_json TEXT")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_reviews (
                video_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'New',
                updated_at TEXT NOT NULL,
                PRIMARY KEY (video_id, event_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _display_name(original_name: str) -> str:
    name = Path(original_name.replace("\\", "/")).name
    if not name or name in {".", ".."}:
        raise VideoLibraryError("Choose a video file with a valid filename.")
    return name


def save_video(data: bytes | BinaryIO, original_name: str) -> dict:
    """Persist an upload atomically and return its durable library record."""
    name = _display_name(original_name)
    extension = Path(name).suffix.lower()
    if extension not in SUPPORTED_VIDEO_EXTENSIONS:
        raise VideoLibraryError("Supported formats: MP4, MOV, AVI, MKV, and WEBM.")

    contents = data if isinstance(data, bytes) else data.read()
    if not contents:
        raise VideoLibraryError("The uploaded video is empty.")
    if len(contents) > MAX_VIDEO_BYTES:
        raise VideoLibraryError("The video exceeds the 500 MB upload limit.")

    video_id = hashlib.sha256(contents).hexdigest()
    directory = videos_directory()
    directory.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{video_id}{extension}"
    destination = directory / stored_filename

    with _connect() as connection:
        existing = connection.execute(
            "SELECT * FROM videos WHERE video_id = ?", (video_id,)
        ).fetchone()
        if existing:
            return dict(existing)

        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=directory, prefix=".upload-", suffix=extension, delete=False
            ) as temporary_file:
                temporary_name = temporary_file.name
                temporary_file.write(contents)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_name, destination)
            temporary_name = None
            connection.execute(
                """
                INSERT INTO videos (
                    video_id, original_name, stored_filename, size_bytes, uploaded_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    video_id,
                    name,
                    stored_filename,
                    len(contents),
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )
        finally:
            if temporary_name and os.path.exists(temporary_name):
                os.unlink(temporary_name)

        row = connection.execute(
            "SELECT * FROM videos WHERE video_id = ?", (video_id,)
        ).fetchone()
        return dict(row)


def list_videos() -> list[dict]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT video_id, original_name, stored_filename, size_bytes, uploaded_at,
                   processed_filename, processed_at, model_name, frames_processed,
                   pedestrian_tracks, vehicle_tracks, pedestrian_detections,
                   vehicle_detections
            FROM videos
            ORDER BY uploaded_at DESC, original_name COLLATE NOCASE
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_video(video_id: str) -> dict | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM videos WHERE video_id = ?", (video_id,)
        ).fetchone()
    if row is None:
        return None
    video = dict(row)
    analysis_json = video.pop("analysis_json", None)
    video["analysis"] = json.loads(analysis_json) if analysis_json else None
    return video


def get_analysis(video_id: str) -> dict | None:
    video = get_video(video_id)
    return video.get("analysis") if video else None


def delete_video(video_id: str) -> None:
    """Remove one saved video, its analysis, and its generated tracked clip."""
    if not re.fullmatch(r"[0-9a-f]{64}", video_id):
        raise VideoLibraryError("The saved video ID is invalid.")

    directory = videos_directory()
    staged_files: list[tuple[Path, Path]] = []
    try:
        with _connect() as connection:
            row = connection.execute(
                "SELECT stored_filename, processed_filename FROM videos WHERE video_id = ?",
                (video_id,),
            ).fetchone()
            if row is None:
                raise VideoLibraryError("This video is no longer in the saved library.")

            stored_filename = row["stored_filename"]
            if not re.fullmatch(
                rf"{re.escape(video_id)}\.(?:mp4|mov|avi|mkv|webm)",
                stored_filename,
            ):
                raise VideoLibraryError("The saved video filename is invalid; no files were deleted.")
            filenames = [stored_filename]

            processed_filename = row["processed_filename"]
            if processed_filename:
                if processed_filename != f"{video_id}_tracked.mp4":
                    raise VideoLibraryError(
                        "The tracked video filename is invalid; no files were deleted."
                    )
                filenames.append(processed_filename)

            for filename in filenames:
                original_path = directory / filename
                if original_path.is_file():
                    staged_path = directory / f".delete-{uuid.uuid4().hex}-{filename}"
                    os.replace(original_path, staged_path)
                    staged_files.append((original_path, staged_path))

            cursor = connection.execute(
                "DELETE FROM videos WHERE video_id = ?",
                (video_id,),
            )
            if cursor.rowcount != 1:
                raise VideoLibraryError("This video is no longer in the saved library.")
            connection.execute(
                "DELETE FROM alert_reviews WHERE video_id = ?",
                (video_id,),
            )
    except Exception as exc:
        restore_errors = []
        for original_path, staged_path in reversed(staged_files):
            try:
                os.replace(staged_path, original_path)
            except OSError as restore_error:
                restore_errors.append(str(restore_error))
        if restore_errors:
            raise VideoLibraryError(
                "Video deletion failed and one or more files could not be restored: "
                + "; ".join(restore_errors)
            ) from exc
        raise

    cleanup_errors = []
    for _, staged_path in staged_files:
        try:
            staged_path.unlink()
        except OSError as exc:
            cleanup_errors.append(str(exc))
    if cleanup_errors:
        raise VideoLibraryError(
            "The video was removed from the library, but stored file cleanup was incomplete: "
            + "; ".join(cleanup_errors)
        )


def analysis_is_current(video: dict, model_name: str) -> bool:
    """Return whether this saved analysis matches the active model and playable output."""
    analysis = video.get("analysis") or {}
    from app.video_processing import ANALYSIS_VERSION

    output = processed_path(video)
    return bool(
        analysis
        and analysis.get("model_name") == model_name
        and analysis.get("analysis_version") == ANALYSIS_VERSION
        and analysis.get("video_codec") in {None, "h264"}
        and output
        and output.is_file()
        and output.stat().st_size > 0
    )


def source_path(video: dict) -> Path:
    return videos_directory() / video["stored_filename"]


def processed_path(video: dict) -> Path | None:
    filename = video.get("processed_filename")
    return videos_directory() / filename if filename else None


def record_analysis(video_id: str, result: dict) -> None:
    processed_filename = Path(result["processed_filename"]).name
    if processed_filename != f"{video_id}_tracked.mp4" or not re.fullmatch(
        r"[0-9a-f]{64}_tracked\.mp4", processed_filename
    ):
        raise VideoLibraryError("The generated analysis video filename is invalid.")
    with _connect() as connection:
        cursor = connection.execute(
            """
            UPDATE videos SET
                processed_filename = ?, processed_at = ?, model_name = ?,
                frames_processed = ?, pedestrian_tracks = ?, vehicle_tracks = ?,
                pedestrian_detections = ?, vehicle_detections = ?, analysis_json = ?
            WHERE video_id = ?
            """,
            (
                processed_filename,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                result["model_name"],
                result["frames_processed"],
                result["pedestrian_tracks"],
                result["vehicle_tracks"],
                result["pedestrian_detections"],
                result["vehicle_detections"],
                json.dumps(result, separators=(",", ":")),
                video_id,
            ),
        )
        if cursor.rowcount != 1:
            raise VideoLibraryError("This video is no longer in the saved library.")
        connection.execute(
            "DELETE FROM alert_reviews WHERE video_id = ?",
            (video_id,),
        )


def get_alert_settings() -> dict:
    with _connect() as connection:
        row = connection.execute(
            "SELECT setting_json FROM app_settings WHERE setting_key = 'alert_settings'"
        ).fetchone()
    if row is None:
        return dict(DEFAULT_ALERT_SETTINGS)
    try:
        saved = json.loads(row["setting_json"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise VideoLibraryError("Saved alert settings are invalid; review or reset the configuration.") from exc
    return {**DEFAULT_ALERT_SETTINGS, **saved}


def save_alert_settings(settings: dict) -> dict:
    medium_threshold = settings.get("medium_threshold")
    high_threshold = settings.get("high_threshold")
    min_observations = settings.get("min_consecutive_observations")
    duplicate_window = settings.get("duplicate_window_seconds")
    if (
        not isinstance(medium_threshold, (int, float))
        or isinstance(medium_threshold, bool)
        or not math.isfinite(medium_threshold)
        or not isinstance(high_threshold, (int, float))
        or isinstance(high_threshold, bool)
        or not math.isfinite(high_threshold)
        or not 0 <= medium_threshold < high_threshold <= 1
    ):
        raise VideoLibraryError("Risk thresholds must satisfy 0 ≤ medium < high ≤ 1.")
    if (
        not isinstance(min_observations, int)
        or isinstance(min_observations, bool)
        or not 1 <= min_observations <= 100
    ):
        raise VideoLibraryError("Minimum consecutive observations must be an integer from 1 to 100.")
    if (
        not isinstance(duplicate_window, (int, float))
        or isinstance(duplicate_window, bool)
        or not math.isfinite(duplicate_window)
        or duplicate_window < 0
        or duplicate_window > 300
    ):
        raise VideoLibraryError("Duplicate suppression window must be between 0 and 300 seconds.")
    for key in ("duplicate_suppression", "sound_notifications", "show_low", "show_medium", "show_high"):
        if not isinstance(settings.get(key), bool):
            raise VideoLibraryError(f"Alert setting '{key}' must be enabled or disabled.")

    normalized = {
        **DEFAULT_ALERT_SETTINGS,
        "medium_threshold": float(medium_threshold),
        "high_threshold": float(high_threshold),
        "min_consecutive_observations": min_observations,
        "duplicate_window_seconds": float(duplicate_window),
        **{
            key: settings[key]
            for key in (
                "duplicate_suppression",
                "sound_notifications",
                "show_low",
                "show_medium",
                "show_high",
            )
        },
    }
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO app_settings (setting_key, setting_json, updated_at)
            VALUES ('alert_settings', ?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_json = excluded.setting_json,
                updated_at = excluded.updated_at
            """,
            (
                json.dumps(normalized, separators=(",", ":")),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
    return normalized


def get_alert_reviews() -> dict[tuple[str, str], str]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT video_id, event_id, status FROM alert_reviews"
        ).fetchall()
    return {(row["video_id"], row["event_id"]): row["status"] for row in rows}


def set_alert_status(video_id: str, event_id: str, status: str) -> None:
    if status not in ALERT_STATUSES:
        raise VideoLibraryError(f"Alert status must be one of: {', '.join(sorted(ALERT_STATUSES))}.")
    if not video_id or not event_id:
        raise VideoLibraryError("A saved video ID and event ID are required to update alert status.")
    with _connect() as connection:
        exists = connection.execute(
            "SELECT 1 FROM videos WHERE video_id = ?",
            (video_id,),
        ).fetchone()
        if exists is None:
            raise VideoLibraryError("This alert's source video is no longer in the saved library.")
        connection.execute(
            """
            INSERT INTO alert_reviews (video_id, event_id, status, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(video_id, event_id) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (
                video_id,
                event_id,
                status,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
