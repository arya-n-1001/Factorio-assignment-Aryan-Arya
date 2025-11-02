import unittest
import json
import subprocess
import sys
import os

# --- PATHS ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BELTS_SCRIPT = os.path.join(PROJECT_ROOT, "belts", "main.py")
TEST_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "test_outputs")

if not os.path.exists(TEST_OUTPUT_DIR):
    os.makedirs(TEST_OUTPUT_DIR)


class TestBeltsSolver(unittest.TestCase):

    def run_solver(self, input_data, output_filename=None):
        # Helper to run belts/main.py as a subprocess with JSON input.
        python_exe = sys.executable
        input_json = json.dumps(input_data)

        process = subprocess.run(
            [python_exe, BELTS_SCRIPT],
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
            with open(output_path, "w") as f:
                json.dump(output_data, f, indent=2)

        return output_data

    def test_belts_simple_feasible(self):
        # Tests a simple feasible flow graph with a lower bound constraint.
        test_input = {
          "nodes": ["s1", "a", "k1"],
          "edges": [
            {"from": "s1", "to": "a", "hi": 1000},
            {"from": "a", "to": "k1", "lo": 50, "hi": 1000}
          ],
          "node_caps": {
            "a": 500
          },
          "sources": {
            "s1": 400
          },
          "sink": "k1"
        }

        output = self.run_solver(test_input, "belts_feasible_output.json")

        self.assertEqual(output.get("status"), "ok")
        self.assertAlmostEqual(output.get("max_flow_per_min"), 400.0)

        flows = output.get("flows", [])
        self.assertEqual(len(flows), 2)

        flow_map = {(f["from"], f["to"]): f["flow"] for f in flows}
        self.assertAlmostEqual(flow_map.get(("s1", "a")), 400.0)
        self.assertAlmostEqual(flow_map.get(("a", "k1")), 400.0)

    def test_belts_infeasible_node_cap(self):
        # Tests that a failure occurs when a node capacity is the bottleneck.
        test_input = {
          "nodes": ["s1", "a", "k1"],
          "edges": [
            {"from": "s1", "to": "a", "hi": 1000},
            {"from": "a", "to": "k1", "hi": 1000}
          ],
          "node_caps": {
            "a": 500   # Bottleneck: node cap blocks flow from source
          },
          "sources": {
            "s1": 1000
          },
          "sink": "k1"
        }

        output = self.run_solver(test_input, "belts_infeasible_output.json")

        self.assertEqual(output.get("status"), "infeasible")
        self.assertIn("s1", output.get("cut_reachable", []))


if __name__ == "__main__":
    unittest.main()
