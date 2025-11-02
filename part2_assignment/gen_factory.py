import json
import sys
import random

def generate_factory_problem(seed=None):
    # Generates a random, likely feasible factory optimization problem.
    # Randomizes machines, recipes, and target rate.
    # Intended to produce graphs that can be used by your solver.

    if seed:
        random.seed(seed)

    num_machines = random.randint(2, 4)
    num_recipes = random.randint(4, 8)
    num_raw = random.randint(2, 3)

    machines = {}
    machine_names = []
    for i in range(num_machines):
        name = f"machine_{i+1}"
        # Random crafting speed for each machine
        machines[name] = {"crafts_per_min": random.choice([30, 60, 90, 120])}
        machine_names.append(name)

    raw_items = [f"raw_{i+1}" for i in range(num_raw)]

    recipes = {}
    items_so_far = list(raw_items)

    # Force recipes to form a chain where each output becomes available
    for i in range(num_recipes):
        r_name = f"recipe_{i+1}"

        # Inputs: 1–2 items from raw or previously created items
        num_in = random.randint(1, 2)
        recipe_in = {}
        for _ in range(num_in):
            item = random.choice(items_so_far)
            recipe_in[item] = random.randint(1, 3)

        # Output: a new item that becomes available for future recipes
        new_item = f"item_{i+1}"
        recipe_out = {new_item: random.randint(1, 2)}
        items_so_far.append(new_item)

        recipes[r_name] = {
            "machine": random.choice(machine_names),
            "time_s": round(random.uniform(0.5, 5.0), 1),
            "in": recipe_in,
            "out": recipe_out
        }

    # Final item = last produced item in chain
    target_item = items_so_far[-1]
    target_rate = random.randint(50, 200)

    # Supply limits and machine limits
    limits = {
        "raw_supply_per_min": {item: random.randint(1000, 5000) for item in raw_items},
        "max_machines": {name: random.randint(100, 500) for name in machine_names}
    }

    # No modules used in this simplified version
    modules = {}

    problem = {
        "machines": machines,
        "recipes": recipes,
        "modules": modules,
        "limits": limits,
        "target": {
            "item": target_item,
            "rate_per_min": target_rate
        }
    }

    return problem


def main():
    # Optional command-line seed argument for reproducibility
    seed = sys.argv[1] if len(sys.argv) > 1 else None

    problem = generate_factory_problem(seed)

    # Output generated problem as JSON
    print(json.dumps(problem, indent=2))


if __name__ == "__main__":
    main()
