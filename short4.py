import pygame
import pygame.gfxdraw  # NEW: Required for premium smooth circles
import math
import random
from pygame.math import Vector2

# =====================================================
# INIT
# =====================================================
pygame.init()
pygame.mixer.init(channels=8)

WIDTH, HEIGHT = 90 * 4, 160 * 4
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Growing Ball Simulation (Premium Render)")
clock = pygame.time.Clock()

CENTER = Vector2(WIDTH // 2, HEIGHT // 2)

# =====================================================
# SOUND 
# =====================================================
try:
    bounce_sound = pygame.mixer.Sound("17800745449874VMz2Vl0.mp3")
except Exception:
    print("Warning: '17800745449874VMz2Vl0.mp3' not found. Make sure it is in the same folder!")
    bounce_sound = None

last_sound_time = 0

# =====================================================
# COLORS (High Contrast Aesthetic)
# =====================================================
BG_COLOR = (0, 0, 0)           # Deep Void Black
CIRCLE_COLOR = (255, 255, 255) # Pure White
LINE_COLOR = (0, 0, 0)         # Silk Black
BALL_COLOR = (220, 10, 30)     # Glowing Cyan (Change to your favorite!)

# =====================================================
# GAME STATE & VARIABLES
# =====================================================
game_state = "PLAYING"
particles = []

CIRCLE_RADIUS = 165
CIRCLE_THICKNESS = 0  # Filled

ball_pos = Vector2(CENTER)
ball_vel = Vector2(random.uniform(-420, 420), random.uniform(-420, 420))

BALL_RADIUS = 4
MAX_RADIUS = CIRCLE_RADIUS - 4

GRAVITY = Vector2(0, 0)
ELASTICITY = 0.995
SPEED_BOOST = 1.02  
MAX_SPEED = 7000    

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

                # TIMED GROWTH CURVE (Power of 10 for maximum end-game suspense)
                progress = min(1.0, elapsed_time / TOTAL_TIME_MS)
                target_radius = 4 + (MAX_RADIUS - 4) * (progress ** 10)
                
                BALL_RADIUS = max(BALL_RADIUS + 0.1, target_radius)
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
        
        # 1. PREMIUM WHITE CIRCLE (Fixed Layering!)
        # Draw the solid fill FIRST
        pygame.gfxdraw.filled_circle(screen, center_render[0], center_render[1], CIRCLE_RADIUS, CIRCLE_COLOR)
        # Draw the smooth edge ON TOP to hide the jagged pixels
        pygame.gfxdraw.aacircle(screen, center_render[0], center_render[1], CIRCLE_RADIUS, CIRCLE_COLOR)

        # 2. PREMIUM FINE-EDGE WEB LINES 
        for anchor_pos in collision_lines:
            start_pos = (int(anchor_pos.x + offset_x), int(anchor_pos.y + offset_y))
            end_pos = (int(ball_pos.x + offset_x), int(ball_pos.y + offset_y))
            pygame.draw.aaline(screen, LINE_COLOR, start_pos, end_pos, 1)

        # 3. PREMIUM BALL (Fixed Layering!)
        ball_render = (int(ball_pos.x + offset_x), int(ball_pos.y + offset_y))
        int_radius = int(max(1, BALL_RADIUS))
        
        # Draw the solid fill FIRST
        pygame.gfxdraw.filled_circle(screen, ball_render[0], ball_render[1], int_radius, BALL_COLOR)
        # Draw the smooth edge ON TOP
        pygame.gfxdraw.aacircle(screen, ball_render[0], ball_render[1], int_radius, BALL_COLOR)

    elif game_state == "BURSTED":
        for p in particles:
            r = int(p["radius"] * min(1.0, p["life"]))
            if r > 0: 
                # Premium particle rendering
                pygame.gfxdraw.aacircle(screen, int(p["pos"].x + offset_x), int(p["pos"].y + offset_y), r, p["color"])
                pygame.gfxdraw.filled_circle(screen, int(p["pos"].x + offset_x), int(p["pos"].y + offset_y), r, p["color"])

    # =================================================
    # UI
    # =================================================
    font = pygame.font.SysFont(None, 40)
    watermark_font = pygame.font.SysFont('arial', 26) 
    
    if game_state == "PLAYING":
        # The Bounce Counter
        bounces_text = font.render(f"Bounces: {collision_count}", True, (255, 255, 255))
        # High quality anti-aliasing is ON by default for font rendering (the 'True' parameter)
        bounces_rect = bounces_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - CIRCLE_RADIUS - 60))
        screen.blit(bounces_text, bounces_rect)

        # The Two-Tone Cinematic Watermark
        part1 = watermark_font.render("@ B o u n c e ", True, (245, 245, 245))
        part2 = watermark_font.render("C u l t", True, (255, 210, 70)) 
        
        total_width = part1.get_width() + part2.get_width()
        start_x = (WIDTH // 2) - (total_width // 2)
        y_pos = HEIGHT // 2 + CIRCLE_RADIUS + 40
        
        screen.blit(part1, (start_x, y_pos))
        screen.blit(part2, (start_x + part1.get_width(), y_pos))
        
    else:
        end_text = pygame.font.SysFont(None, 30).render("HI HIMANSHU", True, (255, 50, 50))
        screen.blit(end_text, end_text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

    pygame.display.flip()

pygame.quit()