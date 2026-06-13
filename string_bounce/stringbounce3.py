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
pygame.display.set_caption("Growing Ball (Lavender Twilight)")
clock = pygame.time.Clock()

CENTER = Vector2(WIDTH // 2, HEIGHT // 2)

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
# COLORS (Lavender Twilight Aesthetic)
# =====================================================
BG_COLOR = (246, 243, 248)      # Very pale lilac
CIRCLE_COLOR = (59, 48, 66)     # Deep plum / eggplant
LINE_COLOR = (188, 176, 196)    # Dusty lavender
BALL_COLOR = (235, 122, 102)   # Soft peach / coral

# =====================================================
# GAME STATE & VARIABLES
# =====================================================
game_state = "PLAYING"
particles = []

CIRCLE_RADIUS = 185
CIRCLE_THICKNESS = 0 

ball_pos = Vector2(CENTER)
ball_vel = Vector2(random.uniform(-420, 420), random.uniform(-420, 420))

# --- ADJUSTED RADIAL GROWTH CONSTANTS ---
START_RADIUS = 4.0
MAX_RADIUS = CIRCLE_RADIUS    # Slightly more padding for late-game clarity
BALL_RADIUS = START_RADIUS        # <--- Initialized globally so frame 1 can read it!

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

    # =================================================
    # PLAYING STATE
    # =================================================
    if game_state == "PLAYING":
        
        if elapsed_time < TOTAL_TIME_MS:
            # 1. Apply Gravity
            ball_vel += GRAVITY * dt
            
            # 2. ENFORCE GLOBAL SPEED LIMITS EVERY FRAME
            if elapsed_time >= TOTAL_TIME_MS - 4000:
                # --- NEW: Last 4 Seconds Cinematic Slow-down ---
                # Apply a smooth drag to bleed off speed naturally
                ball_vel *= 0.992 
            elif collision_count >= 38 and locked_stable_speed is not None:
                # Force the exact same velocity magnitude so gravity cannot accelerate it mid-air
                if ball_vel.length() > 0:
                    ball_vel.scale_to_length(locked_stable_speed)
            elif ball_vel.length() > MAX_SPEED:
                # Normal early-game speed cap
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

                # Store Tether
                wall_anchor = CENTER + normal * CIRCLE_RADIUS
                collision_lines.append(Vector2(wall_anchor))

                # --- NEW RE-ENGINEERED LINEAR-LOG GROWTH BLEND ---
                progress = min(1.0, elapsed_time / TOTAL_TIME_MS)
                
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
                    # Let natural elasticity take energy away during the final 4 seconds
                    ball_vel *= ELASTICITY
                elif collision_count < 38:
                    # Normal acceleration phase
                    ball_vel *= ELASTICITY
                    ball_vel *= SPEED_BOOST     
                else:
                    # Capture the stable speed exactly on the 38th bounce
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
            
            if bounce_sounds:
                bounce_sounds[-1].set_volume(1.0)
                bounce_sounds[-1].play()

            for _ in range(500):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(200, 2500) 
                vel = Vector2(math.cos(angle), math.sin(angle)) * speed
                particles.append({"pos": Vector2(ball_pos), "vel": vel, "radius": random.uniform(2, 8), "life": random.uniform(1.0, 3.5), "color": BALL_COLOR})

            for _ in range(600):
                angle = random.uniform(0, math.pi * 2)
                ring_pos = CENTER + Vector2(math.cos(angle), math.sin(angle)) * CIRCLE_RADIUS
                speed = random.uniform(100, 1500) 
                vel = Vector2(math.cos(angle), math.sin(angle)) * speed
                particles.append({"pos": ring_pos, "vel": vel, "radius": random.uniform(2, 6), "life": random.uniform(1.0, 3.5), "color": CIRCLE_COLOR})
            
            collision_lines.clear()
            ball_vel = Vector2(0, 0)

    # =================================================
    # UPDATE PARTICLES
    # =================================================
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
        
        # 1. PREMIUM CIRCLE 
        pygame.gfxdraw.filled_circle(screen, center_render[0], center_render[1], CIRCLE_RADIUS, CIRCLE_COLOR)
        pygame.gfxdraw.aacircle(screen, center_render[0], center_render[1], CIRCLE_RADIUS, CIRCLE_COLOR)

        # 2. PREMIUM FINE-EDGE WEB LINES 
        for anchor_pos in collision_lines:
            start_pos = (int(anchor_pos.x + offset_x), int(anchor_pos.y + offset_y))
            end_pos = (int(ball_pos.x + offset_x), int(ball_pos.y + offset_y))
            pygame.draw.aaline(screen, LINE_COLOR, start_pos, end_pos, 1)

        # 3. PREMIUM BALL 
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
    # UI
    # =================================================
    font_small_text = pygame.font.SysFont('arial', 22, bold=True)
    font_large_text = pygame.font.SysFont('arial', 32, bold=True)
    watermark_font = pygame.font.SysFont('arial', 26) 
    
    if game_state == "PLAYING":
        prefix_text = font_small_text.render("Will this video get me ", True, CIRCLE_COLOR)
        
        if collision_count == 0:
            k_text = font_large_text.render("? ", True, BALL_COLOR) 
        else:
            k_text = font_large_text.render(f"{collision_count} ", True, BALL_COLOR) 
        
        suffix_word = "subscribers?" if collision_count != 1 else "subscriber?"
        suffix_text = font_small_text.render(suffix_word, True, CIRCLE_COLOR)

        total_width_top = prefix_text.get_width() + k_text.get_width() + suffix_text.get_width()
        start_x_top = (WIDTH // 2) - (total_width_top // 2)
        top_y = 125  
        
        screen.blit(prefix_text, (start_x_top, top_y + 8))
        screen.blit(k_text, (start_x_top + prefix_text.get_width(), top_y))
        screen.blit(suffix_text, (start_x_top + prefix_text.get_width() + k_text.get_width(), top_y + 8))

        part1 = watermark_font.render("@ B o u n c e ", True, CIRCLE_COLOR) 
        # Updated to use BALL_COLOR to match the aesthetic seamlessly
        part2 = watermark_font.render("C u l t", True, BALL_COLOR) 
        
        total_width_bottom = part1.get_width() + part2.get_width()
        start_x_bottom = (WIDTH // 2) - (total_width_bottom // 2)
        y_pos_bottom = HEIGHT - 190 
        
        screen.blit(part1, (start_x_bottom, y_pos_bottom))
        screen.blit(part2, (start_x_bottom + part1.get_width(), y_pos_bottom))
        
    else:
        end_text = pygame.font.SysFont('arial', 42, bold=True).render("HIT SUBSCRIBE!!", True, BALL_COLOR)
        end_rect = end_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 35))
        screen.blit(end_text, end_rect)

        sub_text_str = f"Not sure it'll get {collision_count} subscribers."
        sub_text = font_small_text.render(sub_text_str, True, CIRCLE_COLOR)
        sub_rect = sub_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10))
        screen.blit(sub_text, sub_rect)
        
        try:
            emoji_font = pygame.font.SysFont('segoeuiemoji', 32)
        except:
            emoji_font = font_small_text
            
        emoji_part = emoji_font.render("\U0001F97A", True, CIRCLE_COLOR) 
        emoji_rect = emoji_part.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
        screen.blit(emoji_part, emoji_rect)

    pygame.display.flip()

pygame.quit()