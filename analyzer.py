from database import get_connection
from graph_metrics import calculate_degrees, calculate_heat_scores, categorize_nodes


def build_adjacency_list():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT source_title, target_title FROM edges")
    rows = cursor.fetchall()

    adjacency_list = {}
    for source, target in rows:
        if source not in adjacency_list:
            adjacency_list[source] = []
        adjacency_list[source].append(target)
        if target not in adjacency_list:
            adjacency_list[target] = []

    return adjacency_list


if __name__ == "__main__":
    graph = build_adjacency_list()

    print("Calculating metrics...")
    in_degree, out_degree = calculate_degrees(graph)
    heat_scores = calculate_heat_scores(in_degree)

    # You can tweak these thresholds based on the size of your specific dataset
    base_topics, niche_topics = categorize_nodes(
        heat_scores,
        out_degree,
        heat_threshold=0.3,  # Heat score 0.3 to 1.0
        out_threshold=100  # At least 100 outgoing links
    )

    # Sort results for display
    base_topics.sort(key=lambda x: x[1], reverse=True)
    niche_topics.sort(key=lambda x: x[1], reverse=True)

    print("\n--- BASE TOPICS (High Heat) ---")
    for node, heat in base_topics[:10]:
        print(f"{node}: {heat:.3f}")

    print(f"\n--- NICHE TOPICS (Low Heat, High Out-Degree) ---")
    print(f"Found {len(niche_topics)} niche topics. Top 10:")
    for node, out in niche_topics[:10]:
        print(f"{node}: {out} outgoing links")