"""Compare an observed track baseline with explicit image-plane interventions."""

from html import escape
import math

import plotly.graph_objects as go
import streamlit as st

from active_video import get_active_video
from app.components import event_selector, html_table
from app.video_processing import (
    CPA_MAX_DISTANCE_PX,
    TTC_MAX_SECONDS,
    calculate_cpa_metrics,
    calculate_pet,
    qualifies_near_miss,
    risk_level,
)
from app.video_views import render_video_pair
from navigation import page_header
from video_library import get_video

SCENARIOS = {
    "Reduce vehicle speed": "Scale vehicle movement along its observed path.",
    "Earlier braking": "Apply a straight-line deceleration assumption after a selected delay.",
    "Alternative pedestrian timing": "Shift the observed pedestrian path relative to the vehicle.",
}


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
            valid_points.append([float(value) for value in point[:3]])
    return sorted(valid_points, key=lambda point: point[0])


def _position_at(path: list[list[float]], time: float) -> tuple[float, float] | None:
    if not path or time < path[0][0] or time > path[-1][0]:
        return None
    for index in range(1, len(path)):
        before, after = path[index - 1], path[index]
        if before[0] <= time <= after[0]:
            duration = after[0] - before[0]
            if duration <= 0:
                return after[1], after[2]
            fraction = (time - before[0]) / duration
            return (
                before[1] + (after[1] - before[1]) * fraction,
                before[2] + (after[2] - before[2]) * fraction,
            )
    return path[-1][1], path[-1][2]


def _velocity_at(path: list[list[float]], time: float) -> tuple[float, float] | None:
    for before, after in zip(path, path[1:]):
        if before[0] <= time <= after[0] and after[0] > before[0]:
            duration = after[0] - before[0]
            return (
                (after[1] - before[1]) / duration,
                (after[2] - before[2]) / duration,
            )
    return None


def _synchronized_paths(event: dict, start_time: float) -> tuple[list[list[float]], list[list[float]]]:
    pedestrian_path = _valid_path(event.get("pedestrian_path"))
    vehicle_path = _valid_path(event.get("vehicle_path"))
    vehicle_by_time = {point[0]: point for point in vehicle_path}
    synchronized = [
        (point, vehicle_by_time[point[0]])
        for point in pedestrian_path
        if point[0] in vehicle_by_time and point[0] >= start_time
    ]
    return (
        [pedestrian for pedestrian, _ in synchronized],
        [vehicle for _, vehicle in synchronized],
    )


def _pet(event: dict, pedestrian_path: list[list[float]], vehicle_path: list[list[float]]) -> float | None:
    conflict_zone = event.get("conflict_zone")
    if not isinstance(conflict_zone, dict):
        return None
    center = conflict_zone.get("center")
    radius = conflict_zone.get("radius")
    if (
        not isinstance(center, (list, tuple))
        or len(center) != 2
        or not isinstance(radius, (int, float))
    ):
        return None
    return calculate_pet(pedestrian_path, vehicle_path, tuple(center), float(radius))


def _path_speed(path: list[list[float]], time: float) -> float | None:
    velocity = _velocity_at(path, time)
    return math.hypot(*velocity) if velocity is not None else None


def _simulate(
    event: dict,
    scenario: str,
    value: float | tuple[float, float],
    selected_time: float | None = None,
) -> dict:
    """Recalculate baseline and intervention metrics on the same synchronized samples."""
    pedestrian_path = _valid_path(event.get("pedestrian_path"))
    vehicle_path = _valid_path(event.get("vehicle_path"))
    if len(pedestrian_path) < 2 or len(vehicle_path) < 2:
        raise ValueError("This event does not contain enough trajectory points to simulate.")

    if selected_time is None:
        selected_time = float(event.get("time_seconds", pedestrian_path[0][0]))
    baseline_pedestrian, baseline_vehicle = _synchronized_paths(event, selected_time)
    if len(baseline_pedestrian) < 2:
        raise ValueError("The selected observation has fewer than two synchronized future track samples.")

    selected_time = baseline_pedestrian[0][0]
    baseline_cpa = calculate_cpa_metrics(baseline_pedestrian, baseline_vehicle)
    baseline_pet = _pet(event, baseline_pedestrian, baseline_vehicle)
    baseline_speed = _path_speed(baseline_vehicle, selected_time)

    scenario_pedestrian: list[list[float]] = []
    scenario_vehicle: list[list[float]] = []
    vehicle_start = (baseline_vehicle[0][1], baseline_vehicle[0][2])

    brake_delay, deceleration = value if isinstance(value, tuple) else (0.0, 0.0)
    brake_time = selected_time + brake_delay
    brake_position = _position_at(baseline_vehicle, brake_time)
    brake_velocity = _velocity_at(baseline_vehicle, brake_time)
    brake_speed = math.hypot(*brake_velocity) if brake_velocity is not None else None
    brake_direction = (
        (brake_velocity[0] / brake_speed, brake_velocity[1] / brake_speed)
        if brake_velocity is not None and brake_speed and brake_speed > 0
        else None
    )

    for pedestrian_point, vehicle_point in zip(baseline_pedestrian, baseline_vehicle):
        time = vehicle_point[0]
        pedestrian_position = (pedestrian_point[1], pedestrian_point[2])
        simulated_vehicle = (vehicle_point[1], vehicle_point[2])

        if scenario == "Reduce vehicle speed":
            reduction = float(value)
            factor = 1.0 - reduction / 100.0
            simulated_vehicle = (
                vehicle_start[0] + (vehicle_point[1] - vehicle_start[0]) * factor,
                vehicle_start[1] + (vehicle_point[2] - vehicle_start[1]) * factor,
            )
        elif (
            scenario == "Earlier braking"
            and float(deceleration) > 0
            and brake_position is not None
            and brake_direction is not None
            and brake_speed is not None
            and time >= brake_time
        ):
            elapsed = time - brake_time
            traveled = max(0.0, brake_speed * elapsed - 0.5 * float(deceleration) * elapsed**2)
            simulated_vehicle = (
                brake_position[0] + brake_direction[0] * traveled,
                brake_position[1] + brake_direction[1] * traveled,
            )
        elif scenario == "Alternative pedestrian timing":
            shift = float(value)
            shifted_position = _position_at(pedestrian_path, time - shift)
            if shifted_position is None:
                continue
            pedestrian_position = shifted_position

        scenario_pedestrian.append([time, *pedestrian_position])
        scenario_vehicle.append([time, *simulated_vehicle])

    if len(scenario_pedestrian) < 2:
        raise ValueError("The chosen pedestrian time shift leaves fewer than two overlapping track samples.")

    scenario_cpa = calculate_cpa_metrics(scenario_pedestrian, scenario_vehicle)
    scenario_pet = _pet(event, scenario_pedestrian, scenario_vehicle)
    return {
        "selected_time": selected_time,
        "simulation_horizon": baseline_pedestrian[-1][0] - selected_time,
        "time_step": (
            baseline_pedestrian[1][0] - baseline_pedestrian[0][0]
            if len(baseline_pedestrian) > 1
            else None
        ),
        "baseline": {
            "cpa": baseline_cpa,
            "pet": baseline_pet,
            "vehicle_speed": baseline_speed,
        },
        "scenario": {
            "cpa": scenario_cpa,
            "pet": scenario_pet,
            "vehicle_speed": _path_speed(scenario_vehicle, selected_time),
        },
        "pedestrian": baseline_pedestrian,
        "vehicle": baseline_vehicle,
        "scenario_pedestrian": scenario_pedestrian,
        "scenario_vehicle": scenario_vehicle,
    }


def _metric_value(value: float | None, unit: str = "", precision: int = 2) -> str:
    return f"{value:.{precision}f}{unit}" if value is not None else "Unavailable"


def _comparison_rows(result: dict, distance_unit: str) -> list[list[str]]:
    baseline = result["baseline"]
    scenario = result["scenario"]
    baseline_cpa = baseline["cpa"]
    scenario_cpa = scenario["cpa"]

    def metric_row(label: str, before: float | None, after: float | None, unit: str = "", precision: int = 2) -> list[str]:
        delta = after - before if before is not None and after is not None else None
        return [
            label,
            _metric_value(before, unit, precision),
            _metric_value(after, unit, precision),
            f"{delta:+.{precision}f}{unit}" if delta is not None else "Unavailable",
        ]

    rows = [
        metric_row(
            "Vehicle speed estimate",
            baseline["vehicle_speed"],
            scenario["vehicle_speed"],
            " px/s",
            1,
        ),
        metric_row(
            "Minimum predicted separation (dCPA)",
            baseline_cpa["d_cpa"] if baseline_cpa else None,
            scenario_cpa["d_cpa"] if scenario_cpa else None,
            f" {distance_unit}",
            1,
        ),
        metric_row(
            "Time to closest approach (tCPA)",
            baseline_cpa["t_cpa"] if baseline_cpa else None,
            scenario_cpa["t_cpa"] if scenario_cpa else None,
            " s",
        ),
        metric_row(
            "TTC (image-plane estimate)",
            baseline_cpa["ttc"] if baseline_cpa else None,
            scenario_cpa["ttc"] if scenario_cpa else None,
            " s",
        ),
        metric_row("PET (estimated)", baseline["pet"], scenario["pet"], " s", 3),
        metric_row(
            "Risk score",
            baseline_cpa["risk_score"] if baseline_cpa else None,
            scenario_cpa["risk_score"] if scenario_cpa else None,
            "",
            3,
        ),
        [
            "Risk category",
            risk_level(baseline_cpa["risk_score"]) if baseline_cpa else "Unavailable",
            risk_level(scenario_cpa["risk_score"]) if scenario_cpa else "Unavailable",
            "Category change",
        ],
        [
            "Candidate rule",
            "Meets" if baseline_cpa and qualifies_near_miss(baseline_cpa) else "Does not meet" if baseline_cpa else "Unavailable",
            "Meets" if scenario_cpa and qualifies_near_miss(scenario_cpa) else "Does not meet" if scenario_cpa else "Unavailable",
            "Rule-based classification",
        ],
    ]
    return rows


def _plot_paths(result: dict) -> go.Figure:
    figure = go.Figure()
    traces = (
        ("pedestrian", "Pedestrian · baseline", "#fb7185", "dash"),
        ("scenario_pedestrian", "Pedestrian · scenario", "#fbbf24", "solid"),
        ("vehicle", "Vehicle · baseline", "#38bdf8", "dash"),
        ("scenario_vehicle", "Vehicle · scenario", "#34d399", "solid"),
    )
    for key, name, color, dash in traces:
        points = result[key]
        figure.add_trace(
            go.Scatter(
                x=[point[1] for point in points],
                y=[point[2] for point in points],
                mode="lines+markers",
                name=name,
                line=dict(color=color, dash=dash, width=3),
                marker=dict(size=5),
                customdata=[point[0] for point in points],
                hovertemplate=f"{name}<br>Time: %{{customdata:.3f}} s<br>X: %{{x:.1f}} px<br>Y: %{{y:.1f}} px<extra></extra>",
            )
        )

    for key, label, color, symbol in (
        ("baseline", "Baseline CPA", "#e879f9", "diamond"),
        ("scenario", "Scenario CPA", "#facc15", "x"),
    ):
        cpa = result[key]["cpa"]
        if not cpa:
            continue
        pedestrian_cpa = cpa["pedestrian_cpa"]
        vehicle_cpa = cpa["vehicle_cpa"]
        figure.add_trace(
            go.Scatter(
                x=[pedestrian_cpa[0], vehicle_cpa[0]],
                y=[pedestrian_cpa[1], vehicle_cpa[1]],
                mode="lines+markers",
                name=f"{label} · {cpa['d_cpa']:.1f} px",
                line=dict(color=color, dash="dot", width=2),
                marker=dict(color=color, size=12, symbol=symbol),
                hovertemplate=(
                    f"{label}<br>CPA observation: {cpa['frame_time']:.3f} s"
                    f"<br>tCPA: {cpa['t_cpa']:.2f} s<br>dCPA: {cpa['d_cpa']:.1f} px<extra></extra>"
                ),
            )
        )
    figure.update_layout(
        height=430,
        margin=dict(l=24, r=20, t=88, b=42),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(9,19,33,.62)",
        font=dict(color="#f1f5f9", size=14, family="Inter, Arial, sans-serif"),
        legend=dict(
            orientation="h",
            y=1.18,
            x=0,
            font=dict(color="#f1f5f9", size=13, family="Inter, Arial, sans-serif"),
            bgcolor="rgba(11,15,25,.72)",
        ),
        xaxis=dict(
            title=dict(text="Image-plane X (px)", font=dict(color="#e2e8f0", size=14)),
            tickfont=dict(color="#dbeafe", size=13),
            gridcolor="rgba(148,163,184,.2)",
            zerolinecolor="rgba(148,163,184,.25)",
        ),
        yaxis=dict(
            title=dict(text="Image-plane Y (px)", font=dict(color="#e2e8f0", size=14)),
            tickfont=dict(color="#dbeafe", size=13),
            gridcolor="rgba(148,163,184,.2)",
            zerolinecolor="rgba(148,163,184,.25)",
            autorange="reversed",
            scaleanchor="x",
        ),
        hoverlabel=dict(bgcolor="#111827", font=dict(color="#f8fafc", size=13)),
    )
    return figure


def _scenario_interpretation(result: dict, event: dict, scenario: str, value: float | tuple[float, float]) -> str:
    baseline_cpa = result["baseline"]["cpa"]
    scenario_cpa = result["scenario"]["cpa"]
    if baseline_cpa is None or scenario_cpa is None:
        return (
            "A comparable forward-closing CPA could not be calculated for both the observed baseline "
            "and the intervention. Risk-score change and an avoidance claim are therefore unavailable."
        )

    delta_risk = scenario_cpa["risk_score"] - baseline_cpa["risk_score"]
    baseline_score = baseline_cpa["risk_score"]
    scenario_score = scenario_cpa["risk_score"]
    if scenario == "Reduce vehicle speed":
        intervention = f"vehicle speed reduced by {float(value):.0f}%"
    elif scenario == "Earlier braking":
        intervention = (
            f"braking assumed after {value[0]:.1f}s with "
            f"{value[1]:.1f} px/s² deceleration"
        )
    else:
        intervention = f"pedestrian timing shifted by {float(value):+.1f}s"

    baseline_candidate = qualifies_near_miss(baseline_cpa)
    scenario_candidate = qualifies_near_miss(scenario_cpa)
    if baseline_candidate and not scenario_candidate:
        candidate_change = "The scenario no longer meets the implemented near-miss candidate rule."
    elif not baseline_candidate and scenario_candidate:
        candidate_change = "The scenario meets the implemented near-miss candidate rule, unlike the baseline."
    elif scenario_candidate:
        candidate_change = "The baseline and scenario both meet the implemented near-miss candidate rule."
    else:
        candidate_change = "The baseline and scenario both fall outside the implemented near-miss candidate rule."

    if delta_risk < 0:
        direction = "decreased"
    elif delta_risk > 0:
        direction = "increased"
    else:
        direction = "was unchanged"
    return (
        f"For {event.get('interaction', 'the selected interaction')}, {intervention}: "
        f"the rule-based risk score {direction} from {baseline_score:.3f} to {scenario_score:.3f} "
        f"(ΔR = Rscenario − Rbaseline = {scenario_score:.3f} − {baseline_score:.3f} = "
        f"{delta_risk:+.3f}). {candidate_change} This is a result from the specified image-plane "
        "rule and does not show that a real-world collision would or would not be avoided."
    )


def render() -> None:
    page_header(
        "Counterfactual Analysis",
        "Compare the observed interaction with a clearly specified what-if scenario",
    )
    event_id, event = event_selector()
    if not event:
        st.info("Select an analyzed video and pedestrian–vehicle interaction to compare scenarios.")
        return

    video_id = get_active_video()
    selected_video = get_video(video_id) if video_id else None
    if selected_video:
        with st.expander("Selected video · original and bounding-box output"):
            render_video_pair(selected_video)

    pedestrian_path = _valid_path(event.get("pedestrian_path"))
    vehicle_path = _valid_path(event.get("vehicle_path"))
    shared_times = sorted(
        {point[0] for point in pedestrian_path}
        & {point[0] for point in vehicle_path}
    )
    if len(shared_times) < 2:
        st.warning("This interaction has fewer than two synchronized track observations; a comparison cannot be calculated.")
        return

    target_time = float(event.get("time_seconds", shared_times[0]))
    default_time_index = min(range(len(shared_times)), key=lambda i: abs(shared_times[i] - target_time))
    event_key = "".join(character if character.isalnum() else "_" for character in str(event_id))
    timestamp_key = f"cf_{event_key}_baseline_time"
    selected_time = st.selectbox(
        "Select baseline observation time",
        shared_times,
        index=default_time_index,
        format_func=lambda timestamp: f"{timestamp:.3f} s",
        key=timestamp_key,
        help="The baseline is recalculated from this observation forward. It stays fixed while you adjust the intervention.",
    )
    scenario_key = f"cf_{event_key}_scenario"
    speed_key = f"cf_{event_key}_speed_reduction"
    delay_key = f"cf_{event_key}_brake_delay"
    deceleration_key = f"cf_{event_key}_deceleration"
    shift_key = f"cf_{event_key}_pedestrian_shift"

    if st.button("Reset intervention to baseline", key=f"cf_{event_key}_reset"):
        st.session_state[scenario_key] = list(SCENARIOS)[0]
        st.session_state[speed_key] = 0
        st.session_state[delay_key] = 0.0
        st.session_state[deceleration_key] = 0.0
        st.session_state[shift_key] = 0.0
        st.rerun()

    scenario = st.radio(
        "Select intervention scenario",
        list(SCENARIOS),
        horizontal=True,
        key=scenario_key,
    )
    with st.container(border=True):
        st.caption(f"{event_id} · {event['interaction']} · {SCENARIOS[scenario]}")
        if scenario == "Reduce vehicle speed":
            value: float | tuple[float, float] = st.slider(
                "Vehicle speed reduction from selected observation (%)",
                0,
                80,
                0,
                5,
                key=speed_key,
            )
        elif scenario == "Earlier braking":
            speed_estimate = _path_speed(_synchronized_paths(event, selected_time)[1], selected_time)
            max_deceleration = max(1.0, (speed_estimate or 1.0) * 2.0)
            delay_col, deceleration_col = st.columns(2)
            brake_delay = delay_col.slider(
                "Braking delay after baseline observation (s)",
                0.0,
                2.0,
                0.0,
                0.1,
                key=delay_key,
            )
            deceleration = deceleration_col.slider(
                "Assumed deceleration (px/s²)",
                0.0,
                float(max_deceleration),
                0.0,
                float(max(0.1, max_deceleration / 20.0)),
                key=deceleration_key,
            )
            value = (brake_delay, deceleration)
        else:
            value = st.slider(
                "Pedestrian crossing-time shift (s)",
                -2.0,
                2.0,
                0.0,
                0.1,
                key=shift_key,
                help="Positive values delay the pedestrian trajectory relative to the vehicle.",
            )

    try:
        result = _simulate(event, scenario, value, selected_time)
    except ValueError as exc:
        st.warning(str(exc))
        return

    baseline = result["baseline"]
    counterfactual = result["scenario"]
    baseline_cpa = baseline["cpa"]
    scenario_cpa = counterfactual["cpa"]
    delta_risk = (
        scenario_cpa["risk_score"] - baseline_cpa["risk_score"]
        if baseline_cpa is not None and scenario_cpa is not None
        else None
    )

    summary_cols = st.columns(4)
    summary_cols[0].metric("Baseline vehicle speed", _metric_value(baseline["vehicle_speed"], " px/s", 1))
    summary_cols[1].metric(
        "Baseline minimum separation",
        _metric_value(baseline_cpa["d_cpa"] if baseline_cpa else None, " px", 1),
    )
    summary_cols[2].metric(
        "Baseline risk score",
        _metric_value(baseline_cpa["risk_score"] if baseline_cpa else None, precision=3),
    )
    summary_cols[3].metric(
        "ΔR · scenario − baseline",
        _metric_value(delta_risk, precision=3),
        help="A negative value means this simulated rule-based score decreased; it is not a collision probability.",
    )

    graph_col, result_col = st.columns([1.4, 1], gap="large")
    with graph_col:
        with st.container(border=True):
            st.markdown("<div class='cg-title'>Baseline and counterfactual trajectories</div>", unsafe_allow_html=True)
            st.caption(
                f"Image-plane top view · horizon {result['simulation_horizon']:.2f} s · "
                f"sample step {result['time_step']:.3f} s · selected baseline starts at {result['selected_time']:.3f} s"
                if result["time_step"] is not None
                else "Image-plane top view · sampling interval unavailable"
            )
            if (
                baseline_cpa is not None
                and baseline_cpa["t_cpa"] > result["simulation_horizon"]
            ):
                st.warning(
                    f"Baseline tCPA ({baseline_cpa['t_cpa']:.2f} s) extends beyond the "
                    f"{result['simulation_horizon']:.2f} s observed horizon; it is an extrapolated estimate."
                )
            st.plotly_chart(_plot_paths(result), width="stretch", config={"displayModeBar": False})
    with result_col:
        with st.container(border=True):
            st.markdown("<div class='cg-title'>Numerical comparison</div>", unsafe_allow_html=True)
            st.markdown(
                html_table(
                    ["Metric", "Baseline", "Counterfactual", "Change"],
                    _comparison_rows(result, event.get("distance_unit", "px")),
                ),
                unsafe_allow_html=True,
            )
            st.markdown(
                "<div class='cg-callout'><b>Risk-score change:</b> "
                + escape(_scenario_interpretation(result, event, scenario, value))
                + "</div>",
                unsafe_allow_html=True,
            )

    assumptions = [
        f"Intervention: {scenario}.",
        f"Baseline observation: {result['selected_time']:.3f} s; the baseline uses the original synchronized tracks from this time forward.",
        "Vehicle speed reduction scales displacement along the observed image-plane path from the selected observation.",
        "Earlier braking assumes straight-line motion with constant deceleration after the selected delay; it does not model steering, braking response, road friction, grade, or vehicle dynamics.",
        "Alternative pedestrian timing shifts the observed pedestrian trajectory relative to the vehicle; shifted points outside the recorded pedestrian track are excluded, not extrapolated.",
        "CPA, TTC, PET, and risk are recalculated with the existing rules for the baseline and scenario. PET is available only when the same estimated conflict zone can be evaluated.",
        "Coordinates are image-plane pixels and speed/deceleration units are pixels per second and pixels per second squared. Without camera/ground-plane calibration, physical plausibility cannot be assessed.",
        "A lower ΔR is a lower output from the current rule-based score, not a collision-probability estimate or proof that an event would be avoided.",
    ]
    with st.expander("Scenario assumptions and plausibility"):
        st.markdown("\n".join(f"- {item}" for item in assumptions))
        st.info("Physical plausibility: not assessable from the uncalibrated video tracks and available vehicle/road data.")


if __name__ == "__main__":
    render()
