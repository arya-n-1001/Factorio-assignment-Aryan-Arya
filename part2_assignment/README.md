# Factorio Assignment (Part 2)

This repository contains the solutions for Part A (Factory Steady State) and Part B (Bounded Belts). Both are command-line tools written in Python 3 that read `JSON` from `stdin` and write `JSON` to `stdout`.

## Core Technology Choices

This solution is implemented in **Python 3**. The primary engineering decision was to use industry-standard, robust libraries for the core "engines" rather than relying on custom-built (and potentially buggy) solvers.

* **Part A (Factory):** Solved using **`scipy.optimize.linprog`**. This is a powerful, correct, and well-maintained Linear Programming solver.
* **Part B (Belts):** Solved using **`networkx.maximum_flow`**. This is the standard Python library for graph theory and provides a correct, high-performance max-flow implementation. This was a deliberate choice to replace a buggy, custom-built `Dinic` solver found in a reference repository.

---

## File & Directory Structure

Here is a breakdown of all files in this project:

* **`factory/main.py`**: **(Part A Solver)** The main executable for the Factory Steady State problem.
* **`belts/main.py`**: **(Part B Solver)** The main executable for the Bounded Belts flow problem.
* **`tests/`**: A folder containing all unit tests.
    * `test_factory.py`: Tests the `factory` solver with both feasible and infeasible inputs.
    * `test_belts.py`: Tests the `belts` solver with both feasible and infeasible inputs.
* **`verify_factory.py`**: (Optional) A validation helper that reads an `input.json` and `output.json` and confirms if the solution is valid.
* **`verify_belts.py`**: (Optional) A validation helper that reads a `belts_input.json` and `belts_output.json` and confirms if the flow is valid.
* **`gen_factory.py`**: (Optional) A script to generate random, new factory problems for stress-testing.
* **`gen_belts.py`**: (Optional) A script to generate random, new belt graph problems for stress-testing.
* **`run_samples.py`**: The main test runner script, which discovers and runs all tests in the `tests/` folder.
* **`README.md`**: (This file) The detailed design note explaining all logic and decisions.
* **`RUN.md`**: A simple guide with the exact commands to install, run, and test this project.
* **`Submission.txt`**: My personal submission information.
* **`*.json`**: Various input files used for manual and automated testing.

---

## Part A: `factory/main.py` Logic

This tool models the entire factory as a **Linear Programming (LP)** problem to find the most efficient, balanced state.

### 1. Core Logic: System of Equations
The core of the model is a set of conservation equations, one for each item in the factory:
`(Total Produced) - (Total Consumed) = Net Result`

The variables we are solving for (`x` in `Ax=b`) are the **`crafts_per_min`** for each recipe.

### 2. Model & Equations
* **Intermediates:** For items like `copper_wire`, the `Net Result` is set to **0**. This enforces the "steady state" rule and ensures perfect balance (no surplus, no deficit). This model inherently handles complex **recipe cycles** and **byproducts**, as all intermediates must perfectly balance to zero.
* **Target Item:** For the `green_circuit`, the `Net Result` is set to the exact `target_rate` (e.g., 60).
* **Raw Materials:** For `iron_ore`, the `Net Result` is a variable representing net consumption. This consumption is then constrained to be less than or equal to the `raw_supply_per_min` cap.

### 3. Constraints & Modules
* **Modules:** All module effects are pre-calculated. `prod` modules modify the `(Total Produced)` term in the conservation equation, and `speed` modules are used to calculate the `effective_craft_speed` of each machine.
* **Machine Caps:** A final constraint is added for each machine type, ensuring the total machines used does not exceed the `max_machines` cap. The formula for total machines of one type is:
    `sum(recipe_crafts_per_min / effective_craft_speed) <= max_machines`

### 4. Optimization & Infeasibility
This tool uses a two-phase optimization approach to find the *best* answer or the *max possible* answer.

* **Phase 1 (Feasibility):** The script first attempts to solve the LP with the objective to **minimize total machines** while hitting the *full* requested `target_rate`.
* **Phase 2 (Infeasibility):** If Phase 1 fails (meaning the target is impossible), the tool does not give up. It builds and solves a *new* problem.
    * **New Variable:** A scaling factor `y` (from 0.0 to 1.0) is added.
    * **New Objective:** `maximize y`.
    * **New Target Equation:** `(Total Produced) - (Total Consumed) = y * target_rate`.
    * This finds the highest possible percentage of the target the factory can *actually* produce. The script then reports `"status": "infeasible"` and the calculated `max_feasible_target_per_min` (which is `y * target_rate`).

### 5. Numeric Approach & Determinism
* **Solver:** `scipy.optimize.linprog(method='highs')`. The `highs` solver is modern, fast, robust, and deterministic.
* **Tie-breaking:** To ensure deterministic results when two solutions have the *exact* same machine cost, a tiny, unique cost (`TOLERANCE * recipe_index`) is added to each recipe's machine-cost objective. This ensures the solver always picks the same answer.

---

## Part B: `belts/main.py` Logic

This tool models the belt network as a **Max-Flow with Demands** problem.

### 1. Engine Choice
This solution uses the **`networkx`** library. This was a deliberate engineering decision to ensure correctness. An initial investigation of a custom-built `Dinic` solver from a reference repository revealed it was buggy and produced incorrect flow values. The `networkx` library is the standard, correct, and robust tool for graph analysis in Python.

### 2. Graph Transformation
A real-world belt network has complex rules. To solve it, the input graph is transformed into a standard max-flow problem using two main tricks:

* **Node Splitting (for Splitter Caps):** A node `v` with a `node_cap` of 500 is split into two nodes, `v_IN` and `v_OUT`. A single edge `v_IN -> v_OUT` is added with a capacity of 500. All edges that originally went *to* `v` now go to `v_IN`, and all edges *from* `v` now come from `v_OUT`. This correctly limits the total throughput of the original node.
* **Lower Bounds (for Belt Minimums):** An edge `u -> v` with a `lo` bound of 50 is transformed. This "demand" is handled by:
    1.  Adding `50` as a "demand" at the destination node (`v`).
    2.  Adding `50` as a "supply" at the source node (`u`).
    3.  Setting the edge's capacity in the graph to `hi - lo`.

### 3. Feasibility Check
A super-source (`S*`) and super-sink (`T*`) are added to the graph. `S*` connects to all "supply" nodes, and all "demand" nodes connect to `T*`. The solution is **feasible if and only if** the resulting `max_flow` from `S*` to `T*` is *exactly equal* to the `total_demand` of the graph.

### 4. Infeasibility Certificate
If `max_flow < total_demand`, the system is infeasible. The `networkx.minimum_cut` function is used to find the bottleneck. The set of `cut_reachable` nodes (nodes on the source-side of the bottleneck) is reported to the user.