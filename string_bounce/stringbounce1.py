import pygame
import pygame.gfxdraw
import math
import random
from pygame.math import Vector2

# =====================================================
# INIT
# =====================================================
pygame.init()
pygame.mixer.init(channels=8)

WIDTH, HEIGHT = 430, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Growing Ball (Zen - Suspenseful Ending)")
clock = pygame.time.Clock()

CENTER = Vector2(WIDTH // 2, HEIGHT // 2)

# =====================================================
# SOUND 
# =====================================================
try:
    bounce_sound = pygame.mixer.Sound("../sounds/popshortt4.mp3")
except Exception:
    print("Warning: Sound file not found. Make sure it is in the same folder!")
    bounce_sound = None

last_sound_time = 0

# =====================================================
# COLORS (Matcha / Zen Aesthetic)
# =====================================================
BG_COLOR = (244, 241, 234)
CIRCLE_COLOR = (44, 76, 63)
LINE_COLOR = (163, 177, 138)
BALL_COLOR = (235, 122, 102)

# =====================================================
# GAME STATE & VARIABLES
# =====================================================
game_state = "PLAYING"
particles = []

CIRCLE_RADIUS = 165
CIRCLE_THICKNESS = 0 

ball_pos = Vector2(CENTER)
ball_vel = Vector2(random.uniform(-420, 420), random.uniform(-420, 420))

BALL_RADIUS = 4
# FIXED: Increased the final gap from 4 to 15 so it doesn't vibrate at the end
MAX_RADIUS = CIRCLE_RADIUS - 15 

GRAVITY = Vector2(0, 0)
ELASTICITY = 0.995
SPEED_BOOST = 1.02  
# FIXED: Lowered max speed so the final bounces are distinct and not chaotic
MAX_SPEED = 2000    

# =====================================================
# EFFECTS
# =====================================================
camera_shake = 0
collision_count = 0
collision_lines = [] 
sound_multiplier = 1.0

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
            ball_vel += GRAVITY * dt
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

                # TIMED GROWTH CURVE (Sine S-Curve)
                progress = min(1.0, elapsed_time / TOTAL_TIME_MS)
                s_curve = 0.5 * (1 - math.cos(math.pi * progress))
                
                BALL_RADIUS = 4 + (MAX_RADIUS - 4) * s_curve
                BALL_RADIUS = min(BALL_RADIUS, MAX_RADIUS)

                # Push inward
                ball_pos = CENTER + normal * (CIRCLE_RADIUS - BALL_RADIUS - 1)
                
                # Bounce
                ball_vel = ball_vel.reflect(normal) * ELASTICITY
                ball_vel = ball_vel.rotate(random.uniform(-8, 8))

                # Speed Boost
                ball_vel *= SPEED_BOOST     
                if ball_vel.length() > MAX_SPEED:
                    ball_vel.scale_to_length(MAX_SPEED)
                
                # Audio Throttled
                if current_time - last_sound_time > 40:
                    impact_speed = min(1.0, ball_vel.length() / 900)
                    sound_multiplier += 0.20
                    volume = min(1.0, impact_speed * sound_multiplier)
                    if bounce_sound:
                        bounce_sound.set_volume(volume)
                        bounce_sound.play()
                    last_sound_time = current_time

        # Memory Optimization
        if len(collision_lines) > 400:
            collision_lines = collision_lines[-400:]

        if elapsed_time >= TOTAL_TIME_MS:
            game_state = "BURSTED"
            camera_shake = 60  
            
            if bounce_sound:
                bounce_sound.set_volume(1.0)
                bounce_sound.play()

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
        # 1. TOP ENGAGEMENT HOOK 
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

        # 2. BOTTOM CINEMATIC WATERMARK
        part1 = watermark_font.render("@ B o u n c e ", True, CIRCLE_COLOR) 
        part2 = watermark_font.render("C u l t", True, (232, 192, 81)) 
        
        total_width_bottom = part1.get_width() + part2.get_width()
        start_x_bottom = (WIDTH // 2) - (total_width_bottom // 2)
        y_pos_bottom = HEIGHT - 190 
        
        screen.blit(part1, (start_x_bottom, y_pos_bottom))
        screen.blit(part2, (start_x_bottom + part1.get_width(), y_pos_bottom))
        
    else:
        # 1. MAIN END TEXT (Shifted up slightly)
        end_text = pygame.font.SysFont('arial', 42, bold=True).render("HIT SUBSCRIBE!", True, BALL_COLOR)
        end_rect = end_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 35))
        screen.blit(end_text, end_rect)

        # 2. PLEADING SUBTITLE (Added 'subscribers' and perfectly centered)
        sub_text_str = f"Not sure it'll get {collision_count} subscribers."
        sub_text = font_small_text.render(sub_text_str, True, CIRCLE_COLOR)
        sub_rect = sub_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10))
        screen.blit(sub_text, sub_rect)
        
        # 3. EMOJI (Centered below the text)
        try:
            # Increased emoji font size slightly for better visibility
            emoji_font = pygame.font.SysFont('segoeuiemoji', 32)
        except:
            emoji_font = font_small_text
            
        emoji_part = emoji_font.render("\U0001F97A", True, CIRCLE_COLOR) 
        emoji_rect = emoji_part.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
        screen.blit(emoji_part, emoji_rect)

    pygame.display.flip()

pygame.quit()
