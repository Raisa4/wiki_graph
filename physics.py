import logging
import random
from collections import Counter
import math

logger = logging.getLogger(__name__)


def initialize_positions(nodes, width=800, height=600):
    # Assign random starting (x, y) coordinates for every node
    positions = {}
    for node in nodes:
        positions[node] = {
            'x': random.uniform(0, width),
            'y': random.uniform(0, height)
        }
    return positions


def run_physics_simulation(positions, edges, iterations=50, width=800, height=600):
    # k is the optimal distance we want between nodes
    k = math.sqrt((width * height) / len(positions))

    # Temperature controls how much nodes can move. It cools down (decreases) over time.
    temperature = width / 10

    # Each node's spring pull is divided by sqrt(its degree). Without this, in a dense
    # graph a node with ~150 edges is pulled by ~150 springs at once and the whole
    # layout collapses into a small blob.
    degree = Counter()
    for source, target in edges:
        if source in positions and target in positions:
            degree[source] += 1
            degree[target] += 1

    logger.info("Running physics simulation for %d iterations...", iterations)

    for i in range(iterations):
        if i % 10 == 0:
            logger.debug("Stabilizing... iteration %d/%d", i, iterations)

        # Store the intended movement for each node before actually moving them
        displacements = {node: {'x': 0.0, 'y': 0.0} for node in positions}

        # 1. REPULSION LOGIC: Push all nodes apart (like magnets)
        for node1 in positions:
            for node2 in positions:
                if node1 == node2:
                    continue

                dx = positions[node1]['x'] - positions[node2]['x']
                dy = positions[node1]['y'] - positions[node2]['y']
                dist = math.hypot(dx, dy)

                # Repel at every distance. (A cutoff saves no work here, since the
                # distance is already computed, and it let dense graphs collapse.)
                if dist > 0:
                    force = (k * k) / dist
                    displacements[node1]['x'] += (dx / dist) * force
                    displacements[node1]['y'] += (dy / dist) * force

        # 2. ATTRACTION LOGIC: Pull connected nodes together (like springs)
        for source, target in edges:
            if source in positions and target in positions:
                dx = positions[source]['x'] - positions[target]['x']
                dy = positions[source]['y'] - positions[target]['y']
                dist = math.hypot(dx, dy)

                if dist > 0:
                    force = (dist * dist) / k
                    source_force = force / math.sqrt(degree[source])
                    target_force = force / math.sqrt(degree[target])

                    displacements[source]['x'] -= (dx / dist) * source_force
                    displacements[source]['y'] -= (dy / dist) * source_force

                    displacements[target]['x'] += (dx / dist) * target_force
                    displacements[target]['y'] += (dy / dist) * target_force

        # 3. APPLY MOVEMENT: Move nodes, but cap the speed based on 'temperature'
        for node in positions:
            dx = displacements[node]['x']
            dy = displacements[node]['y']
            dist = math.hypot(dx, dy)

            if dist > 0:
                # Cap the length of the whole displacement vector by the temperature
                # (as in Fruchterman-Reingold), keeping its direction unchanged.
                step = min(dist, temperature)
                move_x = (dx / dist) * step
                move_y = (dy / dist) * step

                # Apply movement and keep nodes within the screen boundaries
                positions[node]['x'] = max(0, min(width, positions[node]['x'] + move_x))
                positions[node]['y'] = max(0, min(height, positions[node]['y'] + move_y))

        # Cool down the temperature so the graph slowly settles into place
        temperature *= 0.9

    logger.info("Physics simulation complete.")
    return positions