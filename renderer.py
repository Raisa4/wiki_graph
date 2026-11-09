import math

import pygame

from graph_metrics import categorize_nodes

BACKGROUND = (14, 17, 23)
MARGIN = 50

# Edges are split into layers and added together, so areas where many links
# overlap glow brighter instead of all edges merging into one flat gray mass.
EDGE_LAYERS = 24
EDGE_STEP = (5, 7, 11)  # brightness each overlapping edge adds

BASE_COLOR = (240, 96, 72)      # Base topics: many articles link to them
NICHE_COLOR = (80, 160, 245)    # Niche topics: rarely linked to, link out a lot
DEFAULT_COLOR = (150, 160, 178)
OUTLINE = (8, 10, 14)
TEXT = (230, 233, 240)
MUTED_TEXT = (140, 148, 162)

LABEL_COUNT = 40  # try to label this many of the hottest nodes (overlapping labels are skipped)


def fit_to_view(positions, width, height, margin=MARGIN):
    """Scale and center the layout so it fills the window, keeping its aspect ratio."""
    xs = [p['x'] for p in positions.values()]
    ys = [p['y'] for p in positions.values()]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-9)
    span_y = max(max_y - min_y, 1e-9)
    scale = min((width - 2 * margin) / span_x, (height - 2 * margin) / span_y)
    offset_x = (width - span_x * scale) / 2
    offset_y = (height - span_y * scale) / 2
    return {
        node: (offset_x + (p['x'] - min_x) * scale, offset_y + (p['y'] - min_y) * scale)
        for node, p in positions.items()
    }


def short_title(title):
    # "ISBN (identifier)" -> "ISBN": citation templates link these from almost every article.
    return title.removesuffix(" (identifier)")


def node_radius(heat):
    # sqrt so area (not radius) grows with heat
    return 2 + 9 * math.sqrt(heat)


def render_edges(points, edges, size):
    accumulated = pygame.Surface(size)
    accumulated.fill((0, 0, 0))
    layer = pygame.Surface(size)
    drawable = [(points[s], points[t]) for s, t in edges if s in points and t in points]

    for i in range(EDGE_LAYERS):
        layer.fill((0, 0, 0))
        for start, end in drawable[i::EDGE_LAYERS]:
            pygame.draw.aaline(layer, EDGE_STEP, start, end)
        accumulated.blit(layer, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return accumulated


def draw_label(surface, font, text, center_x, top_y, placed):
    """Draw a label centered under a node unless it would overlap one already placed."""
    image = font.render(text, True, TEXT)
    rect = image.get_rect(midtop=(center_x, top_y))
    rect.clamp_ip(surface.get_rect().inflate(-8, -8))
    if any(rect.inflate(6, 2).colliderect(other) for other in placed):
        return
    shadow = font.render(text, True, OUTLINE)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        surface.blit(shadow, rect.move(dx, dy))
    surface.blit(image, rect)
    placed.append(rect)


def draw_legend(surface, font, colors_shown):
    entries = [(color, label) for color, label in (
        (BASE_COLOR, "Base topic: many articles link here"),
        (NICHE_COLOR, "Niche topic: rarely linked, links out a lot"),
        (DEFAULT_COLOR, "Other article (size = how often it is linked)"),
    ) if color in colors_shown]
    x, y = 16, surface.get_height() - 10 - 20 * len(entries)
    for color, label in entries:
        pygame.draw.circle(surface, color, (x + 5, y + 7), 5)
        surface.blit(font.render(label, True, MUTED_TEXT), (x + 18, y))
        y += 20


def render_scene(points, edges, heat, styles, width, height, fonts):
    """Everything that doesn't change between frames, drawn once."""
    scene = pygame.Surface((width, height))
    scene.fill(BACKGROUND)
    scene.blit(render_edges(points, edges, (width, height)), (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    # Coolest first, so the hottest nodes are drawn on top.
    for node in sorted(points, key=lambda n: heat[n]):
        x, y = points[node]
        r = node_radius(heat[node])
        pygame.draw.circle(scene, OUTLINE, (x, y), r + 1.5)
        pygame.draw.circle(scene, styles.get(node, DEFAULT_COLOR), (x, y), r)

    placed = []
    for node in sorted(points, key=lambda n: heat[n], reverse=True)[:LABEL_COUNT]:
        x, y = points[node]
        draw_label(scene, fonts['label'], short_title(node), x, y + node_radius(heat[node]) + 3, placed)

    title = fonts['title'].render("Wikipedia Knowledge Graph", True, TEXT)
    scene.blit(title, (16, 14))
    subtitle = f"{len(points)} most-linked articles, {len(edges):,} links between them"
    scene.blit(fonts['small'].render(subtitle, True, MUTED_TEXT), (16, 40))
    draw_legend(scene, fonts['small'], {styles.get(node, DEFAULT_COLOR) for node in points})
    return scene


def draw_tooltip(surface, font, lines, mouse):
    images = [font.render(line, True, TEXT if i == 0 else MUTED_TEXT) for i, line in enumerate(lines)]
    box = pygame.Rect(0, 0, max(i.get_width() for i in images) + 16, sum(i.get_height() for i in images) + 12)
    box.topleft = (mouse[0] + 16, mouse[1] + 12)
    box.clamp_ip(surface.get_rect())  # keep it on screen near the right/bottom edges
    pygame.draw.rect(surface, (0, 0, 0), box, border_radius=4)
    pygame.draw.rect(surface, (60, 66, 80), box, width=1, border_radius=4)
    y = box.y + 6
    for image in images:
        surface.blit(image, (box.x + 8, y))
        y += image.get_height()


def draw_graph(positions, edges, heat_scores, out_degree, width=800, height=600, screenshot=None):
    """Open an interactive window. If `screenshot` is a path, save the first frame there and exit."""
    pygame.init()
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Wikipedia Knowledge Graph")
    fonts = {
        'title': pygame.font.SysFont(None, 30),
        'label': pygame.font.SysFont(None, 19),
        'small': pygame.font.SysFont(None, 20),
    }

    # Categorize once, up front, using the shared thresholds in graph_metrics.
    heat = {node: heat_scores.get(node, 0) for node in positions}
    base_topics, niche_topics = categorize_nodes(heat, out_degree)
    styles = {node: BASE_COLOR for node, _ in base_topics}
    styles.update({node: NICHE_COLOR for node, _ in niche_topics})

    points = fit_to_view(positions, width, height)
    scene = render_scene(points, edges, heat, styles, width, height, fonts)

    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        screen.blit(scene, (0, 0))

        # Hover: the closest node under the cursor, with a little slack for tiny nodes.
        mouse = pygame.mouse.get_pos()
        hovered, best = None, None
        for node, (x, y) in points.items():
            d = math.hypot(mouse[0] - x, mouse[1] - y)
            if d < node_radius(heat[node]) + 4 and (best is None or d < best):
                hovered, best = node, d

        if hovered:
            x, y = points[hovered]
            pygame.draw.circle(screen, TEXT, (x, y), node_radius(heat[hovered]) + 3, width=2)
            draw_tooltip(screen, fonts['small'], [
                hovered,
                f"heat {heat[hovered]:.2f}  ·  {out_degree.get(hovered, 0)} outgoing links",
            ], mouse)

        pygame.display.flip()
        if screenshot:
            pygame.image.save(screen, screenshot)
            running = False
        clock.tick(60)  # cap at 60 FPS instead of spinning at 100% CPU

    pygame.quit()
