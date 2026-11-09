from database import get_connection
from graph_metrics import calculate_degrees, calculate_heat_scores
from physics import initialize_positions, run_physics_simulation
from renderer import draw_graph


def build_adjacency_list(db_name='wiki_graph.db'):
    conn = get_connection(db_name)
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


def analyze(db_name='wiki_graph.db', top=300, iterations=50, width=800, height=600, screenshot=None):
    print("Loading graph data...")
    graph, all_edges = build_adjacency_list(db_name)
    if not graph:
        print(f"No edges found in {db_name}. Run a crawl first.")
        return

    print("Calculating metrics...")
    in_degree, out_degree = calculate_degrees(graph)
    heat_scores = calculate_heat_scores(in_degree)

    sorted_nodes = sorted(heat_scores.items(), key=lambda item: item[1], reverse=True)
    top_nodes = {node for node, score in sorted_nodes[:top]}  # set: O(1) membership checks
    print(f"Extracted the top {len(top_nodes)} nodes for visualization.")

    filtered_edges = []
    for source, target in all_edges:
        if source in top_nodes and target in top_nodes:
            filtered_edges.append((source, target))

    positions = initialize_positions(top_nodes, width=width, height=height)

    # Run physics invisibly in the background
    final_positions = run_physics_simulation(
        positions=positions,
        edges=filtered_edges,
        iterations=iterations,
        width=width,
        height=height
    )

    print("Rendering graph...")
    # Hand the calculated data over to Pygame
    draw_graph(
        positions=final_positions,
        edges=filtered_edges,
        heat_scores=heat_scores,
        out_degree=out_degree,
        width=width,
        height=height,
        screenshot=screenshot
    )
