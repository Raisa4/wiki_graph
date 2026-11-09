import itertools
import math
import random

import pytest

from physics import initialize_positions, run_physics_simulation

WIDTH, HEIGHT = 800, 600


def distance(positions, a, b):
    return math.hypot(positions[a]["x"] - positions[b]["x"],
                      positions[a]["y"] - positions[b]["y"])


@pytest.fixture
def two_clusters():
    # Two dense 6-node clusters joined by a single bridge edge.
    left = [f"L{i}" for i in range(6)]
    right = [f"R{i}" for i in range(6)]
    edges = list(itertools.combinations(left, 2)) + list(itertools.combinations(right, 2))
    edges.append(("L0", "R0"))
    return left + right, edges


def run_layout(nodes, edges, seed=42):
    random.seed(seed)
    positions = initialize_positions(nodes, width=WIDTH, height=HEIGHT)
    return run_physics_simulation(positions, edges, iterations=50, width=WIDTH, height=HEIGHT)


def test_initial_positions_are_inside_screen():
    random.seed(0)
    positions = initialize_positions(range(100), width=WIDTH, height=HEIGHT)
    for pos in positions.values():
        assert 0 <= pos["x"] <= WIDTH
        assert 0 <= pos["y"] <= HEIGHT


def test_nodes_stay_inside_screen(two_clusters):
    nodes, edges = two_clusters
    positions = run_layout(nodes, edges)

    for pos in positions.values():
        assert 0 <= pos["x"] <= WIDTH
        assert 0 <= pos["y"] <= HEIGHT


def test_connected_nodes_end_up_closer_than_unconnected(two_clusters):
    nodes, edges = two_clusters
    positions = run_layout(nodes, edges)

    edge_set = {frozenset(e) for e in edges}
    connected, unconnected = [], []
    for a, b in itertools.combinations(nodes, 2):
        bucket = connected if frozenset((a, b)) in edge_set else unconnected
        bucket.append(distance(positions, a, b))

    mean_connected = sum(connected) / len(connected)
    mean_unconnected = sum(unconnected) / len(unconnected)
    # Random placement gives a ratio near 1.0; the layout should pull clusters clearly
    # together (about 0.33 in practice), so require a wide margin, not just "<".
    assert mean_connected < 0.6 * mean_unconnected
