import unittest

from app.video_processing import (
    _build_interaction_events,
    calculate_cpa_metrics,
    calculate_pet,
    qualifies_near_miss,
    risk_level,
)


class NearMissMetricTests(unittest.TestCase):
    def test_cpa_ttc_and_weighted_risk_follow_the_specified_formulas(self):
        times = [index / 10 for index in range(6)]
        pedestrian_path = [[time, 0.0, 0.0] for time in times]
        vehicle_path = [[time, 10.0 - 5.0 * time, 5.0] for time in times]

        metrics = calculate_cpa_metrics(pedestrian_path, vehicle_path)

        self.assertIsNotNone(metrics)
        self.assertAlmostEqual(metrics["t_cpa"], 1.5, places=6)
        self.assertAlmostEqual(metrics["d_cpa"], 5.0, places=6)
        self.assertAlmostEqual(metrics["ttc"], metrics["distance"] / metrics["closing_rate"], places=6)
        expected_risk = 0.5 * (1 - 1.5 / 3.0) + 0.5 * (1 - 5.0 / 8.0)
        self.assertAlmostEqual(metrics["risk_score"], expected_risk, places=6)
        self.assertTrue(qualifies_near_miss(metrics))

    def test_diverging_tracks_have_no_future_cpa(self):
        times = [index / 10 for index in range(6)]
        pedestrian_path = [[time, 0.0, 0.0] for time in times]
        vehicle_path = [[time, 10.0 + 5.0 * time, 0.0] for time in times]

        self.assertIsNone(calculate_cpa_metrics(pedestrian_path, vehicle_path))

    def test_near_miss_boundaries_and_risk_bands(self):
        self.assertTrue(qualifies_near_miss({"t_cpa": 3.0, "d_cpa": 80.0, "closing_rate": 0.1}))
        self.assertFalse(qualifies_near_miss({"t_cpa": 0.0, "d_cpa": 1.0, "closing_rate": 1.0}))
        self.assertFalse(qualifies_near_miss({"t_cpa": 3.01, "d_cpa": 1.0, "closing_rate": 1.0}))
        self.assertFalse(qualifies_near_miss({"t_cpa": 1.0, "d_cpa": 80.01, "closing_rate": 1.0}))
        self.assertFalse(qualifies_near_miss({"t_cpa": 1.0, "d_cpa": 1.0, "closing_rate": 0.0}))
        self.assertEqual(risk_level(0.299), "Low")
        self.assertEqual(risk_level(0.30), "Medium")
        self.assertEqual(risk_level(0.599), "Medium")
        self.assertEqual(risk_level(0.60), "High")

    def test_pet_is_the_signed_gap_between_zone_occupancies(self):
        pedestrian_path = [[0.0, -2.0, 0.0], [1.0, 0.0, 0.0], [2.0, 2.0, 0.0]]
        vehicle_path = [[2.0, -2.0, 0.0], [3.0, 0.0, 0.0], [4.0, 2.0, 0.0]]

        pet = calculate_pet(pedestrian_path, vehicle_path, (0.0, 0.0), 0.5)

        self.assertEqual(pet, 1.5)

    def test_pet_is_negative_when_zone_occupancies_overlap(self):
        pedestrian_path = [[0.0, -2.0, 0.0], [1.0, 0.0, 0.0], [2.0, 2.0, 0.0]]
        vehicle_path = [[0.25, -2.0, 0.0], [1.25, 0.0, 0.0], [2.25, 2.0, 0.0]]

        pet = calculate_pet(pedestrian_path, vehicle_path, (0.0, 0.0), 0.5)

        self.assertEqual(pet, -0.25)

    def test_pet_is_unavailable_if_both_tracks_do_not_cross_zone(self):
        pedestrian_path = [[0.0, -2.0, 0.0], [1.0, -1.0, 0.0], [2.0, -2.0, 0.0]]
        vehicle_path = [[0.0, 2.0, 0.0], [1.0, 3.0, 0.0], [2.0, 2.0, 0.0]]

        self.assertIsNone(calculate_pet(pedestrian_path, vehicle_path, (0.0, 0.0), 0.5))

    def test_interaction_events_include_a_video_derived_pet_and_zone(self):
        pedestrian_observations = []
        vehicle_observations = []
        for frame in range(31):
            time = frame / 10
            pedestrian_x = -10 + 10 * time
            vehicle_y = 20 - 10 * time
            pedestrian_observations.append({
                "frame": frame,
                "time": time,
                "x": pedestrian_x,
                "y": 0.0,
                "box": [pedestrian_x - 5, -10, pedestrian_x + 5, 10],
            })
            vehicle_observations.append({
                "frame": frame,
                "time": time,
                "x": 0.0,
                "y": vehicle_y,
                "box": [-10, vehicle_y - 5, 10, vehicle_y + 5],
            })

        events = _build_interaction_events(
            {
                1: {"kind": "pedestrian", "observations": pedestrian_observations},
                2: {"kind": "vehicle", "observations": vehicle_observations},
            },
            video_id="abcdef123456",
            fps=10.0,
        )

        self.assertEqual(len(events), 1)
        self.assertIsNotNone(events[0]["pet"])
        self.assertGreater(events[0]["conflict_zone"]["radius"], 0)
        self.assertAlmostEqual(
            events[0]["shared_observation_duration_s"], 3.0
        )
        self.assertFalse(events[0]["trajectory_coverage_warning"])

    def test_short_shared_observation_sets_coverage_warning(self):
        pedestrian_observations = []
        vehicle_observations = []

        for frame in range(6):
            time = frame / 10
            pedestrian_x = -10 + 10 * time
            vehicle_y = 20 - 10 * time

            pedestrian_observations.append({
                "frame": frame,
                "time": time,
                "x": pedestrian_x,
                "y": 0.0,
                "box": [pedestrian_x - 5, -10, pedestrian_x + 5, 10],
            })
            vehicle_observations.append({
                "frame": frame,
                "time": time,
                "x": 0.0,
                "y": vehicle_y,
                "box": [-10, vehicle_y - 5, 10, vehicle_y + 5],
            })

        events = _build_interaction_events(
            {
                1: {"kind": "pedestrian", "observations": pedestrian_observations},
                2: {"kind": "vehicle", "observations": vehicle_observations},
            },
            video_id="abcdef123456",
            fps=10.0,
        )

        self.assertEqual(len(events), 1)
        self.assertAlmostEqual(events[0]["shared_observation_duration_s"], 0.5)
        self.assertTrue(events[0]["trajectory_coverage_warning"])

if __name__ == "__main__":
    unittest.main()
