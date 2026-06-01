import math
import random

import pygame
from pygame.math import Vector2

# =====================================================
# INIT
# =====================================================
pygame.init()

WIDTH, HEIGHT = 500, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Black Hole Paint Bounce")
clock = pygame.time.Clock()

CENTER = Vector2(WIDTH // 2, HEIGHT // 2)

# =====================================================
# COLORS & FONTS
# =====================================================
BLACK = (0, 0, 0)
WHITE = (245, 245, 255)

font_name = pygame.font.match_font('segoeui, helvetica, arial')
title_font = pygame.font.Font(font_name, 28) if font_name else pygame.font.SysFont(None, 32)
stats_font = pygame.font.Font(font_name, 22) if font_name else pygame.font.SysFont(None, 24)

# =====================================================
# ARENA, CANVAS & COVERAGE TRACKER
# =====================================================
CIRCLE_RADIUS = 210

canvas = pygame.Surface((WIDTH, HEIGHT))
canvas.fill(BLACK)
pygame.draw.circle(canvas, WHITE, CENTER, CIRCLE_RADIUS)

# Pixel-perfect grid resolution for hyper-accurate tracking
CELL_SIZE = 1
fillable_cells = []
painted_cells = set()

# Static -1.0 margin aligns the grid with the visual inner edge
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
BOUNCE_BOOST = 1.01       

# Initial Drop Sequence
ball_pos = Vector2(CENTER.x + 40, CENTER.y - CIRCLE_RADIUS * 0.6)
ball_vel = Vector2(0, 0) 

collision_count = 0
game_state = "PLAYING"

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
            
            # Static boundary check: Guarantees we never paint outside the arena
            if cell_pos.distance_to(CENTER) > CIRCLE_RADIUS - 1.0:
                continue

            if point_distance_to_segment(cell_pos, start_pos, end_pos) <= paint_radius:
                painted_cells.add((cx, cy))

    coverage = len(painted_cells) / total_fillable_cells

def draw_smooth_trail(surface, start, end, base_radius):
    paint_radius = base_radius + PAINT_BLEED
    
    dist = start.distance_to(end)
    if dist == 0:
        pygame.draw.circle(surface, BLACK, (int(start.x), int(start.y)), int(paint_radius))
        update_coverage(start, end, base_radius)
        return

    steps = int(dist) * 2 + 1 
    for i in range(steps + 1):
        interp_pos = start.lerp(end, i / steps)
        pygame.draw.circle(surface, BLACK, (int(interp_pos.x), int(interp_pos.y)), int(paint_radius))
    
    update_coverage(start, end, base_radius)

# =====================================================
# MAIN LOOP
# =====================================================
running = True

while running:
    dt = min(clock.tick(60) / 1000, 0.05) 

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

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

        # Extremely strict win condition requiring near-perfect coverage
        if coverage >= 0.99999999999999999999:
            coverage = 1.0
            game_state = "FILLED"

    # =====================================================
    # RENDERING
    # =====================================================
    screen.blit(canvas, (0, 0))

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

    title_text = title_font.render("Not stopping until the circle", True, WHITE)
    subtitle_text = title_font.render("is filled", True, WHITE)
    
    bounces_text = stats_font.render(f"Bounces: {collision_count}", True, WHITE)
    
    display_coverage = coverage if game_state == "FILLED" else min(coverage, 0.9999)
    coverage_text = stats_font.render(f"Filled: {display_coverage * 100:.1f}%", True, WHITE)
    
    for text_surface, pos in [
        (title_text, (WIDTH // 2, 70)),
        (subtitle_text, (WIDTH // 2, 105)),
        (bounces_text, (WIDTH // 2, HEIGHT - 100)),
        (coverage_text, (WIDTH // 2, HEIGHT - 70)),
    ]:
        shadow = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
        shadow.blit(text_surface, (0, 0))
        shadow.fill((0, 0, 0, 150), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(shadow, shadow.get_rect(center=(pos[0] + 2, pos[1] + 2)))
        screen.blit(text_surface, text_surface.get_rect(center=pos))

    pygame.display.flip()

pygame.quit()