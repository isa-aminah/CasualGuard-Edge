import os
import tempfile
import unittest
from unittest.mock import patch

from alerting import (
    alert_severity,
    build_alert_records,
    consecutive_candidate_observations,
    evaluate_video_alert,
)
from video_library import (
    DEFAULT_ALERT_SETTINGS,
    VideoLibraryError,
    get_alert_reviews,
    get_alert_settings,
    save_alert_settings,
    save_video,
    set_alert_status,
)


def make_event(event_id="EV-1", time_seconds=1.0, interaction="P01 - V02", score=0.65):
    return {
        "event_id": event_id,
        "interaction": interaction,
        "time_seconds": time_seconds,
        "time": f"{time_seconds:.2f}",
        "pedestrian_track_id": 1,
        "vehicle_track_id": 2,
        "risk_score": score,
        "risk_time_component": 0.8,
        "risk_distance_component": 0.5,
        "risk_level": "High" if score >= 0.6 else "Medium" if score >= 0.3 else "Low",
        "t_cpa": 1.0,
        "d_cpa": 2.0,
        "closing_rate": 2.0,
        "ttc": 1.0,
        "pet": None,
        "pedestrian_path": [[0.0, 5.0, 0.0], [1.0, 5.0, 0.0], [2.0, 5.0, 0.0], [3.0, 5.0, 0.0]],
        "vehicle_path": [[0.0, 0.0, 0.0], [1.0, 2.0, 0.0], [2.0, 4.0, 0.0], [3.0, 6.0, 0.0]],
    }


class AlertingTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(
            os.environ,
            {"CAUSALGUARD_DATA_DIR": self.temporary_directory.name},
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary_directory.cleanup()

    def test_consecutive_candidate_observation_count_uses_saved_synchronized_paths(self):
        self.assertEqual(consecutive_candidate_observations(make_event()), 3)

    def test_build_alert_records_uses_saved_candidate_score_and_review_status(self):
        video = save_video(b"video data", "road.mp4")
        event = make_event()
        settings = dict(DEFAULT_ALERT_SETTINGS)
        alerts = build_alert_records(
            [{
                "video_id": video["video_id"],
                "original_name": video["original_name"],
                "analysis": {"events": [event]},
            }],
            settings,
            {(video["video_id"], event["event_id"]): "Acknowledged"},
        )

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["risk_level"], "High")
        self.assertEqual(alerts[0]["status"], "Acknowledged")
        self.assertIn("CPA rule", alerts[0]["trigger_reason"])

    def test_minimum_observation_requirement_filters_alerts(self):
        event = make_event()
        settings = dict(DEFAULT_ALERT_SETTINGS, min_consecutive_observations=4)
        alerts = build_alert_records(
            [{"video_id": "video", "analysis": {"events": [event]}}],
            settings,
            {},
        )
        self.assertEqual(alerts, [])

    def test_duplicate_suppression_deduplicates_same_interaction_within_window(self):
        settings = dict(DEFAULT_ALERT_SETTINGS)
        events = [
            make_event("EV-1", 1.0),
            make_event("EV-2", 3.0),
            make_event("EV-3", 12.0),
        ]
        alerts = build_alert_records(
            [{"video_id": "video", "analysis": {"events": events}}],
            settings,
            {},
        )
        self.assertEqual([alert["event_id"] for alert in alerts], ["EV-1", "EV-3"])

    def test_severity_uses_configured_thresholds(self):
        settings = dict(DEFAULT_ALERT_SETTINGS, medium_threshold=0.25, high_threshold=0.75)
        self.assertEqual(alert_severity(0.2, settings), "Low")
        self.assertEqual(alert_severity(0.5, settings), "Medium")
        self.assertEqual(alert_severity(0.9, settings), "High")

    def test_alert_settings_and_review_state_are_persistent(self):
        video = save_video(b"video data", "road.mp4")
        settings = dict(DEFAULT_ALERT_SETTINGS, high_threshold=0.7, show_low=True)
        save_alert_settings(settings)
        set_alert_status(video["video_id"], "EV-1", "Resolved")

        self.assertEqual(get_alert_settings()["high_threshold"], 0.7)
        self.assertTrue(get_alert_settings()["show_low"])
        self.assertEqual(
            get_alert_reviews()[(video["video_id"], "EV-1")],
            "Resolved",
        )

    def test_invalid_threshold_order_is_rejected(self):
        settings = dict(DEFAULT_ALERT_SETTINGS, medium_threshold=0.7, high_threshold=0.6)
        with self.assertRaisesRegex(VideoLibraryError, "0 ≤ medium < high ≤ 1"):
            save_alert_settings(settings)

    def test_selected_video_alert_triggers_at_high_risk_threshold(self):
        event = make_event(score=0.60)
        alert = evaluate_video_alert({"events": [event]})
        self.assertEqual(alert["status"], "ALERT TRIGGERED")
        self.assertEqual(alert["event"], event)

    def test_selected_video_without_high_risk_is_calm(self):
        event = make_event(score=0.59)
        alert = evaluate_video_alert({"events": [event]})
        self.assertEqual(alert["status"], "No High-Risk Alert")
        self.assertEqual(alert["event"], event)

    def test_selected_video_without_analysis_requires_analysis(self):
        self.assertEqual(
            evaluate_video_alert(None),
            {"status": "Analysis Required", "event": None},
        )

    def test_selected_video_with_only_invalid_risk_records_has_insufficient_data(self):
        invalid_events = [
            make_event(score=float("nan")),
            make_event(score=1.2),
            {**make_event(), "time_seconds": float("inf")},
            {**make_event(), "pedestrian_track_id": None},
        ]
        alert = evaluate_video_alert({"events": invalid_events})
        self.assertEqual(alert["status"], "Insufficient Data")
        self.assertIsNone(alert["event"])

    def test_evaluation_uses_only_the_provided_video_analysis(self):
        high_risk_video = {"events": [make_event("HIGH", score=0.91)]}
        low_risk_video = {"events": [make_event("LOW", score=0.42)]}

        self.assertEqual(evaluate_video_alert(high_risk_video)["status"], "ALERT TRIGGERED")
        selected_low = evaluate_video_alert(low_risk_video)
        self.assertEqual(selected_low["status"], "No High-Risk Alert")
        self.assertEqual(selected_low["event"]["event_id"], "LOW")


if __name__ == "__main__":
    unittest.main()
