import sys
import json
import math
from collections import defaultdict

TOLERANCE = 1e-9

def compute_effective_rates(inp):
    # Re-compute effective machine speeds and output yields (same logic as factory/main.py).
    machines = inp.get("machines", {})
    modules = inp.get("modules", {})
    recipes = inp.get("recipes", {})
    
    eff_crafts = {}
    eff_outputs = {}

    for r_name, r_data in recipes.items():
        machine_name = r_data.get("machine")
        if not machine_name:
            continue

        machine = machines.get(machine_name, {})
        module = modules.get(machine_name, {})

        base_speed = machine.get("crafts_per_min", 0)
        mod_speed = module.get("speed", 0.0)
        time_s = r_data.get("time_s", 1.0)

        if time_s > 0:
            eff_crafts[r_name] = base_speed * (1 + mod_speed) * 60.0 / time_s
        else:
            eff_crafts[r_name] = float('inf')

        # Compute productivity-adjusted output
        mod_prod = module.get("prod", 0.0)
        eff_outputs[r_name] = {}
        for item, amount in r_data.get("out", {}).items():
            eff_outputs[r_name][item] = float(amount) * (1.0 + mod_prod)

    return eff_crafts, eff_outputs


def validate_solution(inp, out):
    # Validate solver output against input rules.
    # Returns a list of error messages (empty if valid).
    errors = []

    # Status must be ok
    if out.get("status") != "ok":
        errors.append(f"Output status is not 'ok': {out.get('status')}")
        return errors

    recipes = inp.get("recipes", {})
    crafts_per_min = out.get("per_recipe_crafts_per_min", {})
    eff_crafts, eff_outputs = compute_effective_rates(inp)

    # Collect every item that could appear
    all_items = set()
    for r_data in recipes.values():
        all_items.update(r_data.get("in", {}).keys())
        all_items.update(r_data.get("out", {}).keys())

    target_item = inp.get("target", {}).get("item")
    target_rate = inp.get("target", {}).get("rate_per_min", 0)
    raw_items = inp.get("limits", {}).get("raw_supply_per_min", {}).keys()

    # Item conservation
    for item in all_items:
        net_balance = 0.0

        for r_name, r_data in recipes.items():
            crafts = crafts_per_min.get(r_name, 0.0)

            # Production
            net_balance += eff_outputs.get(r_name, {}).get(item, 0.0) * crafts

            # Consumption
            net_balance -= r_data.get("in", {}).get(item, 0.0) * crafts

        if item == target_item:
            # Target must match desired output rate
            if not math.isclose(net_balance, target_rate, abs_tol=TOLERANCE):
                errors.append(f"Target '{item}' mismatch: got net {net_balance:.2f}, expected {target_rate}")

        elif item in raw_items:
            # Raw items may not be produced
            if net_balance > TOLERANCE:
                errors.append(f"Raw item '{item}' has net production: {net_balance:.2f}")

        else:
            # Intermediate must net zero
            if not math.isclose(net_balance, 0.0, abs_tol=TOLERANCE):
                errors.append(f"Intermediate '{item}' not balanced: net {net_balance:.2f}")

    # Check raw caps
    raw_caps = inp.get("limits", {}).get("raw_supply_per_min", {})
    raw_consumption = out.get("raw_consumption_per_min", {})
    for item, consumed in raw_consumption.items():
        cap = raw_caps.get(item)
        if cap is not None and consumed > cap + TOLERANCE:
            errors.append(f"Raw item '{item}' cap exceeded: used {consumed:.2f}, cap {cap}")

    # Check machine caps
    machine_caps = inp.get("limits", {}).get("max_machines", {})
    machine_counts = out.get("per_machine_counts", {})
    for m_name, used in machine_counts.items():
        cap = machine_caps.get(m_name)
        if cap is not None and used > cap + TOLERANCE:
            errors.append(f"Machine '{m_name}' cap exceeded: used {used:.2f}, cap {cap}")

    return errors


def main():
    # CLI usage: verify_factory.py <input.json> <output.json>
    if len(sys.argv) != 3:
        print("Usage: python verify_factory.py <input.json> <output.json>", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Robust JSON loading (handles UTF-8 BOM and UTF-16)
    def load_json_robust(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='utf-16') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to read {filepath} with utf-8-sig or utf-16: {e}", file=sys.stderr)
                return None
        except Exception as e:
            print(f"Failed to read {filepath}: {e}", file=sys.stderr)
            return None

    inp = load_json_robust(input_file)
    out = load_json_robust(output_file)

    if inp is None or out is None:
        print("Error: Could not load JSON files. Check for encoding errors or empty files.", file=sys.stderr)
        sys.exit(1)

    print(f"Verifying '{output_file}' against '{input_file}'...")
    errors = validate_solution(inp, out)

    if not errors:
        print("\n✅ Solution is VALID")
    else:
        print("\n❌ Solution is INVALID:")
        for err in errors:
            print(f"  - {err}")

if __name__ == "__main__":
    main()
