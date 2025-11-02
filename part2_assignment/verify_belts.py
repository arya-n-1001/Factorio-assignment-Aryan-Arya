import sys
import json
import math
from collections import defaultdict

TOLERANCE = 1e-9

def load_json_robust(filepath):
    # Try to read a JSON file, handling cases of weird BOM/encoding.
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

def validate_solution(inp, out):
    # Validates the solver output against the input belts spec.
    # Returns a list of string error messages if invalid.
    errors = []

    if out.get("status") != "ok":
        errors.append(f"Output status is not 'ok': {out.get('status')}")
        return errors

    flows = out.get("flows", [])
    flow_map = {}  # (from, to) → flow

    # Track net flow on each node
    net_flow = defaultdict(float)

    # --------------------------------------------------------------------
    # 1. Check edge bounds (lo ≤ flow ≤ hi)
    # --------------------------------------------------------------------
    for edge in inp.get("edges", []):
        u, v = edge["from"], edge["to"]

        # Lookup flow on edge
        f = 0.0
        for flow_obj in flows:
            if flow_obj.get("from") == u and flow_obj.get("to") == v:
                f = flow_obj.get("flow", 0.0)
                break

        flow_map[(u, v)] = f
        net_flow[u] -= f   # Outgoing flow subtracts
        net_flow[v] += f   # Incoming flow adds

        lo = edge.get("lo", 0.0)
        hi = edge.get("hi", float('inf'))

        if f < lo - TOLERANCE:
            errors.append(f"Edge ({u} -> {v}) violates lower bound: flow {f:.2f}, min {lo}")
        if f > hi + TOLERANCE:
            errors.append(f"Edge ({u} -> {v}) violates upper bound: flow {f:.2f}, max {hi}")

    # --------------------------------------------------------------------
    # 2. Check node capacity constraints (sum of inflow ≤ cap)
    # --------------------------------------------------------------------
    node_caps = inp.get("node_caps", {})
    for node, cap in node_caps.items():
        total_inflow = 0.0
        for (u, v), f in flow_map.items():
            if v == node:  # Only count incoming flow
                total_inflow += f

        if total_inflow > cap + TOLERANCE:
            errors.append(f"Node '{node}' cap exceeded: inflow {total_inflow:.2f}, cap {cap}")

    # --------------------------------------------------------------------
    # 3. Validate source/sink flow conservation
    # --------------------------------------------------------------------
    sources = inp.get("sources", {})
    sink = inp.get("sink")
    total_supply = sum(sources.values())

    for node, supply in sources.items():
        if not math.isclose(net_flow[node], -supply, abs_tol=TOLERANCE):
            errors.append(f"Source '{node}' mismatch: net flow {net_flow[node]:.2f}, expected {-supply}")

    if not math.isclose(net_flow[sink], total_supply, abs_tol=TOLERANCE):
        errors.append(f"Sink '{sink}' mismatch: net flow {net_flow[sink]:.2f}, expected {total_supply}")

    return errors  # Empty list means valid

def main():
    # CLI wrapper: verify_belts.py <input.json> <output.json>
    if len(sys.argv) != 3:
        print("Usage: python verify_belts.py <input.json> <output.json>", file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    inp = load_json_robust(input_file)
    out = load_json_robust(output_file)

    if inp is None or out is None:
        print("Error: Could not load JSON files.", file=sys.stderr)
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
