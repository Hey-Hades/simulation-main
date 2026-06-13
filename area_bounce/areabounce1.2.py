import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pygame")

import math
import random
import pygame
# ... the rest of your code ...import math

from pygame.math import Vector2

# =====================================================
# INIT
# =====================================================
pygame.init()

WIDTH, HEIGHT = 430, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Teal & Coral Paint Bounce")
clock = pygame.time.Clock()

CENTER = Vector2(WIDTH // 2, HEIGHT // 2)

# =====================================================
# COLORS & FONTS
# =====================================================
# Midnight Teal & Coral Palette
PAINT_COLOR = (18, 30, 49)    # Dark Teal (Void/Paint)
ARENA_COLOR = (255, 140, 105) # Soft Coral (Arena)

# Initialize your custom UI fonts here (outside the loop for performance)
watermark_font = pygame.font.SysFont('arial', 26)

# Added the new fonts needed for the hook text
font_small_text = pygame.font.SysFont("arial", 25, bold=True)
font_large_text = pygame.font.SysFont("arial", 35, bold=True)

# =====================================================
# ARENA, CANVAS & COVERAGE TRACKER
# =====================================================
CIRCLE_RADIUS = 210

canvas = pygame.Surface((WIDTH, HEIGHT))
canvas.fill(PAINT_COLOR)
pygame.draw.circle(canvas, ARENA_COLOR, CENTER, CIRCLE_RADIUS)

# Pixel-perfect grid resolution for hyper-accurate internal tracking
CELL_SIZE = 1
fillable_cells = []
painted_cells = set()

for gy in range(0, HEIGHT, CELL_SIZE):
    for gx in range(0, WIDTH, CELL_SIZE):
        cell_center = Vector2(gx + CELL_SIZE / 2, gy + CELL_SIZE / 2)
        if cell_center.distance_to(CENTER) <= CIRCLE_RADIUS - 1.0:
            fillable_cells.append((gx // CELL_SIZE, gy // CELL_SIZE))

total_fillable_cells = len(fillable_cells)
coverage = 0.0

# =====================================================
# BALL & PHYSICS PARAMS
# =====================================================
ball_radius = 7.0
MAX_BALL_RADIUS = 80.0    
GROWTH_RATE = 2.6         
PAINT_BLEED = 3.2        

GRAVITY = 1500            
MAX_SPEED = 2200          
BOUNCE_BOOST = 1.011       

# Initial Drop Sequence
ball_pos = Vector2(CENTER.x + 40, CENTER.y - CIRCLE_RADIUS * 0.6)
ball_vel = Vector2(0, 0) 

collision_count = 0
game_state = "PLAYING"

# --- NEW ANIMATION & EFFECT TRACKERS ---
text_y = 120.0
particles = []

# =====================================================
# HELPER FUNCTIONS
# =====================================================
def point_distance_to_segment(point, start, end):
    segment = end - start
    segment_length_sq = segment.length_squared()
    if segment_length_sq == 0:
        return point.distance_to(start)
    amount = max(0.0, min(1.0, (point - start).dot(segment) / segment_length_sq))
    closest = start + segment * amount
    return point.distance_to(closest)

def update_coverage(start_pos, end_pos, base_radius):
    global coverage
    paint_radius = base_radius + PAINT_BLEED
    
    min_x = max(0, int((min(start_pos.x, end_pos.x) - paint_radius) // CELL_SIZE))
    max_x = min(WIDTH // CELL_SIZE, int((max(start_pos.x, end_pos.x) + paint_radius) // CELL_SIZE) + 1)
    min_y = max(0, int((min(start_pos.y, end_pos.y) - paint_radius) // CELL_SIZE))
    max_y = min(HEIGHT // CELL_SIZE, int((max(start_pos.y, end_pos.y) + paint_radius) // CELL_SIZE) + 1)

    for cy in range(min_y, max_y):
        for cx in range(min_x, max_x):
            
            if (cx, cy) in painted_cells:
                continue
            
            cell_pos = Vector2(cx * CELL_SIZE + CELL_SIZE / 2, cy * CELL_SIZE + CELL_SIZE / 2)
            
            if cell_pos.distance_to(CENTER) > CIRCLE_RADIUS - 1.0:
                continue

            if point_distance_to_segment(cell_pos, start_pos, end_pos) <= paint_radius:
                painted_cells.add((cx, cy))

    coverage = len(painted_cells) / total_fillable_cells

def draw_smooth_trail(surface, start, end, base_radius):
    paint_radius = base_radius + PAINT_BLEED
    
    dist = start.distance_to(end)
    if dist == 0:
        pygame.draw.circle(surface, PAINT_COLOR, (int(start.x), int(start.y)), int(paint_radius))
        update_coverage(start, end, base_radius)
        return

    steps = int(dist) * 2 + 1 
    for i in range(steps + 1):
        interp_pos = start.lerp(end, i / steps)
        pygame.draw.circle(surface, PAINT_COLOR, (int(interp_pos.x), int(interp_pos.y)), int(paint_radius))
    
    update_coverage(start, end, base_radius)

def spawn_burst_particles(pos, radius, color):
    # Generates a dynamic ring explosion of particles inside the ball boundary
    for _ in range(120):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(150, 700)
        velocity = Vector2(math.cos(angle), math.sin(angle)) * speed
        # Spread particles naturally inside the final size of the ball
        spawn_offset = Vector2(math.cos(angle), math.sin(angle)) * random.uniform(0, radius)
        particles.append({
            "pos": Vector2(pos + spawn_offset),
            "vel": velocity,
            "radius": random.uniform(3, 8),
            "max_life": random.uniform(0.6, 1.4),
            "life": random.uniform(0.6, 1.4),
            "color": color
        })

# =====================================================
# MAIN LOOP
# =====================================================
running = True

while running:
    dt = min(clock.tick(60) / 1000, 0.05) 

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- STATE: PLAYING ---
    if game_state == "PLAYING":
        if ball_radius < MAX_BALL_RADIUS:
            ball_radius += GROWTH_RATE * dt
            if ball_radius > MAX_BALL_RADIUS:
                ball_radius = MAX_BALL_RADIUS

        ball_vel.y += GRAVITY * dt
        next_pos = ball_pos + ball_vel * dt

        direction = next_pos - CENTER
        distance = direction.length()
        inner_limit = CIRCLE_RADIUS - ball_radius

        if distance >= inner_limit:
            collision_count += 1
            normal = direction.normalize() if distance > 0 else Vector2(0, -1)
            impact_pos = CENTER + normal * inner_limit 
            
            draw_smooth_trail(canvas, ball_pos, impact_pos, ball_radius)
            
            ball_vel = ball_vel.reflect(normal) * BOUNCE_BOOST
            ball_vel = ball_vel.rotate(random.uniform(-4, 4))
            
            if ball_vel.length() > MAX_SPEED:
                ball_vel.scale_to_length(MAX_SPEED)
                
            ball_pos = impact_pos
        else:
            draw_smooth_trail(canvas, ball_pos, next_pos, ball_radius)
            ball_pos = next_pos

        # Trigger transition to burst state
        if coverage >= 0.9999999999:
            coverage = 1.0
            game_state = "FILLED"
            
            # Capture the precise current rainbow hue for the explosion
            hue = (pygame.time.get_ticks() * 0.08) % 360
            burst_color = pygame.Color(0)
            burst_color.hsla = (hue, 100, 50, 100)
            
            spawn_burst_particles(ball_pos, ball_radius, burst_color)

    # --- STATE: FILLED (BURST & TEXT ANIMATION) ---
    elif game_state == "FILLED":
        # Slide text directly to the screen's center line smoothly
        target_y = (HEIGHT // 2) - 15
        if text_y < target_y:
            text_y += 350 * dt  # Speed of descent
            if text_y > target_y:
                text_y = target_y

        # Handle particle physics (velocity, air resistance drag, and lifetime)
        for p in particles[:]:
            p["pos"] += p["vel"] * dt
            p["vel"] *= 0.94  # Simulates fluid friction/air drag
            p["life"] -= dt
            if p["life"] <= 0:
                particles.remove(p)

    # =====================================================
    # RENDERING
    # =====================================================
    screen.blit(canvas, (0, 0))
    
    # --- DYNAMIC HOOK TEXT ---
    prefix_text = font_small_text.render("Will this video get ", True, (255, 255, 255))
    
    if collision_count == 0:
        k_text = font_large_text.render("? ", True, (232, 192, 81)) 
    else:
        k_text = font_large_text.render(f"{collision_count}K", True, (232, 192, 81)) 
        
    suffix_text = font_small_text.render(" likes?", True, (255, 255, 255))

    total_width = prefix_text.get_width() + k_text.get_width() + suffix_text.get_width()
    start_x = (WIDTH - total_width) // 2
    
    # Text uses the dynamic text_y position variable
    screen.blit(prefix_text, (start_x, int(text_y)))
    screen.blit(k_text, (start_x + prefix_text.get_width(), int(text_y - 10))) 
    screen.blit(suffix_text, (start_x + prefix_text.get_width() + k_text.get_width(), int(text_y)))
    
    # --- BALL RENDERING ---
    if game_state == "PLAYING":
        hue = (pygame.time.get_ticks() * 0.08) % 360
        boundary_color = pygame.Color(0)
        boundary_color.hsla = (hue, 100, 50, 100)
        
        thickness = max(2, int(ball_radius * 0.12))
        pygame.draw.circle(
            screen, 
            boundary_color, 
            (int(ball_pos.x), int(ball_pos.y)), 
            int(ball_radius), 
            width=thickness
        )

    # --- PARTICLE RENDERING ---
    for p in particles:
        # Scale particle size down gradually as it approaches the end of its life cycle
        life_ratio = max(0.0, p["life"] / p["max_life"])
        current_radius = max(1, int(p["radius"] * life_ratio))
        pygame.draw.circle(screen, p["color"], (int(p["pos"].x), int(p["pos"].y)), current_radius)

    # --- YOUR CUSTOM UI ---

    # Bounce Cult Watermark (Centered below the arena - Untouched)
    part1 = watermark_font.render("@ B o u n c e ", True, (245, 245, 245))
    part2 = watermark_font.render("C u l t", True, (255, 210, 70))

    total_width = part1.get_width() + part2.get_width()
    start_x = (WIDTH // 2) - (total_width // 2)
    
    y_pos = HEIGHT // 2 + CIRCLE_RADIUS + 40

    screen.blit(part1, (start_x, y_pos))
    screen.blit(part2, (start_x + part1.get_width(), y_pos))

    pygame.display.flip()

pygame.quit()