"""Selected-video high-risk alert summary."""

from html import escape

import streamlit as st

from active_video import get_active_video
from alerting import HIGH_RISK_THRESHOLD, evaluate_video_alert
from app.video_processing import MODEL_WEIGHTS, risk_level
from navigation import page_header
from video_library import analysis_is_current, get_video


def _recommendations(alert: dict, event: dict | None) -> list[str]:
    if alert["status"] == "Analysis Required":
        return [
            "Run YOLO + ByteTrack analysis on the selected video to calculate interaction risk.",
            "Return here after analysis; alerts are based on saved pedestrian–vehicle event results, not uploads or detections alone.",
        ]
    if alert["status"] == "Insufficient Data":
        return [
            "Re-run analysis for the selected video to regenerate valid event risk results.",
            "Check that pedestrian and vehicle tracks overlap in time so separation and timing metrics can be calculated.",
        ]
    if alert["status"] == "ALERT TRIGGERED" and event is not None:
        interaction = (
            f"pedestrian {event['pedestrian_track_id']} and vehicle {event['vehicle_track_id']}"
        )
        return [
            f"Review {interaction} at {event['time_seconds']:.2f} s in the tracked video.",
            "Check the available tCPA, dCPA, TTC and PET measurements; unavailable metrics should remain unassumed.",
            "Test reduced vehicle speed or earlier braking in Counterfactual Analysis; simulated results are estimates, not guaranteed collision prevention.",
        ]
    if event is not None:
        interaction = (
            f"pedestrian {event['pedestrian_track_id']} and vehicle {event['vehicle_track_id']}"
        )
        return [
            f"Review the highest-scoring interaction ({interaction}) at {event['time_seconds']:.2f} s if further context is needed.",
            "Inspect the available timing and separation metrics; this selected video's highest valid score is below the 0.60 high-risk threshold.",
        ]
    return []


def render() -> None:
    video_id = get_active_video()
    video = get_video(video_id) if video_id else None
    video_name = video.get("original_name", "No video selected") if video else "No video selected"
    page_header(
        "Alert Status",
        f"High-risk results for the selected video · {escape(video_name)}",
    )

    if video is None or not video.get("analysis"):
        alert = {"status": "Analysis Required", "event": None}
    elif not analysis_is_current(video, MODEL_WEIGHTS):
        alert = {"status": "Analysis Required", "event": None}
    else:
        alert = evaluate_video_alert(video.get("analysis"))

    status = alert["status"]
    event = alert["event"]

    status_class = {
        "ALERT TRIGGERED": "triggered",
        "No High-Risk Alert": "safe",
        "Analysis Required": "required",
        "Insufficient Data": "insufficient",
    }[status]
    st.markdown(
        f"<div class='cg-alert-status {status_class}'>{escape(status)}</div>",
        unsafe_allow_html=True,
    )

    if event is not None:
        score = float(event["risk_score"])
        severity = risk_level(score)
        summary, interaction = st.columns(2, gap="large")
        with summary:
            with st.container(border=True):
                st.markdown("<div class='cg-title'>Actual risk result</div>", unsafe_allow_html=True)
                st.metric("Risk score", f"{score:.3f}")
                st.markdown(
                    f"<span class='cg-status {severity.lower()}'>{escape(severity)} Risk</span>"
                    f"<p class='cg-foot'>High-risk trigger threshold: "
                    f"score ≥ {HIGH_RISK_THRESHOLD:.2f}</p>",
                    unsafe_allow_html=True,
                )
        with interaction:
            with st.container(border=True):
                st.markdown("<div class='cg-title'>Highest-risk interaction</div>", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='cg-alert-copy'>Event {escape(str(event['event_id']))}"
                    f" · {event['time_seconds']:.2f} s</div>"
                    f"<div class='cg-alert-title'>Pedestrian "
                    f"{escape(str(event['pedestrian_track_id']))} · Vehicle "
                    f"{escape(str(event['vehicle_track_id']))}</div>",
                    unsafe_allow_html=True,
                )

    with st.container(border=True):
        st.markdown("<div class='cg-title'>Recommended next steps</div>", unsafe_allow_html=True)
        recommendations = _recommendations(alert, event)
        for recommendation in recommendations:
            st.markdown(f"- {recommendation}")


if __name__ == "__main__":
    render()
