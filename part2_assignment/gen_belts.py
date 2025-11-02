import json
import sys
import random

def generate_belts_problem(seed=None):
    # Generates a random belts-flow LP problem.
    # Mostly tries to make something feasible (creates at least one valid path).

    if seed:
        random.seed(seed)

    num_nodes = random.randint(5, 10)
    num_edges = random.randint(num_nodes, num_nodes * 2)

    nodes = [f"n{i}" for i in range(num_nodes)]

    # Pick source and sink
    source_node = "n0"
    sink_node = f"n{num_nodes - 1}"

    intermediate_nodes = nodes[1:-1]

    edges = []

    # Force a path from source to sink so it's not impossible
    path = [source_node] + random.sample(intermediate_nodes,
                                         min(len(intermediate_nodes), 3)) + [sink_node]

    total_supply = random.randint(500, 1500)

    # Create edges along that forced path
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edges.append({
            "from": u,
            "to": v,
            "lo": random.randint(0, 50),
            "hi": random.randint(total_supply, total_supply + 500)
        })

    # Add some random edges for complexity
    for _ in range(num_edges - len(edges)):
        u, v = random.sample(nodes, 2)

        # Don't create flow out of the sink or into the source
        if u == sink_node or v == source_node:
            continue

        edges.append({
            "from": u,
            "to": v,
            "lo": 0,
            "hi": random.randint(100, 500)
        })

    # Randomly cap some nodes (but not source/sink)
    node_caps = {}
    for node in intermediate_nodes:
        # 50% chance to give node a cap
        if random.random() < 0.5:
            # cap should still allow the forced path to work
            node_caps[node] = random.randint(total_supply, total_supply + 500)

    problem = {
        "nodes": nodes,
        "edges": edges,
        "node_caps": node_caps,
        "sources": {
            source_node: total_supply
        },
        "sink": sink_node
    }

    return problem


def main():
    # Optional seed for reproducibility when debugging/testing
    seed = sys.argv[1] if len(sys.argv) > 1 else None
    problem = generate_belts_problem(seed)

    # Dump generated graph to stdout as JSON
    print(json.dumps(problem, indent=2))


if __name__ == "__main__":
    main()
