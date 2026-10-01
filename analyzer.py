from database import get_connection
from graph_metrics import calculate_degrees, calculate_heat_scores
from physics import initialize_positions, run_physics_simulation
from renderer import draw_graph


def build_adjacency_list():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT source_title, target_title FROM edges")
    rows = cursor.fetchall()

    adjacency_list = {}
    all_edges = []

    for source, target in rows:
        all_edges.append((source, target))
        if source not in adjacency_list:
            adjacency_list[source] = []
        adjacency_list[source].append(target)
        if target not in adjacency_list:
            adjacency_list[target] = []

    return adjacency_list, all_edges


if __name__ == "__main__":
    print("Loading graph data...")
    graph, all_edges = build_adjacency_list()

    print("Calculating metrics...")
    in_degree, out_degree = calculate_degrees(graph)
    heat_scores = calculate_heat_scores(in_degree)

    sorted_nodes = sorted(heat_scores.items(), key=lambda item: item[1], reverse=True)
    top_nodes = [node for node, score in sorted_nodes[:300]]
    print(f"Extracted the top {len(top_nodes)} nodes for visualization.")

    filtered_edges = []
    for source, target in all_edges:
        if source in top_nodes and target in top_nodes:
            filtered_edges.append((source, target))

    positions = initialize_positions(top_nodes, width=800, height=600)

    # Run physics invisibly in the background
    final_positions = run_physics_simulation(
        positions=positions,
        edges=filtered_edges,
        iterations=50,
        width=800,
        height=600
    )

    print("Rendering graph...")
    # Hand the calculated data over to Pygame
    draw_graph(
        positions=final_positions,
        edges=filtered_edges,
        heat_scores=heat_scores,
        out_degree=out_degree,
        width=800,
        height=600
    )