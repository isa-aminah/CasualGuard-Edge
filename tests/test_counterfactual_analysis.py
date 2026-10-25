import importlib.util
import unittest
from pathlib import Path


PAGE_PATH = Path(__file__).resolve().parents[1] / "app" / "pages" / "4_Counterfactual_Analysis.py"
PAGE_SPEC = importlib.util.spec_from_file_location("counterfactual_page", PAGE_PATH)
counterfactual_page = importlib.util.module_from_spec(PAGE_SPEC)
PAGE_SPEC.loader.exec_module(counterfactual_page)


class CounterfactualAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.event = {
            "time_seconds": 0.0,
            "distance_unit": "px",
            "pedestrian_path": [
                [0.0, 5.0, 0.0],
                [1.0, 5.0, 0.0],
                [2.0, 5.0, 0.0],
                [3.0, 5.0, 0.0],
            ],
            "vehicle_path": [
                [0.0, 0.0, 0.0],
                [1.0, 2.0, 0.0],
                [2.0, 4.0, 0.0],
                [3.0, 6.0, 0.0],
            ],
        }

    def test_position_at_interpolates_between_points(self):
        position = counterfactual_page._position_at(
            [[0.0, 0.0, 0.0], [2.0, 10.0, 20.0]],
            1.0,
        )
        self.assertEqual(position, (5.0, 10.0))

    def test_position_at_returns_none_outside_track(self):
        position = counterfactual_page._position_at(
            [[1.0, 2.0, 3.0], [2.0, 4.0, 6.0]],
            0.5,
        )
        self.assertIsNone(position)

    def test_simulate_rejects_insufficient_track_points(self):
        with self.assertRaisesRegex(ValueError, "not contain enough"):
            counterfactual_page._simulate(
                {
                    "pedestrian_path": [[0.0, 1.0, 1.0]],
                    "vehicle_path": [[0.0, 2.0, 2.0]],
                },
                "Reduce vehicle speed",
                20.0,
            )

    def test_zero_interventions_preserve_the_selected_baseline(self):
        scenarios = (
            ("Reduce vehicle speed", 0.0),
            ("Earlier braking", (0.0, 0.0)),
            ("Alternative pedestrian timing", 0.0),
        )
        for scenario, value in scenarios:
            with self.subTest(scenario=scenario):
                result = counterfactual_page._simulate(self.event, scenario, value, 0.0)
                self.assertEqual(result["baseline"]["cpa"], result["scenario"]["cpa"])
                self.assertEqual(result["baseline"]["vehicle_speed"], result["scenario"]["vehicle_speed"])

    def test_speed_reduction_recomputes_speed_and_risk_delta(self):
        result = counterfactual_page._simulate(
            self.event,
            "Reduce vehicle speed",
            50.0,
            0.0,
        )
        self.assertAlmostEqual(result["baseline"]["vehicle_speed"], 2.0)
        self.assertAlmostEqual(result["scenario"]["vehicle_speed"], 1.0)
        baseline_risk = result["baseline"]["cpa"]["risk_score"]
        scenario_risk = result["scenario"]["cpa"]["risk_score"]
        self.assertAlmostEqual(scenario_risk - baseline_risk, -0.25, places=3)

    def test_baseline_stays_fixed_while_intervention_values_change(self):
        first = counterfactual_page._simulate(
            self.event,
            "Reduce vehicle speed",
            20.0,
            0.0,
        )
        second = counterfactual_page._simulate(
            self.event,
            "Reduce vehicle speed",
            60.0,
            0.0,
        )
        self.assertEqual(first["baseline"], second["baseline"])
        self.assertNotEqual(first["scenario"]["vehicle_speed"], second["scenario"]["vehicle_speed"])

    def test_braking_applies_assumed_constant_deceleration_after_delay(self):
        result = counterfactual_page._simulate(
            self.event,
            "Earlier braking",
            (0.0, 0.5),
            0.0,
        )
        self.assertEqual(result["baseline"]["vehicle_speed"], 2.0)
        self.assertLess(result["scenario_vehicle"][-1][1], result["vehicle"][-1][1])

    def test_pedestrian_time_shift_uses_only_observed_overlap(self):
        result = counterfactual_page._simulate(
            self.event,
            "Alternative pedestrian timing",
            0.5,
            0.0,
        )
        self.assertEqual(len(result["scenario_pedestrian"]), 3)
        self.assertEqual(result["scenario_pedestrian"][0][0], 1.0)
        self.assertEqual(result["scenario_pedestrian"][0][1:], [5.0, 0.0])

    def test_comparison_shows_delta_r_as_scenario_minus_baseline(self):
        result = counterfactual_page._simulate(
            self.event,
            "Reduce vehicle speed",
            50.0,
            0.0,
        )
        rows = counterfactual_page._comparison_rows(result, "px")
        risk_row = next(row for row in rows if row[0] == "Risk score")
        expected_delta = result["scenario"]["cpa"]["risk_score"] - result["baseline"]["cpa"]["risk_score"]
        self.assertEqual(float(risk_row[3]), round(expected_delta, 3))

    def test_scenario_statement_names_event_and_rule_based_change(self):
        result = counterfactual_page._simulate(
            self.event,
            "Reduce vehicle speed",
            50.0,
            0.0,
        )
        statement = counterfactual_page._scenario_interpretation(
            result,
            {"interaction": "P01 - V02"},
            "Reduce vehicle speed",
            50.0,
        )
        self.assertIn("P01 - V02", statement)
        self.assertIn("ΔR = Rscenario − Rbaseline", statement)
        self.assertIn("near-miss candidate rule", statement)
        self.assertIn("does not show that a real-world collision", statement)


if __name__ == "__main__":
    unittest.main()
