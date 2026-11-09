import pygame
import math

from graph_metrics import categorize_nodes

BASE_STYLE = ((220, 50, 50), 8)       # Base topics: large, red
NICHE_STYLE = ((50, 120, 220), 4)     # Niche topics: small, blue
DEFAULT_STYLE = ((150, 150, 150), 3)  # Everything else: tiny, light gray


def draw_graph(positions, edges, heat_scores, out_degree, width=800, height=600):
    pygame.init()
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Wikipedia Knowledge Graph")

    # Load a default font for the hover text
    font = pygame.font.SysFont(None, 24)

    # Categorize once, up front, using the shared thresholds in graph_metrics.
    drawn_heat = {node: heat_scores.get(node, 0) for node in positions}
    base_topics, niche_topics = categorize_nodes(drawn_heat, out_degree)
    styles = {node: BASE_STYLE for node, _ in base_topics}
    styles.update({node: NICHE_STYLE for node, _ in niche_topics})

    clock = pygame.time.Clock()

    running = True
    while running:
        # 1. Clear the screen with a dark gray background
        screen.fill((30, 30, 30))

        # 2. Handle events (like closing the window)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        mouse_x, mouse_y = pygame.mouse.get_pos()
        hovered_node = None

        # 3. Draw Edges first (so they render underneath the nodes)
        for source, target in edges:
            if source in positions and target in positions:
                x1, y1 = positions[source]['x'], positions[source]['y']
                x2, y2 = positions[target]['x'], positions[target]['y']
                # Draw a thin, gray line
                pygame.draw.line(screen, (100, 100, 100), (x1, y1), (x2, y2), 1)

        # 4. Draw Nodes
        for node, pos in positions.items():
            x, y = int(pos['x']), int(pos['y'])

            color, radius = styles.get(node, DEFAULT_STYLE)
            pygame.draw.circle(screen, color, (x, y), radius)

            # Check if mouse is within 10 pixels of this node
            if math.hypot(mouse_x - x, mouse_y - y) < 10:
                hovered_node = node

        # 5. Draw Hover Text
        if hovered_node:
            text = font.render(hovered_node, True, (255, 255, 255))
            text_rect = text.get_rect(topleft=(mouse_x + 15, mouse_y + 10))

            # Draw a black background box for text readability
            pygame.draw.rect(screen, (0, 0, 0), text_rect.inflate(10, 6))
            screen.blit(text, text_rect)

        # Update the display
        pygame.display.flip()
        clock.tick(60)  # cap at 60 FPS instead of spinning at 100% CPU

    pygame.quit()