"""Video-grounded event evidence and proposed structural causal graph"""

from html import escape
import math

import plotly.graph_objects as go
import streamlit as st

from active_video import get_active_video
from app.components import event_selector, html_table
from app.video_processing import (
    CPA_MAX_DISTANCE_PX,
    TTC_MAX_SECONDS,
    qualifies_near_miss,
)
from app.video_views import render_video_pair
from navigation import page_header
from video_library import get_video


def _valid_path(path: object) -> list[list[float]]:
    if not isinstance(path, list):
        return []
    valid_points = []
    for point in path:
        if (
            isinstance(point, list)
            and len(point) >= 3
            and all(isinstance(value, (int, float)) and math.isfinite(value) for value in point[:3])
        ):
            valid_points.append(point)
    return valid_points


def _proposed_scm_figure(
    event: dict,
    video_name: str = "Selected video",
    video_id: str = "Unavailable",
) -> go.Figure:
    """Render an event-populated proposed SCM without implying causal validation."""
    unavailable = "Unavailable"
    distance_unit = str(event.get("distance_unit") or "px")
    speed_unit = str(event.get("speed_unit") or "px/s")

    def metric(field: str, precision: int, unit: str) -> str:
        value = event.get(field)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            return unavailable
        return f"{value:.{precision}f} {unit}".strip()

    def detail(label: str, value: str) -> str:
        if value == "Not annotated":
            return (
                f"{escape(label)}<br>"
                "<span style='color:#a8b6c9;font-weight:600'>"
                "Not annotated</span>"
            )
        return f"{escape(label)}<br><b>{escape(value)}</b>"

    context = [
        detail("Visibility", str(event.get("visibility") or "Not annotated")),
        detail("Road condition", str(event.get("road_condition") or "Not annotated")),
        detail("Crossing", str(event.get("crossing_geometry") or "Not annotated")),
    ]
    motion = [
        detail("Pedestrian", f"P{event.get('pedestrian_track_id', '?')} · {metric('pedestrian_speed', 1, speed_unit)}"),
        detail("Vehicle", f"V{event.get('vehicle_track_id', '?')} · {metric('vehicle_speed', 1, speed_unit)}"),
        detail("Relative motion", str(event.get("relative_motion") or unavailable)),
    ]
    geometry = [
        detail("Closest separation", metric("d_cpa", 1, distance_unit)),
        detail("Closing speed", metric("closing_rate", 1, speed_unit)),
        detail("Rule limit", f"{CPA_MAX_DISTANCE_PX:.0f} px"),
    ]
    indicators = [
        detail("tCPA", metric("t_cpa", 2, "s")),
        detail("TTC", metric("ttc", 2, "s")),
        detail("Estimated PET", metric("pet", 3, "s")),
    ]
    candidate_status = _candidate_rule_status(event)
    outcome = [
        detail("Risk category", str(event.get("risk_level") or unavailable)),
        detail("Risk score", metric("risk_score", 3, "")),
        detail("Candidate rule", candidate_status),
    ]

    node_colors = ["#f59e0b", "#14b8a6", "#38bdf8", "#a78bfa", "#fb7185"]
    nodes = [
        ("CONTEXT", context, node_colors[0]),
        ("TRACK MOTION", motion, node_colors[1]),
        ("CONFLICT GEOMETRY", geometry, node_colors[2]),
        ("CONFLICT INDICATORS", indicators, node_colors[3]),
        ("RULE-BASED OUTCOME", outcome, node_colors[4]),
    ]
    centers = [0.105, 0.3025, 0.5, 0.6975, 0.895]
    figure = go.Figure()

    for index, (title, details, color) in enumerate(nodes):
        center = centers[index]
        left, right = center - 0.084, center + 0.084
        figure.add_shape(
            type="rect",
            x0=left,
            x1=right,
            y0=0.17,
            y1=0.86,
            line=dict(color=color, width=1.8),
            fillcolor="rgba(13,23,38,.98)",
            layer="below",
        )
        figure.add_shape(
            type="rect",
            x0=left,
            x1=right,
            y0=0.83,
            y1=0.86,
            line=dict(width=0),
            fillcolor=color,
            layer="below",
        )
        figure.add_annotation(
            x=center,
            y=0.76,
            text=f"<b>{title}</b>",
            showarrow=False,
            xanchor="center",
            yanchor="middle",
            align="center",
            font=dict(size=14, color="#ffffff", family="Inter, Arial, sans-serif"),
        )
        figure.add_annotation(
            x=center,
            y=0.49,
            text="<br><br>".join(details),
            showarrow=False,
            xanchor="center",
            yanchor="middle",
            align="center",
            font=dict(size=13, color="#f1f5f9", family="Inter, Arial, sans-serif"),
        )
        figure.add_trace(
            go.Scatter(
                x=[center],
                y=[0.49],
                mode="markers",
                marker=dict(size=1, color="rgba(0,0,0,0)"),
                hovertemplate=(
                    f"<b>{title}</b><br>"
                    + "<br>".join(details)
                    + "<extra></extra>"
                ),
                showlegend=False,
            )
        )

    arrow_labels = [
        "Context link<br>assumed",
        "Observed tracks",
        "Derived geometry",
        "Scoring rule",
    ]
    for index, label in enumerate(arrow_labels):
        figure.add_annotation(
            x=centers[index + 1] - 0.086,
            y=0.55,
            ax=centers[index] + 0.086,
            ay=0.55,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            text="",
            showarrow=True,
            arrowhead=3,
            arrowsize=1.1,
            arrowwidth=2,
            arrowcolor="#fbbf24" if index == 0 else "#9bb0c9",
        )
        figure.add_annotation(
            x=(centers[index] + centers[index + 1]) / 2,
            y=0.08,
            text=label,
            showarrow=False,
            align="center",
            font=dict(size=12, color="#f1f5f9"),
        )

    safe_video_name = escape(str(video_name))
    figure.update_layout(
        title=dict(
            text=(
                f"<b>{safe_video_name}</b> · Video {escape(str(video_id)[:12])} · "
                f"Event {escape(str(event.get('event_id', 'Unavailable')))} · "
                f"{escape(str(event.get('interaction', 'Unavailable')))}"
            ),
            x=0.02,
            xanchor="left",
            y=0.98,
            yanchor="top",
            font=dict(size=16, color="#f8fafc", family="Inter, Arial, sans-serif"),
        ),
        height=500,
        margin=dict(l=18, r=18, t=82, b=28),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(9,19,33,.35)",
        font=dict(color="#f1f5f9", size=13),
        xaxis=dict(range=[0, 1], visible=False, fixedrange=True),
        yaxis=dict(range=[0.02, 0.92], visible=False, fixedrange=True),
        hoverlabel=dict(
            bgcolor="#111827",
            bordercolor="#475569",
            font=dict(color="#f8fafc", size=14, family="Inter, Arial, sans-serif"),
        ),
        hovermode="closest",
    )
    return figure


def _risk_component_figure(event: dict) -> go.Figure:
    time_component = event.get("risk_time_component")
    distance_component = event.get("risk_distance_component")
    time_contribution = 0.5 * time_component if time_component is not None else None
    distance_contribution = 0.5 * distance_component if distance_component is not None else None

    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            y=["Time-related contribution", "Separation-related contribution"],
            x=[time_contribution, distance_contribution],
            orientation="h",
            marker=dict(
                color=["#a78bfa", "#22d3ee"],
                line=dict(color="rgba(255,255,255,.45)", width=1),
            ),
            text=[
                f"Time score {time_component:.2f} · contribution {time_contribution:.2f}"
                if time_component is not None
                else "Unavailable",
                f"Separation score {distance_component:.2f} · contribution {distance_contribution:.2f}"
                if distance_component is not None
                else "Unavailable",
            ],
            textposition="outside",
            textfont=dict(color="#f8fafc", size=13, family="Inter, Arial, sans-serif"),
            cliponaxis=False,
            hovertemplate="%{y}<br>Weighted contribution: %{x:.3f}<extra></extra>",
        )
    )
    figure.update_layout(
        title=dict(text="Measured inputs to the rule-based risk score", font=dict(color="#f8fafc", size=17)),
        height=250,
        margin=dict(l=12, r=68, t=58, b=42),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(9,19,33,.55)",
        font=dict(color="#f1f5f9", size=13),
        xaxis=dict(
            range=[0, 0.62],
            title=dict(text="Contribution to R", font=dict(color="#e2e8f0", size=13)),
            tickfont=dict(color="#e2e8f0", size=13),
            gridcolor="rgba(148,163,184,.22)",
        ),
        yaxis=dict(autorange="reversed", tickfont=dict(color="#f8fafc", size=13)),
        showlegend=False,
        hoverlabel=dict(bgcolor="#111827", font=dict(color="#f8fafc", size=13)),
    )
    return figure


def _event_evidence_table(event: dict) -> str:
    speed_unit = escape(str(event.get("speed_unit") or "Unavailable"))

    def value(field: str, precision: int = 2, unit: str = "") -> str:
        metric = event.get(field)
        if metric is None:
            return "Unavailable"
        return escape(f"{metric:.{precision}f}{unit}")

    candidate = _candidate_rule_status(event)
    rows = [
        ["Video timestamp", escape(f"{event.get('time', 'Unavailable')} s")],
        ["Pedestrian track ID", escape(str(event.get("pedestrian_track_id", "Unavailable")))],
        ["Vehicle track ID", escape(str(event.get("vehicle_track_id", "Unavailable")))],
        ["Pedestrian estimated speed", value("pedestrian_speed", 1, f" {speed_unit}")],
        ["Vehicle estimated speed", value("vehicle_speed", 1, f" {speed_unit}")],
        ["Relative motion", escape(str(event.get("relative_motion") or "Unavailable"))],
        ["Relative closing speed", value("closing_rate", 1, f" {speed_unit}")],
        ["Closest separation (dCPA)", value("d_cpa", 1, f" {event.get('distance_unit', 'px')}")],
        ["Time to closest approach (tCPA)", value("t_cpa", 2, " s")],
        ["Time to collision (TTC)", value("ttc", 2, " s")],
        ["Post-encroachment time (PET)", value("pet", 3, " s")],
        ["Risk score", value("risk_score", 2)],
        ["Risk category", escape(str(event.get("risk_level") or "Unavailable"))],
        ["Meets near-miss candidate rule", candidate],
    ]
    return html_table(["Selected interaction evidence", "Video-derived value"], rows)


def _candidate_rule_status(event: dict) -> str:
    if any(event.get(field) is None for field in ("t_cpa", "d_cpa", "closing_rate")):
        return "Unavailable · required CPA metrics are missing"
    return "Yes" if qualifies_near_miss(event) else "No"


def render() -> None:
    page_header(
        "Causal Analysis",
        "Video-grounded interaction evidence and an explicitly proposed causal structure",
    )
    event_id, event = event_selector()
    video_id = get_active_video()
    selected_video = get_video(video_id) if video_id else None

    if selected_video:
        with st.expander("Selected video · original and bounding-box output"):
            render_video_pair(selected_video)
    if not event:
        st.info("Choose an analyzed video and interaction to inspect its evidence.")
        return

    st.markdown(
        f"""
        <div class="cg-causal-hero">
          <div>
            <div class="cg-kicker">Selected interaction · {escape(str(event_id))}</div>
            <div class="cg-causal-hero-title">{escape(str(event.get('interaction', 'Unavailable')))}</div>
            <div class="cg-causal-hero-sub">Video time {escape(str(event.get('time', 'Unavailable')))} s
              · Pedestrian track {escape(str(event.get('pedestrian_track_id', 'Unavailable')))}
              · Vehicle track {escape(str(event.get('vehicle_track_id', 'Unavailable')))}</div>
          </div>
          <div class="cg-causal-risk {escape(str(event.get('risk_level', 'low')).lower())}">
            <span>{escape(str(event.get('risk_level', 'Unavailable')))} risk</span>
            <strong>{escape(f"{event['risk_score']:.2f}" if event.get('risk_score') is not None else "Unavailable")}</strong>
            <small>Rule-based R</small>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='cg-section-heading'>Proposed causal structure</div>"
        "<p class='cg-section-copy'>This is a proposed, unvalidated SCM. Arrows show stated assumptions and "
        "calculation flow; they do not establish causal effects.</p>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.plotly_chart(
            _proposed_scm_figure(
                event,
                selected_video.get("original_name", "Selected video") if selected_video else "Selected video",
                video_id or "Unavailable",
            ),
            width="stretch",
            config={"displayModeBar": False},
        )
        st.markdown(
            """
            <div class="cg-causal-legend">
              <span><i style="background:#14b8a6"></i>Observed track motion</span>
              <span><i style="background:#38bdf8"></i>Derived geometry</span>
              <span><i style="background:#a78bfa"></i>Calculated indicators</span>
              <span><i style="background:#fb7185"></i>Rule-based outcome</span>
              <span><i style="background:#f59e0b"></i>Context unavailable · assumed link</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    evidence_col, components_col = st.columns([1.15, .85], gap="large")
    with evidence_col:
        with st.container(border=True):
            st.markdown(
                "<div class='cg-section-heading'>Selected interaction evidence</div>"
                "<p class='cg-section-copy'>All values below belong to this video and selected track pair.</p>",
                unsafe_allow_html=True,
            )
            st.markdown(_event_evidence_table(event), unsafe_allow_html=True)

    with components_col:
        with st.container(border=True):
            st.markdown(
                "<div class='cg-section-heading'>Risk-factor explanation</div>"
                "<p class='cg-section-copy'>These are the inputs to the implemented score, not causal feature importance.</p>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                _risk_component_figure(event),
                width="stretch",
                config={"displayModeBar": False},
            )
if __name__ == "__main__":
    render()
