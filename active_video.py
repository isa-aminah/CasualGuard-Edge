"""Session-state helpers shared by pages that inspect a video event."""

from __future__ import annotations

import streamlit as st


DEFAULT_EVENT_ID = "E003"
DEFAULT_TIMESTAMP = 12.4


def initialize() -> None:
    """Set predictable defaults without overwriting a user's current selection."""
    st.session_state.setdefault("active_event_id", DEFAULT_EVENT_ID)
    st.session_state.setdefault("active_video_timestamp", DEFAULT_TIMESTAMP)
    st.session_state.setdefault("active_video_id", None)


def set_active_event(event_id: str) -> None:
    st.session_state["active_event_id"] = event_id


def get_active_event() -> str:
    initialize()
    return str(st.session_state["active_event_id"])


def set_timestamp(timestamp: float) -> None:
    st.session_state["active_video_timestamp"] = max(0.0, float(timestamp))


def get_timestamp() -> float:
    initialize()
    return float(st.session_state["active_video_timestamp"])


def set_active_video(video_id: str | None) -> None:
    st.session_state["active_video_id"] = video_id


def get_active_video() -> str | None:
    initialize()
    return st.session_state.get("active_video_id")
