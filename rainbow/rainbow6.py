import math
import random

import pygame
from pygame.math import Vector2

# =====================================================
# INIT
# =====================================================
pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 90 * 4, 160 * 4
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sakura Paint Fill Bounce")
clock = pygame.time.Clock()

CENTER = Vector2(WIDTH // 2, HEIGHT // 2)

# =====================================================
# SOUND
# =====================================================
try:
    bounce_sound = pygame.mixer.Sound("sounds/sound.mp3")
except Exception:
    print("Warning: 'sounds/sound.mp3' not found. Running without sound.")
    bounce_sound = None

last_sound_time = 0

# =====================================================
# COLORS (Midnight Sakura Aesthetic)
# =====================================================
BG = (18, 18, 22)          # Deep muted charcoal
WHITE = (255, 220, 230)    # Soft petal pink (for text)

# =====================================================
# ARENA & BALL
# =====================================================
CIRCLE_RADIUS = 165
CIRCLE_THICKNESS = 4
BALL_RADIUS = 24
MAX_SPEED = 1800
ELASTICITY = 0.995
SPEED_BOOST = 1.012

ball_pos = Vector2(CENTER)
ball_vel = Vector2(random.uniform(-520, 520), random.uniform(-520, 520))
if ball_vel.length() < 250:
    ball_vel.scale_to_length(420)

# =====================================================
# PAINT COVERAGE
# =====================================================
paint_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
painted_cells = set()
CELL_SIZE = 4
FILL_TARGET = 1.0
STROKE_MIN_DISTANCE = 2

# Crimson, Magentas, and Soft Pinks
STRIPE_COLORS = [
    (120, 20, 60, 255),    # Deep Crimson
    (200, 50, 100, 255),   # Ruby Red
    (255, 105, 180, 255),  # Hot Pink
    (255, 183, 197, 255),  # Cherry Blossom Pink
    (255, 228, 225, 255),  # Misty Rose
]

fillable_cells = []
for gy in range(0, HEIGHT, CELL_SIZE):
    for gx in range(0, WIDTH, CELL_SIZE):
        cell_center = Vector2(gx + CELL_SIZE / 2, gy + CELL_SIZE / 2)
        if cell_center.distance_to(CENTER) <= CIRCLE_RADIUS - CIRCLE_THICKNESS:
            fillable_cells.append((gx // CELL_SIZE, gy // CELL_SIZE))

total_fillable_cells = len(fillable_cells)
coverage = 0.0

# =====================================================
# EFFECTS
# =====================================================
game_state = "PLAYING"
collision_count = 0
particles = []
start_time = pygame.time.get_ticks()
last_stamp_pos = None


def color_from_hue(hue):
    color = pygame.Color(0)
    # Restricted hue between 320 (Pink/Magenta) and 370/10 (Red/Rose)
    restricted_hue = 320 + (hue % 50)
    color.hsla = (restricted_hue % 360, 85, 65, 100)
    return color


def stripe_color_for_distance(distance, stripe_width):
    stripe_index = int(distance // stripe_width) % len(STRIPE_COLORS)
    return STRIPE_COLORS[stripe_index]


def make_ball_texture(radius):
    size = radius * 2
    texture = pygame.Surface((size, size), pygame.SRCALPHA)
    stripe_width = max(2, size // 7)
    origin = Vector2(radius, radius)

    for y in range(size):
        for x in range(size):
            distance = Vector2(x, y).distance_to(origin)
            texture.set_at((x, y), stripe_color_for_distance(distance, stripe_width))

    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (radius, radius), radius)
    texture.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return texture


ball_texture = make_ball_texture(BALL_RADIUS)


def draw_rainbow_ring(surface, center, radius, thickness, spin):
    segments = 96
    rect = pygame.Rect(0, 0, radius * 2, radius * 2)
    rect.center = center

    for i in range(segments):
        start = (i / segments) * math.tau
        end = ((i + 1.35) / segments) * math.tau
        color = color_from_hue(i * 360 / segments + spin)
        pygame.draw.arc(surface, color, rect, start, end, thickness)


def draw_rainbow_ball(surface, pos, radius):
    texture = ball_texture
    if texture.get_width() != radius * 2:
        texture = pygame.transform.smoothscale(ball_texture, (radius * 2, radius * 2))

    surface.blit(texture, (int(pos.x - radius), int(pos.y - radius)))


def point_distance_to_segment(point, start, end):
    segment = end - start
    segment_length_sq = segment.length_squared()
    if segment_length_sq == 0:
        return point.distance_to(start)

    amount = max(0.0, min(1.0, (point - start).dot(segment) / segment_length_sq))
    closest = start + segment * amount
    return point.distance_to(closest)


def update_coverage_for_stroke(start, end, radius):
    global coverage

    min_x = max(0, int((min(start.x, end.x) - radius) // CELL_SIZE))
    max_x = min(WIDTH // CELL_SIZE, int((max(start.x, end.x) + radius) // CELL_SIZE) + 1)
    min_y = max(0, int((min(start.y, end.y) - radius) // CELL_SIZE))
    max_y = min(HEIGHT // CELL_SIZE, int((max(start.y, end.y) + radius) // CELL_SIZE) + 1)

    arena_radius = CIRCLE_RADIUS - CIRCLE_THICKNESS

    for cy in range(min_y, max_y):
        for cx in range(min_x, max_x):
            cell_pos = Vector2(cx * CELL_SIZE + CELL_SIZE / 2, cy * CELL_SIZE + CELL_SIZE / 2)
            if point_distance_to_segment(cell_pos, start, end) > radius:
                continue
            if cell_pos.distance_to(CENTER) > arena_radius:
                continue
            painted_cells.add((cx, cy))

    coverage = len(painted_cells) / total_fillable_cells


def paint_stroke(start, end, radius):
    if start.distance_to(end) == 0:
        draw_rainbow_ball(paint_surface, end, radius)
        update_coverage_for_stroke(end, end, radius)
        return

    min_x = max(0, int(min(start.x, end.x) - radius - 2))
    min_y = max(0, int(min(start.y, end.y) - radius - 2))
    max_x = min(WIDTH, int(max(start.x, end.x) + radius + 2))
    max_y = min(HEIGHT, int(max(start.y, end.y) + radius + 2))
    width = max_x - min_x
    height = max_y - min_y

    if width <= 0 or height <= 0:
        return

    stripe_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    mask = pygame.Surface((width, height), pygame.SRCALPHA)

    local_start = (int(start.x - min_x), int(start.y - min_y))
    local_end = (int(end.x - min_x), int(end.y - min_y))
    diameter = radius * 2

    pygame.draw.line(mask, (255, 255, 255, 255), local_start, local_end, diameter)
    pygame.draw.circle(mask, (255, 255, 255, 255), local_start, radius)
    pygame.draw.circle(mask, (255, 255, 255, 255), local_end, radius)

    stripe_width = max(2, diameter // 7)
    for y in range(height):
        for x in range(width):
            point = Vector2(min_x + x, min_y + y)
            brush_distance = point_distance_to_segment(point, start, end)
            stripe_surface.set_at((x, y), stripe_color_for_distance(brush_distance, stripe_width))

    stripe_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    paint_surface.blit(stripe_surface, (min_x, min_y))
    update_coverage_for_stroke(start, end, radius)


def spawn_burst():
    for _ in range(650):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(180, 1800)
        vel = Vector2(math.cos(angle), math.sin(angle)) * speed
        particles.append({
            "pos": Vector2(ball_pos),
            "vel": vel,
            "radius": random.uniform(2, 7),
            "life": random.uniform(1.0, 3.0),
            "color": color_from_hue(random.uniform(0, 360)),
        })


# =====================================================
# MAIN LOOP
# =====================================================
running = True

while running:
    dt = min(clock.tick(60) / 1000, 0.1)
    current_time = pygame.time.get_ticks()
    elapsed_time = current_time - start_time

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    hue = (elapsed_time * 0.09 + collision_count * 18) % 360
    if game_state == "PLAYING":
        ball_pos += ball_vel * dt

        direction = ball_pos - CENTER
        distance = direction.length()
        inner_limit = CIRCLE_RADIUS - CIRCLE_THICKNESS - BALL_RADIUS

        if distance >= inner_limit:
            collision_count += 1
            normal = direction.normalize() if distance > 0 else Vector2(1, 0)
            ball_pos = CENTER + normal * inner_limit
            ball_vel = ball_vel.reflect(normal) * ELASTICITY
            ball_vel = ball_vel.rotate(random.uniform(-10, 10))
            ball_vel *= SPEED_BOOST
            
            if ball_vel.length() > MAX_SPEED:
                ball_vel.scale_to_length(MAX_SPEED)

            if bounce_sound and current_time - last_sound_time > 35:
                impact_volume = min(1.0, 0.25 + ball_vel.length() / MAX_SPEED)
                bounce_sound.set_volume(impact_volume)
                bounce_sound.play()
                last_sound_time = current_time

        if last_stamp_pos is None:
            paint_stroke(ball_pos, ball_pos, BALL_RADIUS)
            last_stamp_pos = Vector2(ball_pos)
        elif ball_pos.distance_to(last_stamp_pos) >= STROKE_MIN_DISTANCE:
            paint_stroke(last_stamp_pos, ball_pos, BALL_RADIUS)
            last_stamp_pos = Vector2(ball_pos)

        if coverage >= FILL_TARGET:
            game_state = "FILLED"
            spawn_burst()

    elif game_state == "FILLED":
        for p in particles:
            p["vel"] += Vector2(0, 650) * dt
            p["pos"] += p["vel"] * dt
            p["life"] -= dt
        particles = [p for p in particles if p["life"] > 0]

    # Rendering (Stationary / No Shake)
    screen.fill(BG)
    screen.blit(paint_surface, (0, 0))

    center_render = (int(CENTER.x), int(CENTER.y))
    draw_rainbow_ring(screen, center_render, CIRCLE_RADIUS, CIRCLE_THICKNESS, hue)

    if game_state == "PLAYING":
        draw_rainbow_ball(
            screen,
            Vector2(ball_pos.x, ball_pos.y),
            BALL_RADIUS,
        )
    else:
        for p in particles:
            radius = int(p["radius"] * min(1.0, p["life"]))
            if radius > 0:
                pygame.draw.circle(
                    screen,
                    p["color"],
                    (int(p["pos"].x), int(p["pos"].y)),
                    radius,
                )

    font = pygame.font.SysFont(None, 34)
    fill_text = font.render(f"Filled: {coverage * 100:05.1f}%", True, WHITE)
    hit_text = font.render(f"Bounces: {collision_count}", True, WHITE)
    screen.blit(fill_text, fill_text.get_rect(center=(WIDTH // 2, HEIGHT - 75)))
    screen.blit(hit_text, hit_text.get_rect(center=(WIDTH // 2, HEIGHT - 40)))

    pygame.display.flip()

pygame.quit()