import unittest
import json
import subprocess
import sys
import os

# --- PATHS ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTORY_SCRIPT = os.path.join(PROJECT_ROOT, "factory", "main.py")
TEST_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "test_outputs")

if not os.path.exists(TEST_OUTPUT_DIR):
    os.makedirs(TEST_OUTPUT_DIR)


class TestFactorySolver(unittest.TestCase):

    def run_solver(self, input_data, output_filename=None):
        # Runs main.py as subprocess with JSON input and optionally writes result
        python_exe = sys.executable
        input_json = json.dumps(input_data)

        process = subprocess.run(
            [python_exe, FACTORY_SCRIPT],
            input=input_json,
            text=True,
            capture_output=True,
            cwd=PROJECT_ROOT
        )

        if process.stderr:
            print("Solver STDERR:", process.stderr)

        self.assertEqual(process.returncode, 0, "Solver script failed")

        try:
            output_data = json.loads(process.stdout)
        except json.JSONDecodeError:
            self.fail(f"Solver did not output valid JSON. Output: {process.stdout}")

        if output_filename:
            output_path = os.path.join(TEST_OUTPUT_DIR, output_filename)
            with open(output_path, 'w') as f:
                json.dump(output_data, f, indent=2)

        return output_data

    def test_green_circuit_simple(self):
        # Checks a valid simple green-circuit factory
        test_input = {
          "machines": {
            "assembler_1": {"crafts_per_min": 30},
            "steel_furnace": {"crafts_per_min": 120}
          },
          "recipes": {
            "iron_plate": {"machine": "steel_furnace", "time_s": 3.2, "in": {"iron_ore": 1}, "out": {"iron_plate": 1}},
            "copper_plate": {"machine": "steel_furnace", "time_s": 3.2, "in": {"copper_ore": 1}, "out": {"copper_plate": 1}},
            "copper_wire": {"machine": "assembler_1", "time_s": 0.5, "in": {"copper_plate": 1}, "out": {"copper_wire": 2}},
            "green_circuit": {"machine": "assembler_1", "time_s": 0.5, "in": {"iron_plate": 1, "copper_wire": 3}, "out": {"green_circuit": 1}}
          },
          "modules": {},
          "limits": {
            "raw_supply_per_min": {
              "iron_ore": 1000,
              "copper_ore": 1000
            },
            "max_machines": {
              "steel_furnace": 8,
              "assembler_1": 3
            }
          },
          "target": {
            "item": "green_circuit",
            "rate_per_min": 60
          }
        }

        output = self.run_solver(test_input, "factory_feasible_output.json")

        self.assertEqual(output.get("status"), "ok")

        recipes = output.get("per_recipe_crafts_per_min", {})
        self.assertAlmostEqual(recipes.get("green_circuit"), 60.0)
        self.assertAlmostEqual(recipes.get("copper_wire"), 90.0)

        raw = output.get("raw_consumption_per_min", {})
        self.assertAlmostEqual(raw.get("copper_ore"), 90.0)

    def test_infeasible_copper_limit(self):
        # Ensures solving fails when copper ore supply is too low
        test_input = {
          "machines": {
            "assembler_1": {"crafts_per_min": 30},
            "steel_furnace": {"crafts_per_min": 120}
          },
          "recipes": {
            "iron_plate": {"machine": "steel_furnace", "time_s": 3.2, "in": {"iron_ore": 1}, "out": {"iron_plate": 1}},
            "copper_plate": {"machine": "steel_furnace", "time_s": 3.2, "in": {"copper_ore": 1}, "out": {"copper_plate": 1}},
            "copper_wire": {"machine": "assembler_1", "time_s": 0.5, "in": {"copper_plate": 1}, "out": {"copper_wire": 2}},
            "green_circuit": {"machine": "assembler_1", "time_s": 0.5, "in": {"iron_plate": 1, "copper_wire": 3}, "out": {"green_circuit": 1}}
          },
          "modules": {},
          "limits": {
            "raw_supply_per_min": {
              "iron_ore": 1000,
              "copper_ore": 80
            },
            "max_machines": {
              "steel_furnace": 8,
              "assembler_1": 3
            }
          },
          "target": {
            "item": "green_circuit",
            "rate_per_min": 60
          }
        }

        output = self.run_solver(test_input, "factory_infeasible_output.json")

        self.assertEqual(output.get("status"), "infeasible")
        self.assertIn("Review machine or raw material caps", output.get("bottleneck_hint", []))
        self.assertAlmostEqual(output.get("max_feasible_target_per_min"), 60.0 * (80.0 / 90.0))


if __name__ == "__main__":
    unittest.main()
