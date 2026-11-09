import pytest

from graph_metrics import calculate_degrees, calculate_heat_scores, categorize_nodes


@pytest.fixture
def four_node_graph():
    #   A -> B, A -> C, A -> D
    #   B -> C
    #   C -> D
    #   D          (no outgoing links)
    return {
        "A": ["B", "C", "D"],
        "B": ["C"],
        "C": ["D"],
        "D": [],
    }


def test_degrees_on_hand_computed_graph(four_node_graph):
    in_degree, out_degree = calculate_degrees(four_node_graph)

    assert in_degree == {"A": 0, "B": 1, "C": 2, "D": 2}
    assert out_degree == {"A": 3, "B": 1, "C": 1, "D": 0}


def test_heat_scores_are_normalised_in_degree(four_node_graph):
    in_degree, _ = calculate_degrees(four_node_graph)
    heat = calculate_heat_scores(in_degree)

    # min in-degree is 0 (A), max is 2 (C, D)
    assert heat == {"A": 0.0, "B": 0.5, "C": 1.0, "D": 1.0}


def test_heat_scores_when_every_node_has_same_degree():
    # A 3-cycle: every node has in-degree 1, so there is no range to normalise over.
    graph = {"A": ["B"], "B": ["C"], "C": ["A"]}
    in_degree, _ = calculate_degrees(graph)

    assert set(in_degree.values()) == {1}
    assert calculate_heat_scores(in_degree) == {"A": 0.0, "B": 0.0, "C": 0.0}


def test_heat_scores_empty():
    assert calculate_heat_scores({}) == {}


def test_categorize_nodes():
    heat = {"hub": 0.9, "niche": 0.0, "plain": 0.2, "quiet": 0.0}
    out = {"hub": 5, "niche": 150, "plain": 500, "quiet": 3}

    base, niche = categorize_nodes(heat, out)

    assert base == [("hub", 0.9)]
    assert niche == [("niche", 150)]
