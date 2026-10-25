"""Reusable video-event, media, and presentation helpers."""

from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

def event_label(event_id: str, event: dict) -> str:
    return f"{event_id} — {event['interaction']} ({event['time']}s)"


def event_selector() -> tuple[str | None, dict | None]:
    """Display events from the selected video's saved analysis."""
    from active_video import get_active_event, get_active_video, set_active_event
    from app.video_processing import ANALYSIS_VERSION, MODEL_WEIGHTS
    from video_library import analysis_is_current, get_video

    video_id = get_active_video()
    video = get_video(video_id) if video_id else None
    analysis = video.get("analysis") if video else None
    if (
        analysis
        and analysis.get("analysis_version") != ANALYSIS_VERSION
        and analysis.get("model_name") == MODEL_WEIGHTS
    ):
        st.warning("Reanalyze this video to update its CPA metrics and estimated PET.")
    analysis = (
        video.get("analysis")
        if video and analysis_is_current(video, MODEL_WEIGHTS)
        else None
    )
    events = (
        {event["event_id"]: event for event in analysis["events"]}
        if analysis
        else {}
    )
    if not events:
        if video and video.get("analysis"):
            st.warning("This video has outdated analysis. Rerun YOLO + ByteTrack to refresh its events.")
        elif video:
            st.info("This saved video has no analyzed pedestrian-vehicle interactions yet. Run video analysis first.")
        else:
            st.info("Upload and analyze a video to generate interaction events.")
        return None, None

    labels = {event_label(event_id, event): event_id for event_id, event in events.items()}
    current = get_active_event()
    options = list(labels)
    default_event = current if current in events else max(
        events,
        key=lambda event_id: (
            events[event_id].get("ttc") is not None,
            events[event_id].get("risk_score", 0),
        ),
    )
    default_index = next(i for i, label in enumerate(options) if labels[label] == default_event)
    widget_key = f"selected_event_{video_id or 'none'}"
    if widget_key in st.session_state and st.session_state[widget_key] not in labels:
        del st.session_state[widget_key]
    selected_label = st.selectbox("Select Event", options, index=default_index, key=widget_key)
    selected_id = labels[selected_label]
    set_active_event(selected_id)
    return selected_id, events[selected_id]


def status_badge(level: str) -> str:
    level_class = {
        "high": "high",
        "medium": "medium",
        "low": "low",
        "online": "online",
        "connected": "online",
        "sent": "online",
        "not sent": "high",
        "not configured": "medium",
        "no projected cpa": "medium",
    }.get(level.lower(), "low")
    return f"<span class='cg-status {level_class}'>{escape(level)}</span>"


def html_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<div class='cg-table-wrap'><table class='cg-table'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def metric_table(event: dict, include_location: bool = False) -> str:
    if not event.get("calibrated", True):
        distance_label = "dCPA (px)"
        pedestrian_speed_label = "Pedestrian speed (px/s)"
        vehicle_speed_label = "Vehicle speed (px/s)"
        distance = f"{event['distance']:.1f}"
        pedestrian_speed = f"{event['pedestrian_speed']:.1f}"
        vehicle_speed = f"{event['vehicle_speed']:.1f}"
        ttc = f"{event['ttc']:.2f} s" if event["ttc"] is not None else "N/A"
        pet = (
            f"{event['pet']:.3f} s"
            if event.get("pet") is not None
            else "N/A — vehicle did not enter estimated conflict zone"
        )
        coverage_warning = (
            "<br><b>Warning:</b> Limited observation window; "
            "interpret predicted risk with caution."
            if event.get("trajectory_coverage_warning", False)
            else ""
        )
    else:
        distance_label = "Distance (m)"
        pedestrian_speed_label = "Pedestrian Speed (m/s)"
        vehicle_speed_label = "Vehicle Speed (km/h)"
        distance = f"{event['distance']:.1f}"
        pedestrian_speed = f"{event['pedestrian_speed']:.1f}"
        vehicle_speed = f"{event['vehicle_speed']:.0f}"
        ttc = f"{event['ttc']:.1f}"
        pet = f"{event['pet']:.3f} s" if event.get("pet") is not None else "N/A (zone crossing unavailable)"
    rows = [
        ("Time", event["time"]),
        (distance_label, distance),
        ("Relative Motion", event["relative_motion"]),
        ("tCPA (s)", f"{event['t_cpa']:.2f}"),
        ("Image-plane TTC" if not event.get("calibrated", True) else "TTC", ttc),
        ("PET", pet + coverage_warning),
        (pedestrian_speed_label, pedestrian_speed),
        (vehicle_speed_label, vehicle_speed),
        (
            "Closing speed (px/s)" if not event.get("calibrated", True) else "Closing speed (m/s)",
            f"{event['closing_rate']:.1f}",
        ),
        ("Risk Score", f"{event['risk_score']:.2f}"),
        ("RT (time risk)", f"{event['risk_time_component']:.2f}"),
        ("RD (distance risk)", f"{event['risk_distance_component']:.2f}"),
        ("Risk Level", status_badge(event["risk_level"])),
    ]
    if include_location:
        rows.insert(1, ("Location", event["location"]))
    table = html_table(["Parameter", "Value"], [[escape(key), value] for key, value in rows])
    if not event.get("calibrated", True):
        table += (
            "<p class='cg-foot'>PET uses the signed time gap between the two track centers' "
            "occupancy of an estimated CPA-centered zone. It is an image-plane estimate; "
            "N/A means both tracks did not provide one unambiguous crossing.</p>"
        )
    return table


def traffic_scene_svg(timestamp: float = 12.4, show_red: bool = True, show_vehicle: bool = True) -> str:
    """Return a self-contained illustrative frame until a real video is connected."""
    red = "#ef4444" if show_red else "transparent"
    vehicle = "#10b981" if show_vehicle else "transparent"
    phase = max(0.0, min(timestamp / 24.0, 1.0))
    px = 280 + phase * 135
    return f"""
    <svg viewBox="0 0 1000 520" role="img" aria-label="Illustrative monitored crosswalk frame" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="sky" x2="0" y2="1"><stop stop-color="#18374c"/><stop offset="1" stop-color="#45624e"/></linearGradient>
        <linearGradient id="road" x2="0" y2="1"><stop stop-color="#283644"/><stop offset="1" stop-color="#151c25"/></linearGradient>
      </defs>
      <rect width="1000" height="520" fill="url(#sky)"/>
      <path d="M0 0h160v270H0M840 0h160v270H840" fill="#162b35"/>
      <g fill="#263b46"><path d="M22 35h30v65H22zm65-10h44v76H87zm766 7h45v80h-45zm65-13h34v92h-34z"/></g>
      <g fill="#48604c"><circle cx="205" cy="80" r="65"/><circle cx="310" cy="55" r="52"/><circle cx="735" cy="68" r="68"/><circle cx="825" cy="52" r="55"/></g>
      <path d="M0 258h1000v262H0z" fill="url(#road)"/>
      <path d="M0 305h1000M0 445h1000" stroke="#aab5b7" stroke-width="4" opacity=".3"/>
      <g fill="#d9e1df" opacity=".88">
        <path d="M90 360h86v26H90zm105 0h86v26h-86zm105 0h86v26h-86zm105 0h86v26h-86zm105 0h86v26h-86zm105 0h86v26h-86zm105 0h86v26h-86z"/>
        <path d="M90 405h86v20H90zm105 0h86v20h-86zm105 0h86v20h-86zm105 0h86v20h-86zm105 0h86v20h-86zm105 0h86v20h-86zm105 0h86v20h-86z"/>
      </g>
      <path d="M{px:.0f} 360 Q560 315 710 280" fill="none" stroke="{red}" stroke-width="7" stroke-dasharray="14 10"/>
      <path d="M700 295 Q780 252 865 270" fill="none" stroke="{vehicle}" stroke-width="7" stroke-dasharray="14 10"/>
      <g fill="{red}"><circle cx="{px:.0f}" cy="360" r="9"/><circle cx="475" cy="335" r="8"/><circle cx="585" cy="310" r="8"/></g>
      <g>
        <circle cx="{px:.0f}" cy="280" r="19" fill="#1f2937"/><path d="M{px:.0f} 300l-17 50h34z" fill="#2563eb"/><path d="M{px-7:.0f} 346l-14 32m27-32 14 32" stroke="#d4b99c" stroke-width="10" stroke-linecap="round"/>
        <rect x="{px-38:.0f}" y="251" width="76" height="142" rx="4" fill="none" stroke="{red}" stroke-width="5"/>
        <rect x="{px-38:.0f}" y="225" width="76" height="28" rx="4" fill="{red}"/><text x="{px:.0f}" y="245" text-anchor="middle" fill="white" font-size="18" font-weight="700">P01</text>
      </g>
      <g transform="translate(735 235)">
        <rect x="0" y="25" width="165" height="74" rx="22" fill="#18232b" stroke="{vehicle}" stroke-width="5"/>
        <path d="M25 25l20-34h67l28 34" fill="#294354" stroke="{vehicle}" stroke-width="4"/>
        <circle cx="38" cy="101" r="15" fill="#080d12" stroke="#91a4b8" stroke-width="5"/><circle cx="130" cy="101" r="15" fill="#080d12" stroke="#91a4b8" stroke-width="5"/>
        <rect x="0" y="-5" width="165" height="134" fill="none" stroke="{vehicle}" stroke-width="5"/>
        <rect x="0" y="-31" width="68" height="28" rx="4" fill="{vehicle}"/><text x="34" y="-11" text-anchor="middle" fill="white" font-size="18" font-weight="700">V02</text>
      </g>
      <rect x="18" y="18" width="186" height="34" rx="8" fill="#07111c" opacity=".78"/>
      <circle cx="37" cy="35" r="6" fill="#34d399"/><text x="52" y="41" fill="#e5edf5" font-size="16" font-family="sans-serif">LIVE · CROSSWALK 1</text>
    </svg>
    """


def scene(timestamp: float = 12.4, show_red: bool = True, show_vehicle: bool = True) -> None:
    st.markdown(
        f"<div style='border:1px solid rgba(148,163,184,.2);border-radius:11px;overflow:hidden;background:#101923'>{traffic_scene_svg(timestamp, show_red, show_vehicle)}</div>",
        unsafe_allow_html=True,
    )


def show_actual_video(video: dict) -> None:
    """Display the uploaded video and only show a current playable detection output."""
    from app.video_processing import MODEL_WEIGHTS
    from video_library import analysis_is_current, processed_path, source_path

    original_path = source_path(video)
    annotated_path = processed_path(video)
    current_analysis = analysis_is_current(video, MODEL_WEIGHTS)
    original_col, tracked_col = st.columns(2, gap="medium")
    with original_col:
        st.markdown("<div class='cg-title'>Original video</div>", unsafe_allow_html=True)
        if original_path.is_file():
            st.video(str(original_path))
        else:
            st.error("The uploaded video is missing from server storage.")
    with tracked_col:
        st.markdown(
            f"<div class='cg-title'>{MODEL_WEIGHTS} + ByteTrack bounding boxes</div>",
            unsafe_allow_html=True,
        )
        if current_analysis and annotated_path:
            st.video(str(annotated_path))
        elif video.get("analysis"):
            st.warning("The saved output is outdated or not browser-compatible. Rerun YOLO + ByteTrack.")
        else:
            st.info("Run YOLO + ByteTrack to generate and save the bounding-box video.")


def trajectory_figure(speed: float = 30.0, brake_delay: float = 0.0, crossing_shift: float = 0.0) -> go.Figure:
    """Create the two-dimensional pedestrian/vehicle paths for a scenario."""
    fig = go.Figure()
    pedestrian_y = [0, 5, 10, 15, 20, 25]
    pedestrian_x = [11 + crossing_shift] * len(pedestrian_y)
    vehicle_x = [0, 8, 16, 24, 32, 40, 48]
    vehicle_y = [3 + brake_delay * .4, 5 + brake_delay * .3, 7 + brake_delay * .1, 9, 10, 10.4, 10.6]
    scenario_x = [x * max(.45, min(speed / 30, 1.5)) for x in vehicle_x]
    fig.add_trace(go.Scatter(x=pedestrian_x, y=pedestrian_y, mode="lines+markers", name="Pedestrian", line=dict(color="#ef4444", dash="dash", width=3)))
    fig.add_trace(go.Scatter(x=vehicle_x, y=vehicle_y, mode="lines+markers", name="Vehicle · baseline", line=dict(color="#38bdf8", dash="dash", width=3)))
    fig.add_trace(go.Scatter(x=scenario_x, y=vehicle_y, mode="lines+markers", name="Vehicle · scenario", line=dict(color="#10b981", dash="dash", width=3)))
    fig.add_trace(go.Scatter(x=[11 + crossing_shift], y=[8], mode="markers", name="Conflict point", marker=dict(color="#f59e0b", size=12, symbol="diamond")))
    fig.update_layout(
        height=300, margin=dict(l=12, r=12, t=12, b=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(9,19,33,.62)",
        font=dict(color="#cbd5e1", size=12), legend=dict(orientation="h", y=1.15, x=0),
        xaxis=dict(title="X position (m)", gridcolor="rgba(148,163,184,.12)", zerolinecolor="rgba(148,163,184,.25)"),
        yaxis=dict(title="Y position (m)", gridcolor="rgba(148,163,184,.12)", zerolinecolor="rgba(148,163,184,.25)"),
    )
    return fig
