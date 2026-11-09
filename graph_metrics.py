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


# Single source of truth for node categories (used by the renderer too).
BASE_HEAT_THRESHOLD = 0.3   # heat at or above this -> base topic
NICHE_HEAT_MAX = 0.05       # heat at or below this ...
NICHE_OUT_THRESHOLD = 100   # ... with at least this many outgoing links -> niche topic


def categorize_nodes(heat_scores, out_degree, heat_threshold=BASE_HEAT_THRESHOLD,
                     out_threshold=NICHE_OUT_THRESHOLD, niche_heat_max=NICHE_HEAT_MAX):
    base_topics = []
    niche_topics = []

    for node in heat_scores:
        heat = heat_scores[node]
        out = out_degree.get(node, 0)

        # Base Topics: Highly linked-to by other articles
        if heat >= heat_threshold:
            base_topics.append((node, heat))

        # Niche Topics: Point to many articles, but rarely linked to themselves
        elif heat <= niche_heat_max and out >= out_threshold:
            niche_topics.append((node, out))

    return base_topics, niche_topics