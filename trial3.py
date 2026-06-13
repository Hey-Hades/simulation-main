import math
import random
from pathlib import Path

import pygame
from pygame.math import Vector2

# =====================================================
# INIT
# =====================================================
pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 430, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cotton Candy Cloud Bounce")
clock = pygame.time.Clock()

CENTER = Vector2(WIDTH // 2, HEIGHT // 2)

# =====================================================
# SOUND
# =====================================================
SOUND_SEQUENCE_DIR = Path("./sounds/sp_notes/")
SOUND_SEQUENCE_LOOP = True
SONG_CLIP_STEP_SECONDS = 0.3
SONG_END_SPEED_BOOST = 0.75
SOUND_EXTENSIONS = {".wav", ".mp3", ".ogg"}
SOUND_HIT_COOLDOWN_MS = 25

sound_paths = sorted(
    path
    for path in SOUND_SEQUENCE_DIR.iterdir()
    if path.is_file() and path.suffix.lower() in SOUND_EXTENSIONS
) if SOUND_SEQUENCE_DIR.exists() else []

bounce_sounds = []
for sound_path in sound_paths:
    try:
        bounce_sounds.append(pygame.mixer.Sound(str(sound_path)))
    except Exception as exc:
        print(f"Warning: could not load '{sound_path}': {exc}")

if not bounce_sounds:
    try:
        bounce_sounds = [pygame.mixer.Sound("sounds/sound.mp3")]
    except Exception:
        print("Warning: no collision sounds found. Running without sound.")

sound_cursor = 0.0
last_sound_time = None
SOUND_VOLUME_BOOST = 5

def play_progressive_sound(volume, current_time, fill_progress):
    global sound_cursor, last_sound_time

    if not bounce_sounds:
        return

    if last_sound_time is None:
        last_sound_time = current_time
    else:
        seconds_since_last_hit = max(0.0, (current_time - last_sound_time) / 1000)
        original_song_step = seconds_since_last_hit / SONG_CLIP_STEP_SECONDS
        late_speed_boost = 1.0 + (fill_progress ** 2) * SONG_END_SPEED_BOOST
        sound_cursor += max(1.0, original_song_step * late_speed_boost)
        last_sound_time = current_time

    if SOUND_SEQUENCE_LOOP:
        sound_cursor %= len(bounce_sounds)
    else:
        sound_cursor = min(sound_cursor, len(bounce_sounds) - 1)

    sound_index = int(sound_cursor) % len(bounce_sounds)
    if not SOUND_SEQUENCE_LOOP:
        sound_index = min(sound_index, len(bounce_sounds) - 1)

    sound = bounce_sounds[sound_index]
    sound.set_volume(min(1.0, volume * SOUND_VOLUME_BOOST))
    sound.play()

# =====================================================
# COLORS & PASTEL COTTON PALETTE
# =====================================================
BG = (16, 12, 28)  
WHITE = (255, 255, 255)
MAIN_TEXT = (245, 245, 255)
SUB_TEXT = (150, 150, 180)
HIGHLIGHT = (255, 180, 210)  

COTTON_PALETTE = [
    (245, 130, 180),  
    (190, 120, 225),  
    (130, 175, 240),  
    (135, 235, 210),  
    (240, 235, 150),  
    (250, 170, 135)   
]

# =====================================================
# FONTS (Loaded once to prevent lag)
# =====================================================
font_small_text = pygame.font.SysFont('arial', 22, bold=True)
font_large_text = pygame.font.SysFont('arial', 32, bold=True)
watermark_font = pygame.font.SysFont('arial', 26)
counter_font = pygame.font.SysFont(None, 40)

# =====================================================
# ARENA & BALL
# =====================================================
CIRCLE_RADIUS = 210
CIRCLE_THICKNESS = 4
BALL_RADIUS = 26  
PAINT_BLEED = 4
GRAVITY = 1500
MAX_SPEED = 2200
BOUNCE_BOOST = 1.025

ball_pos = Vector2(CENTER.x + 40, CENTER.y - CIRCLE_RADIUS * 0.6)
ball_vel = Vector2(0, 0)

# =====================================================
# PAINT COVERAGE
# =====================================================
paint_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
painted_cells = set()
CELL_SIZE = 2
FILL_TARGET = 1.0
STROKE_MIN_DISTANCE = 1.5  

fillable_cells = []
for gy in range(0, HEIGHT, CELL_SIZE):
    for gx in range(0, WIDTH, CELL_SIZE):
        cell_center = Vector2(gx + CELL_SIZE / 2, gy + CELL_SIZE / 2)
        if cell_center.distance_to(CENTER) <= CIRCLE_RADIUS - CIRCLE_THICKNESS:
            fillable_cells.append((gx // CELL_SIZE, gy // CELL_SIZE))

total_fillable_cells = len(fillable_cells)
coverage = 0.0

# =====================================================
# EFFECTS & PROCEDURAL CLOUD GRADIENT ENGINE
# =====================================================
game_state = "PLAYING"
collision_count = 0
particles = []
camera_shake = 0  # NEW: Added for cinematic explosion
start_time = pygame.time.get_ticks()
last_stamp_pos = None

def make_cotton_puff_texture(radius, base_color):
    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = radius, radius
    for y in range(size):
        for x in range(size):
            dist = math.hypot(x - cx, y - cy)
            if dist <= radius:
                falloff = (math.cos((dist / radius) * math.pi) + 1.0) * 0.5
                alpha = int(falloff * 11) 
                if alpha > 0:
                    surf.set_at((x, y), (base_color[0], base_color[1], base_color[2], alpha))
    return surf

cached_puffs = [make_cotton_puff_texture(BALL_RADIUS + PAINT_BLEED, c) for c in COTTON_PALETTE]

def get_current_palette_color(index_offset=0):
    progress = ((pygame.time.get_ticks() - start_time) * 0.0003 + collision_count * 0.12 + index_offset) % len(COTTON_PALETTE)
    idx1 = int(progress) % len(COTTON_PALETTE)
    idx2 = (idx1 + 1) % len(COTTON_PALETTE)
    mix = progress - int(progress)
    c1, c2 = COTTON_PALETTE[idx1], COTTON_PALETTE[idx2]
    r = int(c1[0] * (1 - mix) + c2[0] * mix)
    g = int(c1[1] * (1 - mix) + c2[1] * mix)
    b = int(c1[2] * (1 - mix) + c2[2] * mix)
    return (r, g, b)

def draw_rainbow_ring(surface, center, radius, thickness):
    segments = 120
    rect = pygame.Rect(0, 0, radius * 2, radius * 2)
    rect.center = center
    for i in range(segments):
        start = (i / segments) * math.tau
        end = ((i + 1.5) / segments) * math.tau
        color = get_current_palette_color(index_offset=i / segments * 2.0)
        pygame.draw.arc(surface, color, rect, start, end, thickness)

def draw_cotton_ball(surface, pos):
    color = get_current_palette_color()
    pygame.draw.circle(surface, (255, 255, 255), (int(pos.x), int(pos.y)), int(BALL_RADIUS * 0.85))
    pygame.draw.circle(surface, color, (int(pos.x), int(pos.y)), int(BALL_RADIUS), width=3)

def point_distance_to_segment(point, start, end):
    segment = end - start
    segment_length_sq = segment.length_squared()
    if segment_length_sq == 0: return point.distance_to(start)
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
            if point_distance_to_segment(cell_pos, start, end) > radius: continue
            if cell_pos.distance_to(CENTER) > arena_radius: continue
            painted_cells.add((cx, cy))
    coverage = len(painted_cells) / total_fillable_cells

def paint_stroke(start, end, radius):
    dist = start.distance_to(end)
    steps = max(1, int(dist / 3)) 
    current_color = get_current_palette_color()
    puff_brush = make_cotton_puff_texture(int(radius), current_color)
    brush_offset = Vector2(radius, radius)
    for i in range(steps + 1):
        t = i / steps
        stamp_pos = start.lerp(end, t)
        paint_surface.blit(puff_brush, (int(stamp_pos.x - brush_offset.x), int(stamp_pos.y - brush_offset.y)))
    update_coverage_for_stroke(start, end, radius * 0.85)

def spawn_burst():
    """NEW: Double cinematic burst (Ball + Ring) using Pastel Colors"""
    # 1. Burst from the ball
    for _ in range(500):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(200, 2500)
        vel = Vector2(math.cos(angle), math.sin(angle)) * speed
        src_color = random.choice(COTTON_PALETTE)
        p_color = pygame.Color(src_color[0], src_color[1], src_color[2])
        particles.append({
            "pos": Vector2(ball_pos),
            "vel": vel,
            "radius": random.uniform(4, 12), 
            "life": random.uniform(1.0, 3.5),
            "color": p_color,
        })
    # 2. Burst from the ring
    for _ in range(600):
        angle = random.uniform(0, math.tau)
        ring_pos = CENTER + Vector2(math.cos(angle), math.sin(angle)) * CIRCLE_RADIUS
        speed = random.uniform(100, 1500) 
        vel = Vector2(math.cos(angle), math.sin(angle)) * speed
        src_color = random.choice(COTTON_PALETTE)
        p_color = pygame.Color(src_color[0], src_color[1], src_color[2])
        particles.append({
            "pos": ring_pos,
            "vel": vel,
            "radius": random.uniform(4, 10), 
            "life": random.uniform(1.0, 3.5),
            "color": p_color,
        })

# =====================================================
# MAIN LOOP
# =====================================================
running = True

while running:
    dt = min(clock.tick(60) / 1000, 0.05)
    current_time = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

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

            if bounce_sounds and (last_sound_time is None or current_time - last_sound_time > SOUND_HIT_COOLDOWN_MS):
                impact_volume = min(1.0, 0.25 + ball_vel.length() / MAX_SPEED)
                play_progressive_sound(impact_volume, current_time, coverage)

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
            play_progressive_sound(1.0, current_time, 1.0)
            
            # --- NEW CINEMATIC FINISH TRIGGERS ---
            camera_shake = 60 
            if bounce_sounds:
                bounce_sounds[-1].set_volume(1.0)
                bounce_sounds[-1].play()
            spawn_burst()

    elif game_state == "FILLED":
        # NEW: Gravity drop on particles
        for p in particles:
            p["vel"] += Vector2(0, 800) * dt
            p["pos"] += p["vel"] * dt
            p["life"] -= dt
        particles = [p for p in particles if p["life"] > 0]

    # --- RENDER CAMERA SHAKE OFFSETS ---
    camera_shake *= 0.9
    offset_x = random.uniform(-camera_shake, camera_shake) if camera_shake > 0.5 else 0
    offset_y = random.uniform(-camera_shake, camera_shake) if camera_shake > 0.5 else 0

    screen.fill(BG)
    screen.blit(paint_surface, (offset_x, offset_y))

    center_render = (int(CENTER.x + offset_x), int(CENTER.y + offset_y))
    
    if game_state == "PLAYING":
        draw_rainbow_ring(screen, center_render, CIRCLE_RADIUS, CIRCLE_THICKNESS)
        draw_cotton_ball(screen, Vector2(ball_pos.x + offset_x, ball_pos.y + offset_y))
    else:
        # Render end game screen puff particles bursting with soft transparency
        for p in particles:
            life_ratio = min(1.0, p["life"])
            radius = int(p["radius"] * life_ratio)
            if radius > 0:
                p_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                alpha_val = int(life_ratio * 45)
                pygame.draw.circle(p_surf, (p["color"].r, p["color"].g, p["color"].b, alpha_val), (radius, radius), radius)
                screen.blit(p_surf, (int(p["pos"].x + offset_x - radius), int(p["pos"].y + offset_y - radius)))

    # =====================================================
    # UI OVERLAY & TEXT RENDERING
    # =====================================================
    if game_state == "PLAYING":
        # Top text asking for subscribers
        prefix_text = watermark_font.render("Will this video get me ", True, SUB_TEXT)
        
        if collision_count == 0:
            k_text = counter_font.render("? ", True, HIGHLIGHT) 
        else:
            k_text = counter_font.render(f"{collision_count} ", True, HIGHLIGHT) 
        
        suffix_word = "subscribers?" if collision_count != 1 else "subscriber?"
        suffix_text = watermark_font.render(suffix_word, True, SUB_TEXT)

        total_width_top = prefix_text.get_width() + k_text.get_width() + suffix_text.get_width()
        start_x_top = (WIDTH // 2) - (total_width_top // 2)
        
        # Bottom-alignment fixing the floating text
        baseline_y = 115 
        prefix_rect = prefix_text.get_rect(bottomleft=(start_x_top, baseline_y))
        k_rect = k_text.get_rect(bottomleft=(prefix_rect.right, baseline_y))
        suffix_rect = suffix_text.get_rect(bottomleft=(k_rect.right, baseline_y))

        screen.blit(prefix_text, prefix_rect)
        screen.blit(k_text, k_rect)
        screen.blit(suffix_text, suffix_rect)
        
    else:
        # End game text
        end_text = pygame.font.SysFont('arial', 38, bold=True).render("HIT SUBSCRIBE!!", True, HIGHLIGHT)
        end_rect = end_text.get_rect(center=(WIDTH // 2, 65))
        screen.blit(end_text, end_rect)

    # --- FILLED PERCENTAGE ---
    percent_val = coverage * 100
    if percent_val >= 100:
        formatted_percent = "100.0%"
    else:
        formatted_percent = f"{percent_val:4.1f}%".lstrip("0")

    fill_text = counter_font.render(f"Filled: {formatted_percent}", True, (255, 0, 50))
    fill_rect = fill_text.get_rect(
        center=(WIDTH // 2, CENTER.y + CIRCLE_RADIUS + 25) 
    )
    screen.blit(fill_text, fill_rect)

    # --- WATERMARK ---
    part1 = watermark_font.render("@ B o u n c e ", True, (255, 255, 255))
    part2 = watermark_font.render("C u l t", True, (255, 255, 0))
    
    total_width_bottom = part1.get_width() + part2.get_width()
    start_x_bottom = (WIDTH // 2) - (total_width_bottom // 2)
    y_pos_bottom = fill_rect.bottom + 25 
    
    screen.blit(part1, (start_x_bottom, y_pos_bottom))
    screen.blit(part2, (start_x_bottom + part1.get_width(), y_pos_bottom))

    pygame.display.flip()

pygame.quit()