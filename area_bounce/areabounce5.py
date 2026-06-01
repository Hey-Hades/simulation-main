import math
import random
import pygame
from pygame.math import Vector2

# =====================================================
# INIT
# =====================================================
pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 450, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Blood Moon Gravity Bounce")
clock = pygame.time.Clock()

CENTER = Vector2(WIDTH // 2, HEIGHT // 2)

# =====================================================
# SOUND
# =====================================================
try:
    bounce_sound = pygame.mixer.Sound("../sounds/sound.mp3")
except Exception:
    print("Warning: 'sounds/sound.mp3' not found. Running without sound.")
    bounce_sound = None

last_sound_time = 0

# =====================================================
# COLORS (Blood Moon Aesthetic)
# =====================================================
BG = (12, 4, 4)               # Deep abyss red
MAIN_TEXT = (255, 220, 220)   # Pale rose 
SUB_TEXT = (150, 50, 50)      # Dim maroon 

# CHANGED: Was (255, 50, 50) crimson. Now a glowing gold!
HIGHLIGHT = (255, 180, 50)    # Glowing Ember Gold

STRIPE_COLORS = [
    (90, 40, 25, 255),      # Smoldering ember
    (139, 0, 0, 255),      # Dark Red
    (220, 20, 60, 255),    # Crimson
    (255, 69, 0, 255),     # Red-Orange
    (255, 140, 100, 255),  # Pale Ember
]

# =====================================================
# FONTS
# =====================================================
hook_font = pygame.font.SysFont("arial", 25, bold=True)
counter_font = pygame.font.SysFont(None, 40)
watermark_font = pygame.font.SysFont('arial', 26)

# =====================================================
# ARENA & PAINT COVERAGE
# =====================================================
CIRCLE_RADIUS = 210
CIRCLE_THICKNESS = 4
CELL_SIZE = 2
FILL_TARGET = 1.0
STROKE_MIN_DISTANCE = 2

paint_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
painted_cells = set()
fillable_cells = []

for gy in range(0, HEIGHT, CELL_SIZE):
    for gx in range(0, WIDTH, CELL_SIZE):
        cell_center = Vector2(gx + CELL_SIZE / 2, gy + CELL_SIZE / 2)
        if cell_center.distance_to(CENTER) <= CIRCLE_RADIUS - CIRCLE_THICKNESS:
            fillable_cells.append((gx // CELL_SIZE, gy // CELL_SIZE))

total_fillable_cells = len(fillable_cells)
coverage = 0.0

# =====================================================
# BALL & PHYSICS PARAMS
# =====================================================
BALL_RADIUS = 24.0        
PAINT_BLEED = 3.0
GRAVITY = 1500            
MAX_SPEED = 2200          
BOUNCE_BOOST = 1.01       

# Initial Drop Sequence
ball_pos = Vector2(CENTER.x + 40, CENTER.y - CIRCLE_RADIUS * 0.6)
ball_vel = Vector2(0, 0)

game_state = "PLAYING"
collision_count = 0
particles = []
start_time = pygame.time.get_ticks()
last_stamp_pos = None


def color_from_hue(hue):
    color = pygame.Color(0)
    restricted_hue = 350 + (hue % 30)
    color.hsla = (restricted_hue % 360, 95, 50, 100)
    return color


def stripe_color_for_distance(distance, stripe_width):
    stripe_index = int(distance // stripe_width) % len(STRIPE_COLORS)
    return STRIPE_COLORS[stripe_index]


def make_ball_texture(radius):
    size = int(radius * 2)
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
    surface.blit(ball_texture, (int(pos.x - radius), int(pos.y - radius)))


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
    diameter = int(radius * 2)

    pygame.draw.line(mask, (255, 255, 255, 255), local_start, local_end, diameter)
    pygame.draw.circle(mask, (255, 255, 255, 255), local_start, int(radius))
    pygame.draw.circle(mask, (255, 255, 255, 255), local_end, int(radius))

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
    dt = min(clock.tick(60) / 1000, 0.05)
    current_time = pygame.time.get_ticks()
    elapsed_time = current_time - start_time

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    hue = (elapsed_time * 0.09 + collision_count * 18) % 360
    
    if game_state == "PLAYING":
        ball_vel.y += GRAVITY * dt
        next_pos = ball_pos + ball_vel * dt

        direction = next_pos - CENTER
        distance = direction.length()
        inner_limit = CIRCLE_RADIUS - CIRCLE_THICKNESS - BALL_RADIUS

        if distance >= inner_limit:
            collision_count += 1
            normal = direction.normalize() if distance > 0 else Vector2(0, -1)
            impact_pos = CENTER + normal * inner_limit

            if last_stamp_pos is not None:
                paint_stroke(last_stamp_pos, impact_pos, BALL_RADIUS + PAINT_BLEED)
            last_stamp_pos = Vector2(impact_pos)

            ball_vel = ball_vel.reflect(normal) * BOUNCE_BOOST
            ball_vel = ball_vel.rotate(random.uniform(-4, 4))
            
            if ball_vel.length() > MAX_SPEED:
                ball_vel.scale_to_length(MAX_SPEED)

            if bounce_sound and current_time - last_sound_time > 35:
                impact_volume = min(1.0, 0.25 + ball_vel.length() / MAX_SPEED)
                bounce_sound.set_volume(impact_volume)
                bounce_sound.play()
                last_sound_time = current_time
            
            ball_pos = impact_pos
        else:
            if last_stamp_pos is None:
                paint_stroke(ball_pos, ball_pos, BALL_RADIUS + PAINT_BLEED)
                last_stamp_pos = Vector2(ball_pos)
            elif ball_pos.distance_to(last_stamp_pos) >= STROKE_MIN_DISTANCE:
                paint_stroke(last_stamp_pos, next_pos, BALL_RADIUS + PAINT_BLEED)
                last_stamp_pos = Vector2(next_pos)
            
            ball_pos = next_pos

        if coverage >= FILL_TARGET:
            game_state = "FILLED"
            spawn_burst()

    elif game_state == "FILLED":
        for p in particles:
            p["vel"] += Vector2(0, 650) * dt
            p["pos"] += p["vel"] * dt
            p["life"] -= dt
        particles = [p for p in particles if p["life"] > 0]


    # =====================================================
    # RENDERING
    # =====================================================
    screen.fill(BG)
    screen.blit(paint_surface, (0, 0))

    center_render = (int(CENTER.x), int(CENTER.y))
    draw_rainbow_ring(screen, center_render, CIRCLE_RADIUS, CIRCLE_THICKNESS, hue)

    if game_state == "PLAYING":
        draw_rainbow_ball(screen, Vector2(ball_pos.x, ball_pos.y), BALL_RADIUS)
        
        boundary_color = color_from_hue(hue)
        thickness = max(2, int(BALL_RADIUS * 0.12))
        pygame.draw.circle(
            screen, 
            boundary_color, 
            (int(ball_pos.x), int(ball_pos.y)), 
            int(BALL_RADIUS), 
            width=thickness
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

    # --- UI RENDERING ---
    hook_text = hook_font.render("THE LAST 25% IS THE HARDEST!!", True, MAIN_TEXT)
    hook_rect = hook_text.get_rect(center=(WIDTH // 2, 65))
    screen.blit(hook_text, hook_rect)

    percent_val = coverage * 100
    if percent_val >= 100:
        formatted_percent = f"100.0%"
    else:
        formatted_percent = f"{percent_val:4.1f}%".lstrip('0') 
        
    fill_text = counter_font.render(f"Filled: {formatted_percent}", True, HIGHLIGHT)
    fill_rect = fill_text.get_rect(
        center=(WIDTH // 2, HEIGHT // 2 + CIRCLE_RADIUS + 35)
    )
    screen.blit(fill_text, fill_rect)

    bounces_text = counter_font.render(f"Bounces: {collision_count}", True, MAIN_TEXT)
    bounces_rect = bounces_text.get_rect(
        center=(WIDTH // 2, fill_rect.bottom + 20)
    )
    screen.blit(bounces_text, bounces_rect)

    part1 = watermark_font.render("@ B o u n c e ", True, SUB_TEXT)
    part2 = watermark_font.render("C u l t", True, HIGHLIGHT)

    total_width = part1.get_width() + part2.get_width()
    start_x = (WIDTH // 2) - (total_width // 2)
    y_pos = bounces_rect.bottom + 15 

    screen.blit(part1, (start_x, y_pos))
    screen.blit(part2, (start_x + part1.get_width(), y_pos))

    pygame.display.flip()

pygame.quit()