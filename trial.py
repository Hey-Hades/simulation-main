import pygame
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
pygame.display.set_caption("Growing Ball Simulation")
clock = pygame.time.Clock()

CENTER = Vector2(WIDTH // 2, HEIGHT // 2)

# =====================================================
# SOUND
# =====================================================
import glob

notes = []

for file in sorted(glob.glob("sounds/notes/note_*.wav")):
    try:
        notes.append(pygame.mixer.Sound(file))
    except Exception as e:
        print(f"Failed to load {file}: {e}")

# 8 channels for overlapping sounds
channels = [pygame.mixer.Channel(i) for i in range(8)]

note_index = 0
channel_index = 0

last_sound_time = 0

# Optional burst sound
try:
    burst_sound = pygame.mixer.Sound("sounds/burst.wav")
except:
    burst_sound = None

# =====================================================
# COLORS (UPDATED TO SPIDER WEB AESTHETIC)
# =====================================================
BG_COLOR = (0, 0, 0)           # Black background outside
CIRCLE_COLOR = (255, 255, 255) # Filled white circle
LINE_COLOR = (0, 0, 0)         # Black web lines
BALL_COLOR = (200, 160, 255)    # Vibrant Lavender 

# =====================================================
# GAME STATE & VARIABLES
# =====================================================
game_state = "PLAYING"
particles = []

CIRCLE_RADIUS = 165
CIRCLE_THICKNESS = 0  # Changed to 0 so the circle fills in completely white

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
# EXACT 40-SECOND TIMERS
# =====================================================
start_time = pygame.time.get_ticks()
TOTAL_TIME_MS = 40000  # 40 seconds total for both filling and bursting

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
        
        # -------------------------------------------------
        # NORMAL PHYSICS
        # -------------------------------------------------
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

                # Store Tether to inner circumference
                wall_anchor = CENTER + normal * CIRCLE_RADIUS
                collision_lines.append(Vector2(wall_anchor))

                # TIMED GROWTH CURVE 
                progress = min(1.0, elapsed_time / TOTAL_TIME_MS)
                target_radius = 4 + (MAX_RADIUS - 4) * (progress ** 4)
                
                BALL_RADIUS = max(BALL_RADIUS + 0.1, target_radius)
                BALL_RADIUS = min(BALL_RADIUS, MAX_RADIUS)

                # Push inward
                ball_pos = CENTER + normal * (CIRCLE_RADIUS - BALL_RADIUS - 1)
                
                # Bounce & Add Random Angle
                ball_vel = ball_vel.reflect(normal) * ELASTICITY
                ball_vel = ball_vel.rotate(random.uniform(-8, 8))

                # Apply Speed Boost
                ball_vel *= SPEED_BOOST     
                if ball_vel.length() > MAX_SPEED:
                    ball_vel.scale_to_length(MAX_SPEED)
                    
                    # Audio Throttled
                # Audio Throttled
                if current_time - last_sound_time > 15 and notes:
                        impact_speed = min(1.0, ball_vel.length() / 900)

                        sound_multiplier += 0.20
                        volume = min(1.0, impact_speed * sound_multiplier)

                        channel = channels[channel_index]

                        channel.set_volume(volume)
                        channel.play(notes[note_index])

                        note_index = (note_index + 1) % len(notes)
                        channel_index = (channel_index + 1) % len(channels)

                        last_sound_time = current_time
            
        # MEMORY OPTIMIZATION
        # -------------------------------------------------
        if len(collision_lines) > 400:
            collision_lines = collision_lines[-400:]

        # =================================================
        # END STATE (THE 40-SECOND BURST)
        # =================================================
        if elapsed_time >= TOTAL_TIME_MS:
            game_state = "BURSTED"
            camera_shake = 60  
   

            # 1. SPAWN BALL PARTICLES (Pink)
            for _ in range(500):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(200, 2500) 
                vel = Vector2(math.cos(angle), math.sin(angle)) * speed
                particles.append({"pos": Vector2(ball_pos), "vel": vel, "radius": random.uniform(2, 8), "life": random.uniform(1.0, 3.5), "color": BALL_COLOR})

            # 2. SPAWN CIRCLE PARTICLES (White)
            for _ in range(600):
                angle = random.uniform(0, math.pi * 2)
                ring_pos = CENTER + Vector2(math.cos(angle), math.sin(angle)) * CIRCLE_RADIUS
                speed = random.uniform(100, 1500) 
                vel = Vector2(math.cos(angle), math.sin(angle)) * speed
                particles.append({"pos": ring_pos, "vel": vel, "radius": random.uniform(2, 6), "life": random.uniform(1.0, 3.5), "color": CIRCLE_COLOR})
            
            collision_lines.clear()
            ball_vel = Vector2(0, 0)

    # =================================================
    # UPDATE PARTICLES (IF BURSTED)
    # =================================================
    elif game_state == "BURSTED":
        for p in particles:
            p["vel"] += Vector2(0, 800) * dt # Gravity
            p["pos"] += p["vel"] * dt
            p["life"] -= dt
        particles = [p for p in particles if p["life"] > 0]

    # =================================================
    # CAMERA SHAKE & DRAWING
    # =================================================
    camera_shake *= 0.9
    offset_x = random.uniform(-camera_shake, camera_shake) if camera_shake > 0.5 else 0
    offset_y = random.uniform(-camera_shake, camera_shake) if camera_shake > 0.5 else 0

    screen.fill(BG_COLOR)

    if game_state == "PLAYING":
        # Draw Filled White Circle
        center_render = (int(CENTER.x + offset_x), int(CENTER.y + offset_y))
        pygame.draw.circle(screen, CIRCLE_COLOR, center_render, CIRCLE_RADIUS, CIRCLE_THICKNESS)

        # Draw Black Lines
        for anchor_pos in collision_lines:
            pygame.draw.line(screen, LINE_COLOR, (int(anchor_pos.x + offset_x), int(anchor_pos.y + offset_y)), (int(ball_pos.x + offset_x), int(ball_pos.y + offset_y)), 1)

        # Draw Pink Ball
        ball_render = (int(ball_pos.x + offset_x), int(ball_pos.y + offset_y))
        pygame.draw.circle(screen, BALL_COLOR, ball_render, int(BALL_RADIUS))

    elif game_state == "BURSTED":
        for p in particles:
            r = int(p["radius"] * min(1.0, p["life"]))
            if r > 0: pygame.draw.circle(screen, p["color"], (int(p["pos"].x + offset_x), int(p["pos"].y + offset_y)), r)

    # =================================================
    # UI
    # =================================================
    font = pygame.font.SysFont(None, 40)
    watermark_font = pygame.font.SysFont(None, 24) 
    
    if game_state == "PLAYING":
        # THE BOUNCE COUNTER 
        bounces_text = font.render(f"Bounces: {collision_count}", True, (255, 255, 255))
        bounces_rect = bounces_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - CIRCLE_RADIUS - 60))
        screen.blit(bounces_text, bounces_rect)

        # THE WATERMARK 
        watermark_text = watermark_font.render("@BounceCult", True, (150, 150, 150))
        # Placed dynamically inside/below the circle area
        watermark_rect = watermark_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + CIRCLE_RADIUS + 40))
        screen.blit(watermark_text, watermark_rect)
        
    else:
        end_text = pygame.font.SysFont(None, 30).render("HIT SUBSCRIBE!!", True, (255, 50, 50))
        screen.blit(end_text, end_text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

    pygame.display.flip()

pygame.quit()