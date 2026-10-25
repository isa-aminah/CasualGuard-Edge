import importlib.util
import unittest
from pathlib import Path


PAGE_PATH = Path(__file__).resolve().parents[1] / "app" / "pages" / "3_Causal_Analysis.py"
PAGE_SPEC = importlib.util.spec_from_file_location("causal_analysis_page", PAGE_PATH)
causal_page = importlib.util.module_from_spec(PAGE_SPEC)
PAGE_SPEC.loader.exec_module(causal_page)


class CausalAnalysisEvidenceTests(unittest.TestCase):
    def test_missing_event_metrics_are_explicitly_unavailable(self):
        table = causal_page._event_evidence_table({
            "time": "1.25",
            "pedestrian_track_id": 4,
            "vehicle_track_id": 8,
            "speed_unit": "px/s",
            "distance_unit": "px",
            "relative_motion": "Closing",
            "t_cpa": 1.0,
            "d_cpa": 20.0,
            "closing_rate": 5.0,
            "risk_score": None,
            "risk_level": None,
        })

        self.assertIn("TTC", table)
        self.assertIn("PET", table)
        self.assertIn("Unavailable", table)

    def test_candidate_rule_is_unavailable_without_required_cpa_metrics(self):
        self.assertEqual(
            causal_page._candidate_rule_status({"t_cpa": 1.0, "d_cpa": None, "closing_rate": 2.0}),
            "Unavailable · required CPA metrics are missing",
        )

    def test_risk_component_chart_uses_half_weighted_observed_inputs(self):
        figure = causal_page._risk_component_figure({
            "risk_time_component": 0.8,
            "risk_distance_component": 0.4,
        })

        self.assertEqual(list(figure.data[0].x), [0.4, 0.2])
        self.assertEqual(list(figure.data[0].y), [
            "Time-related contribution",
            "Separation-related contribution",
        ])

    def test_proposed_scm_uses_the_selected_video_and_event_measurements(self):
        event = {
            "event_id": "EV-23",
            "interaction": "P03 - V08",
            "pedestrian_track_id": 3,
            "vehicle_track_id": 8,
            "pedestrian_speed": 12.5,
            "vehicle_speed": 41.0,
            "speed_unit": "px/s",
            "relative_motion": "Closing",
            "d_cpa": 4.5,
            "distance": 9.0,
            "closing_rate": 7.5,
            "t_cpa": 1.25,
            "ttc": 1.6,
            "pet": None,
            "risk_score": 0.72,
            "risk_level": "High",
            "risk_time_component": 0.6,
            "risk_distance_component": 0.84,
        }
        figure = causal_page._proposed_scm_figure(event, "Night Crossing.mp4", "video-id-123456789")

        self.assertIn("Night Crossing.mp4", figure.layout.title.text)
        self.assertIn("EV-23", figure.layout.title.text)
        annotations = [annotation.text for annotation in figure.layout.annotations]
        self.assertTrue(any("41.0 px/s" in text for text in annotations))
        self.assertTrue(any("4.5 px" in text for text in annotations))
        self.assertTrue(any("1.60 s" in text for text in annotations))
        self.assertTrue(any("0.720" in text for text in annotations))
        self.assertTrue(any("<br><br>" in text for text in annotations))
        self.assertTrue(any(
            "Not annotated" in text and "#a8b6c9" in text
            for text in annotations
        ))
        self.assertEqual(figure.layout.height, 500)


if __name__ == "__main__":
    unittest.main()
