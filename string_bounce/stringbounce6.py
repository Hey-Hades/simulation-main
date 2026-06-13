import pygame
import pygame.gfxdraw
import math
import random
from pathlib import Path
from pygame.math import Vector2

# =====================================================
# INIT
# =====================================================
pygame.init()
pygame.mixer.init(channels=8)

WIDTH, HEIGHT = 430, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Growing Ball (Shorts Hook Edition)")
clock = pygame.time.Clock()

CENTER = Vector2(WIDTH // 2, HEIGHT // 2)

# Define screen corners to calculate absolute max exit radius
SCREEN_CORNERS = [
    Vector2(0, 0),
    Vector2(WIDTH, 0),
    Vector2(0, HEIGHT),
    Vector2(WIDTH, HEIGHT)
]

# =====================================================
# PROGRESSIVE SOUND SEQUENCING SETUP
# =====================================================
SOUND_SEQUENCE_DIR = Path("../sounds/kp/")  
SOUND_SEQUENCE_LOOP = True

MELODY_ADVANCE_PER_BOUNCE = 1.0  
SONG_END_SPEED_BOOST = 0.50       
SOUND_EXTENSIONS = {".wav", ".mp3", ".ogg"}
SOUND_HIT_COOLDOWN_MS = 35        

# Load all sound clips from the directory dynamically
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

# Fallback
if not bounce_sounds:
    try:
        bounce_sounds = [pygame.mixer.Sound("../sounds/popshortt4.mp3")]
        print("Note sequence folder empty/missing. Using fallback pop sound.")
    except Exception:
        print("Warning: no collision sounds found. Running without sound.")

sound_cursor = 0.0
last_sound_time = None
SOUND_VOLUME_BOOST = 100


def play_progressive_sound(base_volume, current_time, progress_ratio):
    global sound_cursor, last_sound_time

    if not bounce_sounds:
        return

    if last_sound_time is None:
        last_sound_time = current_time
    else:
        late_speed_boost = 1.0 + (progress_ratio ** 3) * SONG_END_SPEED_BOOST
        sound_cursor += MELODY_ADVANCE_PER_BOUNCE * late_speed_boost
        last_sound_time = current_time

    if SOUND_SEQUENCE_LOOP:
        sound_cursor %= len(bounce_sounds)
    else:
        sound_cursor = min(sound_cursor, len(bounce_sounds) - 1)

    sound_index = int(sound_cursor) % len(bounce_sounds)
    sound = bounce_sounds[sound_index]
    
    sound.set_volume(min(10.0, base_volume * SOUND_VOLUME_BOOST))
    sound.play()

# =====================================================
# DYNAMIC COLOR PROFILE STATES (With Hot Magenta Hook)
# =====================================================
BASE_BG_COLOR     = (247, 245, 238)
BASE_CIRCLE_COLOR = (34, 38, 41)
BASE_LINE_COLOR   = (186, 193, 184)
BASE_BALL_COLOR   = (224, 153, 36)

HOOK_BALL_COLOR   = (255, 0, 85)     # Saturated Hot Magenta
HOOK_CIRCLE_COLOR = (20, 22, 24)     # Near pitch black for absolute contrast
ACCENT_GOLD       = (212, 175, 55)

BG_COLOR     = BASE_BG_COLOR
CIRCLE_COLOR = BASE_CIRCLE_COLOR
LINE_COLOR   = BASE_LINE_COLOR
BALL_COLOR   = BASE_BALL_COLOR
TEXT_HIGHLIGHT_COLOR = HOOK_BALL_COLOR

def lerp_color(color_a, color_b, t):
    """Linearly interpolates between two RGB tuples based on factor t (0.0 to 1.0)"""
    return (
        int(color_a[0] + (color_b[0] - color_a[0]) * t),
        int(color_a[1] + (color_b[1] - color_a[1]) * t),
        int(color_a[2] + (color_b[2] - color_a[2]) * t)
    )

# =====================================================
# GAME STATE & VARIABLES
# =====================================================
game_state = "PLAYING"
particles = []
shockwaves = []  

CIRCLE_RADIUS = 185
CIRCLE_THICKNESS = 0 

ball_pos = Vector2(CENTER)
ball_vel = Vector2(random.uniform(-420, 420), random.uniform(-420, 420))

START_RADIUS = 4.0
MAX_RADIUS = CIRCLE_RADIUS    
BALL_RADIUS = START_RADIUS        

GRAVITY = Vector2(0, 100)
ELASTICITY = 0.995
SPEED_BOOST = 1.15  
MAX_SPEED = 300    
locked_stable_speed = None        

# =====================================================
# EFFECTS
# =====================================================
camera_shake = 0
collision_count = 0
collision_lines = [] 

# =====================================================
# TIMERS
# =====================================================
start_time = pygame.time.get_ticks()
TOTAL_TIME_MS = 40000  
HOOK_DURATION_MS = 1500  

# =====================================================
# MAIN LOOP
# =====================================================
running = True

while running:
    dt = min(clock.tick(60) / 1000, 0.1)
    current_time = pygame.time.get_ticks()
    elapsed_time = current_time - start_time
    progress = min(1.0, elapsed_time / TOTAL_TIME_MS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # =================================================
    # PLAYING STATE & COLOR LERP MANAGEMENT
    # =================================================
    if game_state == "PLAYING":
        
        if elapsed_time < HOOK_DURATION_MS:
            hook_factor = 1.0 - (elapsed_time / HOOK_DURATION_MS)
        else:
            hook_factor = 0.0

        BG_COLOR     = BASE_BG_COLOR
        CIRCLE_COLOR = lerp_color(BASE_CIRCLE_COLOR, HOOK_CIRCLE_COLOR, hook_factor)
        LINE_COLOR   = BASE_LINE_COLOR
        BALL_COLOR   = lerp_color(BASE_BALL_COLOR, HOOK_BALL_COLOR, hook_factor)
        TEXT_HIGHLIGHT_COLOR = lerp_color(ACCENT_GOLD, HOOK_BALL_COLOR, hook_factor)

        if elapsed_time < TOTAL_TIME_MS:
            # 1. Apply Gravity
            ball_vel += GRAVITY * dt
            
            # 2. ENFORCE GLOBAL SPEED LIMITS EVERY FRAME
            if elapsed_time >= TOTAL_TIME_MS - 4000:
                ball_vel *= 0.992 
            elif collision_count >= 38 and locked_stable_speed is not None:
                if ball_vel.length() > 0:
                    ball_vel.scale_to_length(locked_stable_speed)
            elif ball_vel.length() > MAX_SPEED:
                ball_vel.scale_to_length(MAX_SPEED)

            # 3. Apply Velocity to Position
            ball_pos += ball_vel * dt
            
            direction = ball_pos - CENTER
            distance = direction.length()

            # COLLISION DETECTION
            if distance + BALL_RADIUS >= CIRCLE_RADIUS:
                collision_count += 1
                
                if distance > 0: normal = direction.normalize()
                else: normal = Vector2(1, 0)

                # Store Tether Anchor
                wall_anchor = CENTER + normal * CIRCLE_RADIUS
                collision_lines.append(Vector2(wall_anchor))

                # --- CALCULATE EXACT SCREEN BOUNDARY FOR THE CIRCLE ---
                # Find max distance from impact point to the furthest screen corner
                max_clear_radius = max(wall_anchor.distance_to(corner) for corner in SCREEN_CORNERS) + 10

                # --- TRIGGER BOLD CONCENTRIC SHOCKWAVE OUTWARDS ---
                shockwaves.append({
                    "pos": Vector2(wall_anchor),
                    "radius": 1.0,
                    "max_radius": max_clear_radius,  # Will expand until completely outside the bounds
                    "speed": 180.0,                  # Smooth, highly visible video pacing
                    "color": BALL_COLOR   
                })

                # --- LINEAR-LOG GROWTH BLEND ---
                linear_factor = progress 
                log_factor = math.log1p(progress * (math.e - 1))
                blend_factor = (1.0 - progress) * linear_factor + progress * log_factor
                
                BALL_RADIUS = START_RADIUS + (MAX_RADIUS - START_RADIUS) * blend_factor
                BALL_RADIUS = min(BALL_RADIUS, MAX_RADIUS)

                # Push inward
                ball_pos = CENTER + normal * (CIRCLE_RADIUS - BALL_RADIUS - 1)
                
                # Bounce Reflection
                ball_vel = ball_vel.reflect(normal)
                ball_vel = ball_vel.rotate(random.uniform(-8, 8))

                # --- COLLISION COUNT SPEED LOGIC ---
                if elapsed_time >= TOTAL_TIME_MS - 4000:
                    ball_vel *= ELASTICITY
                elif collision_count < 38:
                    ball_vel *= ELASTICITY
                    ball_vel *= SPEED_BOOST     
                else:
                    if locked_stable_speed is None:
                        locked_stable_speed = ball_vel.length()
                    if ball_vel.length() > 0:
                        ball_vel.scale_to_length(locked_stable_speed)
                
                # Audio Trigger
                if last_sound_time is None or (current_time - last_sound_time > SOUND_HIT_COOLDOWN_MS):
                    impact_speed_ratio = min(1.0, ball_vel.length() / 900)
                    play_progressive_sound(impact_speed_ratio, current_time, progress)

        # Memory Optimization
        if len(collision_lines) > 400:
            collision_lines = collision_lines[-400:]

        if elapsed_time >= TOTAL_TIME_MS:
            game_state = "BURSTED"
            camera_shake = 60  
            shockwaves.clear() 
            
            if bounce_sounds:
                bounce_sounds[-1].set_volume(1.0)
                bounce_sounds[-1].play()

            for _ in range(500):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(200, 2500) 
                vel = Vector2(math.cos(angle), math.sin(angle)) * speed
                particles.append({"pos": Vector2(ball_pos), "vel": vel, "radius": random.uniform(2, 8), "life": random.uniform(1.0, 3.5), "color": BASE_BALL_COLOR})

            for _ in range(600):
                angle = random.uniform(0, math.pi * 2)
                ring_pos = CENTER + Vector2(math.cos(angle), math.sin(angle)) * CIRCLE_RADIUS
                speed = random.uniform(100, 1500) 
                vel = Vector2(math.cos(angle), math.sin(angle)) * speed
                particles.append({"pos": ring_pos, "vel": vel, "radius": random.uniform(2, 6), "life": random.uniform(1.0, 3.5), "color": BASE_CIRCLE_COLOR})
            
            collision_lines.clear()
            ball_vel = Vector2(0, 0)

    # =================================================
    # UPDATE PARTICLES & SHOCKWAVES
    # =================================================
    if game_state == "PLAYING":
        for sw in shockwaves:
            sw["radius"] += sw["speed"] * dt
        # Shockwaves now safely clear the screen corner boundaries completely before removal
        shockwaves = [sw for sw in shockwaves if sw["radius"] < sw["max_radius"]]

    elif game_state == "BURSTED":
        for p in particles:
            p["vel"] += Vector2(0, 800) * dt
            p["pos"] += p["vel"] * dt
            p["life"] -= dt
        particles = [p for p in particles if p["life"] > 0]

    # =================================================
    # PREMIUM RENDERING & DRAWING
    # =================================================
    camera_shake *= 0.9
    offset_x = random.uniform(-camera_shake, camera_shake) if camera_shake > 0.5 else 0
    offset_y = random.uniform(-camera_shake, camera_shake) if camera_shake > 0.5 else 0

    screen.fill(BG_COLOR)

    if game_state == "PLAYING":
        center_render = (int(CENTER.x + offset_x), int(CENTER.y + offset_y))
        
        # 1. RENDER HIGH-VISIBILITY OUTWARD RINGS
        for sw in shockwaves:
            # Keeps alpha bold (max 210) and scales smoothly to maintain contrast out to edge
            life_ratio = max(0.0, min(1.0, 1.0 - (sw["radius"] / sw["max_radius"])))
            alpha = int(life_ratio * 210) 
            
            if alpha > 10:
                wave_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                wave_pos = (int(sw["pos"].x + offset_x), int(sw["pos"].y + offset_y))
                wave_color_with_alpha = (sw["color"][0], sw["color"][1], sw["color"][2], alpha)
                
                # Multi-layered concentric drawing for enhanced stroke weight and clean visual visibility
                r_int = int(sw["radius"])
                pygame.gfxdraw.aacircle(wave_surf, wave_pos[0], wave_pos[1], r_int, wave_color_with_alpha)
                if r_int > 1:
                    pygame.gfxdraw.aacircle(wave_surf, wave_pos[0], wave_pos[1], r_int - 1, wave_color_with_alpha)
                    pygame.gfxdraw.aacircle(wave_surf, wave_pos[0], wave_pos[1], r_int - 2, wave_color_with_alpha)
                screen.blit(wave_surf, (0, 0))

        # 2. MAIN CONTAINER CIRCLE
        pygame.gfxdraw.filled_circle(screen, center_render[0], center_render[1], CIRCLE_RADIUS, CIRCLE_COLOR)
        pygame.gfxdraw.aacircle(screen, center_render[0], center_render[1], CIRCLE_RADIUS, CIRCLE_COLOR)

        # 3. WEB LINES
        for anchor_pos in collision_lines:
            start_pos = (int(anchor_pos.x + offset_x), int(anchor_pos.y + offset_y))
            end_pos = (int(ball_pos.x + offset_x), int(ball_pos.y + offset_y))
            pygame.draw.aaline(screen, LINE_COLOR, start_pos, end_pos, 1)

        # 4. GROWING BALL
        ball_render = (int(ball_pos.x + offset_x), int(ball_pos.y + offset_y))
        int_radius = int(max(1, BALL_RADIUS))
        
        pygame.gfxdraw.filled_circle(screen, ball_render[0], ball_render[1], int_radius, BALL_COLOR)
        pygame.gfxdraw.aacircle(screen, ball_render[0], ball_render[1], int_radius, BALL_COLOR)

    elif game_state == "BURSTED":
        for p in particles:
            r = int(p["radius"] * min(1.0, p["life"]))
            if r > 0: 
                pygame.gfxdraw.aacircle(screen, int(p["pos"].x + offset_x), int(p["pos"].y + offset_y), r, p["color"])
                pygame.gfxdraw.filled_circle(screen, int(p["pos"].x + offset_x), int(p["pos"].y + offset_y), r, p["color"])

    # =================================================
    # UI RENDER BLOCK
    # =================================================
    font_small_text = pygame.font.SysFont('arial', 22, bold=True)
    font_large_text = pygame.font.SysFont('arial', 32, bold=True)
    watermark_font = pygame.font.SysFont('arial', 26) 
    
    if game_state == "PLAYING":
        prefix_text = font_small_text.render("Will this video get me ", True, CIRCLE_COLOR)
        
        if collision_count == 0:
            k_text = font_large_text.render("? ", True,HOOK_BALL_COLOR) 
        else:
            k_text = font_large_text.render(f"{collision_count} ", True, HOOK_BALL_COLOR) 
        
        suffix_word = "subscribers?" if collision_count != 1 else "subscriber?"
        suffix_text = font_small_text.render(suffix_word, True, CIRCLE_COLOR)

        total_width_top = prefix_text.get_width() + k_text.get_width() + suffix_text.get_width()
        start_x_top = (WIDTH // 2) - (total_width_top // 2)
        top_y = 125  
        
        screen.blit(prefix_text, (start_x_top, top_y + 8))
        screen.blit(k_text, (start_x_top + prefix_text.get_width(), top_y))
        screen.blit(suffix_text, (start_x_top + prefix_text.get_width() + k_text.get_width(), top_y + 8))

        part1 = watermark_font.render("@ B o u n c e ", True, CIRCLE_COLOR) 
        part2 = watermark_font.render("C u l t", True, TEXT_HIGHLIGHT_COLOR) 
        
        total_width_bottom = part1.get_width() + part2.get_width()
        start_x_bottom = (WIDTH // 2) - (total_width_bottom // 2)
        y_pos_bottom = HEIGHT - 190 
        
        screen.blit(part1, (start_x_bottom, y_pos_bottom))
        screen.blit(part2, (start_x_bottom + part1.get_width(), y_pos_bottom))
        
    else:
        end_text = pygame.font.SysFont('arial', 42, bold=True).render("HIT SUBSCRIBE!", True, HOOK_BALL_COLOR)
        end_rect = end_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 35))
        screen.blit(end_text, end_rect)

        sub_text_str = f"Not sure it'll get {collision_count} subscribers."
        sub_text = font_small_text.render(sub_text_str, True, BASE_CIRCLE_COLOR)
        sub_rect = sub_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10))
        screen.blit(sub_text, sub_rect)
        
        try:
            emoji_font = pygame.font.SysFont('segoeuiemoji', 32)
        except:
            emoji_font = font_small_text
            
        emoji_part = emoji_font.render("\U0001F97A", True, BASE_CIRCLE_COLOR) 
        emoji_rect = emoji_part.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
        screen.blit(emoji_part, emoji_rect)

    pygame.display.flip()

pygame.quit()