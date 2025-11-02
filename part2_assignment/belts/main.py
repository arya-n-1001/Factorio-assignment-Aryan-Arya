#!/usr/bin/env python
# Solves the Factorio bounded belts problem (Part B).
# Reads JSON from stdin, runs max-flow with lower bounds, prints result as JSON.

import sys
import json
import networkx as nx
from collections import defaultdict
from typing import Dict, Any, List, Tuple

TOLERANCE = 1e-9


def solve_belts_flow(data: Dict[str, Any]) -> Dict[str, Any]:
    # Computes a feasible flow for a graph that has lower bounds and optional node caps.

    G = nx.DiGraph()
    super_source = "_SUPER_SOURCE_"
    super_sink = "_SUPER_SINK_"
    balance = defaultdict(float)
    original_edges: List[Tuple] = []

    # === 1. Node splitting: handle node caps and create internal "in/out" nodes ===
    all_nodes = set(data.get("sources", {}).keys()) | {data.get("sink")}
    for edge in data.get("edges", []):
        all_nodes.add(edge["from"])
        all_nodes.add(edge["to"])

    node_caps = data.get("node_caps", {})
    node_map = {}  # maps original node -> (in_node, out_node)

    for node in all_nodes:
        if node is None:
            continue

        is_source = node in data.get("sources", {})
        is_sink = node == data.get("sink")

        if node in node_caps and not is_source and not is_sink:
            # node needs splitting into in/out so we can apply throughput limits
            in_node, out_node = f"{node}_IN", f"{node}_OUT"
            node_map[node] = (in_node, out_node)
            G.add_edge(in_node, out_node, capacity=node_caps[node])
        else:
            # normal node, not capped
            node_map[node] = (node, node)
            if not G.has_node(node):
                G.add_node(node)

    # === 2. Apply lower bounds + supply/demand accounting ===
    total_supply = 0.0

    # source nodes push flow into the system
    for node, supply in data.get("sources", {}).items():
        balance[node_map[node][0]] += supply
        total_supply += supply

    # sink node takes in everything (demand = total supply)
    sink_node_name = data.get("sink")
    if sink_node_name:
        balance[node_map[sink_node_name][1]] -= total_supply

    # handle edges with lower/upper bounds
    for edge in data.get("edges", []):
        u_orig, v_orig = edge["from"], edge["to"]
        lo = edge.get("lo", 0.0)
        hi = edge.get("hi", float('inf'))

        u_mapped = node_map[u_orig][1]  # leaving original node
        v_mapped = node_map[v_orig][0]  # entering original node

        original_edges.append((u_orig, v_orig, u_mapped, v_mapped, lo))

        G.add_edge(u_mapped, v_mapped, capacity=(hi - lo))

        balance[u_mapped] -= lo
        balance[v_mapped] += lo

    # === 3. Hook up super source/sink to fix flow imbalances ===
    total_demand_imbalance = 0.0

    for node in list(G.nodes()):
        if node in (super_source, super_sink):
            continue

        bal = balance[node]

        if bal > TOLERANCE:
            G.add_edge(super_source, node, capacity=bal)
        elif bal < -TOLERANCE:
            G.add_edge(node, super_sink, capacity=-bal)
            total_demand_imbalance += -bal

    # === 4. Solve via max-flow ===
    try:
        flow_value, flow_dict = nx.maximum_flow(G, super_source, super_sink)
    except nx.NetworkXUnbounded:
        return {
            "status": "infeasible",
            "cut_reachable": ["Graph is unbounded"],
            "deficit": {}
        }

    # === 5. Check feasibility and return results ===
    if abs(flow_value - total_demand_imbalance) > TOLERANCE:
        cut_value, partition = nx.minimum_cut(G, super_source, super_sink)
        reachable, _ = partition

        # Show nodes on the reachable side
        cut_nodes = []
        for node in reachable:
            if node == super_source:
                continue
            orig_node = node.replace("_IN", "").replace("_OUT", "")
            if orig_node not in cut_nodes:
                cut_nodes.append(orig_node)

        return {
            "status": "infeasible",
            "cut_reachable": sorted(list(set(cut_nodes))),
            "deficit": {"demand_balance": total_demand_imbalance - flow_value}
        }

    # reconstruct final flow (including lower bounds)
    final_flows = []
    for (u_orig, v_orig, u_mapped, v_mapped, lo) in original_edges:
        flow_on_edge = flow_dict.get(u_mapped, {}).get(v_mapped, 0.0)
        total_edge_flow = flow_on_edge + lo

        if total_edge_flow > TOLERANCE:
            final_flows.append({
                "from": u_orig,
                "to": v_orig,
                "flow": total_edge_flow
            })

    return {
        "status": "ok",
        "max_flow_per_min": total_supply,
        "flows": final_flows
    }


def main():
    # main program logic: read JSON, run solver, print result
    try:
        input_data = json.load(sys.stdin)
        output_data = solve_belts_flow(input_data)
    except Exception as e:
        output_data = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        }

    print(json.dumps(output_data, indent=2))


if __name__ == "__main__":
    main()
