"""Operational overview dashboard."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from active_video import get_active_video, set_active_video
from app.components import html_table, status_badge
from app.video_processing import MODEL_WEIGHTS
from app.video_views import render_video_pair
from navigation import page_header
from video_library import analysis_is_current, get_video, list_videos


def _latest_event_rows(events: list[dict]) -> list[list[str]]:
    return [
        [
            f"{event['time']} s",
            event["interaction"],
            f"{event['d_cpa']:.1f} px",
            f"{event['t_cpa']:.2f} s",
            f"{event['pet']:.2f} s" if event.get("pet") is not None else "N/A",
            status_badge(event["risk_level"]),
        ]
        for event in sorted(events, key=lambda item: item["time_seconds"], reverse=True)[:8]
    ]


def _analytics_charts(events: list[dict]) -> None:
    st.markdown("<div class='cg-title'>Risk &amp; Trajectory Analytics</div>", unsafe_allow_html=True)
    if events:
        ranked = sorted(events, key=lambda event: event["risk_score"], reverse=True)[:12]
        labels = [f"{event['interaction']} · {event['event_id']}" for event in ranked]
        colors = [
            {"High": "#fb7185", "Medium": "#fbbf24", "Low": "#34d399"}[event["risk_level"]]
            for event in ranked
        ]
        figure = go.Figure(
            go.Bar(
                x=[event["risk_score"] for event in ranked],
                y=labels,
                orientation="h",
                marker=dict(color=colors, line=dict(color="rgba(255,255,255,.18)", width=1)),
                text=[f"{event['risk_score']:.2f} · {event['risk_level']}" for event in ranked],
                textposition="outside",
                customdata=[[event["t_cpa"], event["d_cpa"]] for event in ranked],
                hovertemplate="%{y}<br>Risk %{x:.2f}<br>tCPA %{customdata[0]:.2f}s<br>dCPA %{customdata[1]:.1f}px<extra></extra>",
            )
        )
        figure.update_layout(
            title=dict(text="Highest calculated near-miss risk", font=dict(color="#f8fafc", size=17)),
            height=330,
            margin=dict(l=12, r=72, t=52, b=30),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(9,19,33,.62)",
            font=dict(color="#f1f5f9", size=13),
            xaxis=dict(
                range=[0, 1.12],
                title=dict(text="Risk score", font=dict(color="#dbeafe", size=13)),
                tickfont=dict(color="#dbeafe", size=12),
                gridcolor="rgba(148,163,184,.22)",
            ),
            yaxis=dict(autorange="reversed", title="", tickfont=dict(color="#dbeafe", size=12)),
            showlegend=False,
        )
        st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})
    else:
        st.info("No interactions currently satisfy the near-miss thresholds.")

    if events:
        cpa_col, components_col = st.columns(2, gap="large")
        with cpa_col:
            event_frame = pd.DataFrame(events)
            figure = px.scatter(
                event_frame,
                x="t_cpa",
                y="d_cpa",
                color="risk_level",
                size="risk_score",
                hover_name="interaction",
                hover_data={"event_id": True, "risk_score": ":.2f", "t_cpa": ":.2f", "d_cpa": ":.1f"},
                color_discrete_map={"High": "#fb7185", "Medium": "#fbbf24", "Low": "#34d399"},
                labels={"t_cpa": "Time to CPA (s)", "d_cpa": "Projected CPA distance (px)", "risk_level": "Risk"},
            )
            figure.add_vline(x=3, line_dash="dash", line_color="#a78bfa", annotation_text="3 s threshold")
            figure.add_hline(y=80, line_dash="dash", line_color="#38bdf8", annotation_text="80 px event limit")
            figure.update_layout(
                title=dict(text="Closest-point-of-approach map", font=dict(color="#f8fafc", size=17)),
                height=350,
                margin=dict(l=12, r=20, t=52, b=30),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(9,19,33,.62)",
                font=dict(color="#f1f5f9", size=13),
                xaxis=dict(gridcolor="rgba(148,163,184,.22)", tickfont=dict(color="#dbeafe", size=12)),
                yaxis=dict(gridcolor="rgba(148,163,184,.22)", tickfont=dict(color="#dbeafe", size=12)),
            )
            st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})

        with components_col:
            ordered = sorted(events, key=lambda event: event["risk_score"], reverse=True)[:12]
            figure = go.Figure()
            figure.add_bar(
                name="TTC risk component",
                x=[event["interaction"] for event in ordered],
                y=[.5 * event["risk_time_component"] for event in ordered],
                marker_color="#a78bfa",
            )
            figure.add_bar(
                name="dCPA risk component",
                x=[event["interaction"] for event in ordered],
                y=[.5 * event["risk_distance_component"] for event in ordered],
                marker_color="#fb7185",
            )
            figure.update_layout(
                barmode="stack",
                title=dict(text="Risk score composition · equal weights", font=dict(color="#f8fafc", size=17)),
                height=350,
                margin=dict(l=12, r=12, t=52, b=90),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(9,19,33,.62)",
                font=dict(color="#f1f5f9", size=13),
                xaxis=dict(tickangle=-35, title="", tickfont=dict(color="#dbeafe", size=12)),
                yaxis=dict(
                    range=[0, 1],
                    title=dict(text="Weighted component", font=dict(color="#dbeafe", size=12)),
                    tickfont=dict(color="#dbeafe", size=12),
                    gridcolor="rgba(148,163,184,.22)",
                ),
                legend=dict(orientation="h", y=1.12, x=0),
            )
            st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})


def _active_saved_video() -> dict | None:
    videos = list_videos()
    if not videos:
        return None

    active_id = get_active_video()
    video_ids = {video["video_id"] for video in videos}
    if active_id not in video_ids:
        active_id = videos[0]["video_id"]
        set_active_video(active_id)
    return get_video(active_id)


def render() -> None:
    page_header("Real-Time Near-Miss Detection", "Monitor pedestrians, vehicles and near-miss events in real time")
    selected_video = _active_saved_video()
    analysis = (
        selected_video.get("analysis")
        if selected_video and analysis_is_current(selected_video, MODEL_WEIGHTS)
        else None
    )
    events = analysis.get("events", []) if analysis else []

    if analysis:
        pedestrians = analysis["pedestrian_tracks"]
        vehicles = analysis["vehicle_tracks"]
        event_count = len(events)
        risk_level = max(
            (event["risk_level"] for event in events),
            key=lambda level: {"Low": 1, "Medium": 2, "High": 3}[level],
            default="No event",
        )
    else:
        pedestrians = vehicles = event_count = risk_level = "—"

    for column, (label, value) in zip(
        st.columns(4),
        (
            ("Pedestrians", pedestrians),
            ("Vehicles", vehicles),
            ("Near-Miss Events", event_count),
            ("Risk Level", risk_level),
        ),
    ):
        column.metric(label, value)

    left, right = st.columns([.83, 1.42], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("<div class='cg-title'>Recent Events (Near-Miss Log)</div>", unsafe_allow_html=True)
            if analysis:
                rows = _latest_event_rows(events)
            else:
                rows = []
            if rows:
                st.markdown(
                    html_table(["Time", "Interaction", "dCPA", "tCPA", "PET", "Risk"], rows),
                    unsafe_allow_html=True,
                )
            elif selected_video:
                st.info("Run YOLO + ByteTrack on the selected video to calculate its event log.")
            else:
                st.info("Upload and analyze a video to populate this log with detected interactions.")

    with right:
        with st.container(border=True):
            if selected_video:
                st.markdown("<div class='cg-title'>Input Video</div>", unsafe_allow_html=True)
                render_video_pair(selected_video)
            else:
                st.markdown("<div class='cg-title'>Input Video</div>", unsafe_allow_html=True)
                st.info("Select or upload a video to view the original clip and its bounding-box output.")

    if analysis:
        with st.container(border=True):
            _analytics_charts(events)
            st.caption(
                "Precision = TP/(TP+FP), Recall = TP/(TP+FN), F1 = 2·Precision·Recall/(Precision+Recall). "
                "These model-quality scores are not reported until detections are matched against labeled ground truth."
            )
    elif selected_video and (selected_video.get("analysis") or {}).get("model_name") == MODEL_WEIGHTS:
        st.warning("Reanalyze this video to refresh its CPA risk and estimated PET.")


if __name__ == "__main__":
    render()
