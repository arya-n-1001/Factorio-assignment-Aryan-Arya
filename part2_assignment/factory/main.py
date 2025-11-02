#!/usr/bin/env python
import sys
import json
import numpy as np
from scipy.optimize import linprog
from typing import Dict, Any, List, Tuple

TOLERANCE = 1e-9
LP_SOLVER_METHOD = 'highs'  # using the newer highs solver


class FactorySolver:
    # Class that stores LP data and solves for factory layout

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.recipes = data["recipes"]
        self.recipe_names = sorted(self.recipes.keys())
        self.num_recipes = len(self.recipe_names)
        self.recipe_to_index = {name: i for i, name in enumerate(self.recipe_names)}

        self.target_item = data["target"]["item"]

        self._identify_items()
        self._calculate_effective_values()

    def _identify_items(self):
        # Figure out what items exist and categorize them

        all_items = set()
        self.raw_items = set(self.data.get("limits", {}).get("raw_supply_per_min", {}).keys())

        for r in self.recipes.values():
            all_items.update(r.get("in", {}).keys())
            all_items.update(r.get("out", {}).keys())

        self.intermediate_items = all_items - self.raw_items - {self.target_item}

        self.item_names = sorted(list(all_items))
        self.item_to_index = {name: i for i, name in enumerate(self.item_names)}
        self.num_items = len(self.item_names)

    def _calculate_effective_values(self):
        # Precompute crafting speed and output amounts (after module effects)

        self.objective_c = np.zeros(self.num_recipes)
        self.eff_outputs: Dict[str, Dict[str, float]] = {}
        self.eff_crafts: Dict[str, float] = {}

        machines_map = self.data["machines"]
        modules_map = self.data.get("modules", {})

        for i, r_name in enumerate(self.recipe_names):
            recipe = self.recipes[r_name]
            machine_name = recipe["machine"]
            machine = machines_map[machine_name]
            modules = modules_map.get(machine_name, {})

            base_speed = machine["crafts_per_min"]
            mod_speed = modules.get("speed", 0.0)
            time_s = recipe["time_s"]

            if time_s > 0:
                eff_crafts_per_min = base_speed * (1 + mod_speed) * 60.0 / time_s
            else:
                eff_crafts_per_min = float('inf')

            self.eff_crafts[r_name] = eff_crafts_per_min

            if eff_crafts_per_min > 0:
                self.objective_c[i] = (1.0 / eff_crafts_per_min) + (TOLERANCE * (i + 1))
            else:
                self.objective_c[i] = float('inf')

            mod_prod = modules.get("prod", 0.0)
            self.eff_outputs[r_name] = {}

            for item, amount in recipe["out"].items():
                self.eff_outputs[r_name][item] = float(amount) * (1.0 + mod_prod)

    def build_lp_model(self, target_rate: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        # Build LP matrices (A_eq, b_eq, A_ub, b_ub)

        A_eq = np.zeros((self.num_items, self.num_recipes))
        b_eq = np.zeros(self.num_items)

        raw_item_rows = {}

        for i, item in enumerate(self.item_names):
            if item == self.target_item:
                b_eq[i] = target_rate
            elif item in self.intermediate_items:
                b_eq[i] = 0.0
            elif item in self.raw_items:
                b_eq[i] = 0.0
                raw_item_rows[item] = i

            for r, r_name in enumerate(self.recipe_names):
                net_prod = self.eff_outputs[r_name].get(item, 0.0)
                net_prod -= self.recipes[r_name].get("in", {}).get(item, 0.0)
                A_eq[i, r] = net_prod

        A_ub_list: List[np.ndarray] = []
        b_ub_list: List[float] = []

        raw_caps = self.data.get("limits", {}).get("raw_supply_per_min", {})
        for item, cap in raw_caps.items():
            if item in raw_item_rows:
                item_idx = raw_item_rows[item]
                constraint_row = -A_eq[item_idx, :]
                A_ub_list.append(constraint_row)
                b_ub_list.append(cap + TOLERANCE)
                A_eq[item_idx, :] = 0.0

        machine_caps = self.data.get("limits", {}).get("max_machines", {})
        for machine_name, cap in machine_caps.items():
            constraint_row = np.zeros(self.num_recipes)
            for r, r_name in enumerate(self.recipe_names):
                if self.recipes[r_name]["machine"] == machine_name:
                    if self.eff_crafts[r_name] > 0:
                        constraint_row[r] = 1.0 / self.eff_crafts[r_name]

            A_ub_list.append(constraint_row)
            b_ub_list.append(cap + TOLERANCE)

        A_ub = np.array(A_ub_list) if A_ub_list else np.empty((0, self.num_recipes))
        b_ub = np.array(b_ub_list) if b_ub_list else np.empty(0)

        return A_eq, b_eq, A_ub, b_ub

    def solve(self) -> Dict[str, Any]:
        # Solve LP; if infeasible, compute max possible output

        target_rate = self.data["target"]["rate_per_min"]

        A_eq, b_eq, A_ub, b_ub = self.build_lp_model(target_rate)

        result = linprog(
            c=self.objective_c,
            A_eq=A_eq, b_eq=b_eq,
            A_ub=A_ub, b_ub=b_ub,
            bounds=(0, None),
            method=LP_SOLVER_METHOD
        )

        if result.success:
            return self.format_success_output(result)

        # Try to solve a second LP to find max feasible rate
        num_vars = self.num_recipes + 1
        y_idx = self.num_recipes

        c_p2 = np.zeros(num_vars)
        c_p2[y_idx] = -1.0

        A_eq_p2 = np.zeros((self.num_items, num_vars))
        A_eq_p2[:, :self.num_recipes] = A_eq[:, :self.num_recipes]
        b_eq_p2 = np.zeros(self.num_items)

        A_eq_p2[self.item_to_index[self.target_item], y_idx] = -target_rate

        A_ub_p2 = np.zeros((A_ub.shape[0], num_vars))
        A_ub_p2[:, :self.num_recipes] = A_ub
        b_ub_p2 = b_ub

        bounds = [(0, None) for _ in range(self.num_recipes)] + [(0, 1.0)]

        result_p2 = linprog(
            c=c_p2,
            A_eq=A_eq_p2, b_eq=b_eq_p2,
            A_ub=A_ub_p2, b_ub=b_ub_p2,
            bounds=bounds,
            method=LP_SOLVER_METHOD
        )

        if result_p2.success:
            max_y = result_p2.x[y_idx]
            max_rate = max_y * target_rate
            return self.format_infeasible_output(max_rate)
        else:
            return self.format_infeasible_output(0.0)

    def format_success_output(self, lp_result: Any) -> Dict[str, Any]:
        # Convert successful solve into JSON returned to caller

        x_r = lp_result.x
        machine_counts: Dict[str, float] = {}

        for r, r_name in enumerate(self.recipe_names):
            if x_r[r] > TOLERANCE:
                machine_name = self.recipes[r_name]["machine"]
                if self.eff_crafts[r_name] > 0:
                    machines_used = x_r[r] / self.eff_crafts[r_name]
                    machine_counts[machine_name] = machine_counts.get(machine_name, 0.0) + machines_used

        raw_consumption: Dict[str, float] = {}
        for item in self.raw_items:
            if item not in self.item_to_index:
                continue

            consumption = 0.0
            for r, r_name in enumerate(self.recipe_names):
                consumption += (
                    self.recipes[r_name].get("in", {}).get(item, 0.0)
                    - self.eff_outputs[r_name].get(item, 0.0)
                ) * x_r[r]

            if consumption > TOLERANCE:
                raw_consumption[item] = consumption

        return {
            "status": "ok",
            "per_recipe_crafts_per_min": {r_name: x_r[i] for i, r_name in enumerate(self.recipe_names)},
            "per_machine_counts": machine_counts,
            "raw_consumption_per_min": raw_consumption
        }

    def format_infeasible_output(self, max_rate: float) -> Dict[str, Any]:
        # Format response for infeasible LP runs

        return {
            "status": "infeasible",
            "max_feasible_target_per_min": max_rate,
            "bottleneck_hint": ["Review machine or raw material caps"]
        }


def main():
        # Entry point: read JSON, run solver, output JSON

    try:
        input_data = json.load(sys.stdin)

        solver = FactorySolver(input_data)
        output_data = solver.solve()

    except Exception as e:
        output_data = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        }

    print(json.dumps(output_data, indent=2))


if __name__ == "__main__":
    main()
