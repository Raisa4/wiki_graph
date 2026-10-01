def calculate_degrees(adjacency_list):
    # Create dictionaries with every node starting at 0
    in_degree = {node: 0 for node in adjacency_list}
    out_degree = {node: 0 for node in adjacency_list}

    for source, targets in adjacency_list.items():
        # Out-Degree is just the length of the targets list
        out_degree[source] = len(targets)

        # For In-Degree, we add 1 to every target node found in this list
        for target in targets:
            if target in in_degree:
                in_degree[target] += 1
            else:
                in_degree[target] = 1

    return in_degree, out_degree


def calculate_heat_scores(in_degree):
    if not in_degree:
        return {}

    max_in = max(in_degree.values())
    min_in = min(in_degree.values())

    heat_scores = {}
    for node, degree in in_degree.items():
        # Prevent division by zero if all nodes have the exact same score
        if max_in == min_in:
            heat_scores[node] = 0.0
        else:
            heat_scores[node] = (degree - min_in) / (max_in - min_in)

    return heat_scores


def categorize_nodes(heat_scores, out_degree, heat_threshold=0.5, out_threshold=50):
    base_topics = []
    niche_topics = []

    for node in heat_scores:
        heat = heat_scores[node]
        out = out_degree.get(node, 0)

        # Base Topics: Highly linked-to by other articles
        if heat >= heat_threshold:
            base_topics.append((node, heat))

        # Niche Topics: Point to many articles, but rarely linked to themselves
        elif heat <= 0.05 and out >= out_threshold:
            niche_topics.append((node, out))

    return base_topics, niche_topics