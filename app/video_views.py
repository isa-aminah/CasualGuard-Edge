"""Video preview components shared by all analysis pages."""

import streamlit as st

from app.components import show_actual_video


def render_video_pair(video: dict) -> None:
    """Show the saved source clip beside its YOLO + ByteTrack annotated output."""
    show_actual_video(video)
