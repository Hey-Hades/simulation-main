import math
import os
import random

import pygame
import pymunk

pygame.init()
pygame.mixer.init()

# --- Configuration ---
WIDTH = 430
HEIGHT = 800
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Zen Garden Cascade")
clock = pygame.time.Clock()

# --- Sounds ---
try:
    pygame.mixer.music.load("sounds/viacheslavstarostin-gaming-game-video-game-music-474517.mp3")
    pygame.mixer.music.set_volume(0.20)
    pygame.mixer.music.play(-1)
except pygame.error:
    pass

bounce_sounds = []
for folder in ("sounds/sp_notes", "sounds/notes"):
    if os.path.isdir(folder):
        note_files = sorted(
            os.path.join(folder, name)
            for name in os.listdir(folder)
            if name.endswith(".wav")
        )
        if note_files:
            for path in note_files[:: max(1, len(note_files) // 18)]:
                try:
                    bounce_sounds.append(pygame.mixer.Sound(path))
                except pygame.error:
                    pass
            break

if not bounce_sounds:
    try:
        bounce_sounds.append(pygame.mixer.Sound("../sounds/sound.mp3"))
    except pygame.error:
        pass

try:
    victory_sound = pygame.mixer.Sound("../sounds/sound.mp3")
except pygame.error:
    victory_sound = bounce_sounds[0] if bounce_sounds else None

# --- Physics Space ---
space = pymunk.Space()
space.gravity = (0, 140)  # Slightly lower gravity for a more relaxed fall
space.damping = 0.99      

BALL_COLLISION = 1
WALL_COLLISION = 2
SLAB_COLLISION = 3
BLOCK_COLLISION = 4

# --- Zen Aesthetics ---
BG_SAND_1 = (245, 238, 228)
BG_SAND_2 = (235, 225, 212)
PATH_COLOR = (240, 232, 220)
STONE_WALL = (85, 95, 100)
BAMBOO_SLAB = (120, 180, 110)
POND_WATER = (75, 155, 195)
# Koi & Lotus colors: Orange, White, Pink, Gold
BALL_COLORS = [(255, 120, 60), (250, 250, 250), (255, 160, 180), (255, 210, 70)] 

# --- Background Raked Sand Grid ---
grid_surface = pygame.Surface((WIDTH, HEIGHT))
sz = 20
for y in range(0, HEIGHT, sz):
    color = BG_SAND_1 if (y // sz) % 2 == 0 else BG_SAND_2
    pygame.draw.rect(grid_surface, color, (0, y, WIDTH, sz))
    # Add subtle wave lines to the sand
    pygame.draw.line(grid_surface, BG_SAND_2, (0, y + sz//2), (WIDTH, y + sz//2), 1)

# --- Helpers ---
def clamp(value, low, high):
    return max(low, min(high, value))

def lighten(color, amount=70):
    return tuple(clamp(c + amount, 0, 255) for c in color)

class Particle:
    def __init__(self, x, y, color, speed=1.0, life=0.8, radius=None):
        angle = random.uniform(0, math.tau)
        power = random.uniform(35, 150) * speed
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * power
        self.vy = math.sin(angle) * power - random.uniform(10, 60) * speed
        self.color = color
        self.life = life
        self.max_life = life
        self.radius = radius if radius is not None else random.uniform(2.0, 5.0)

    def update(self, dt):
        self.life -= dt
        self.vy += 120 * dt # Gravity for sparks
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.life > 0

    def draw(self, surface, offset):
        alpha = clamp(int(255 * self.life / self.max_life), 0, 255)
        color = (*self.color, alpha)
        size = int(self.radius * 2) + 2
        temp_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(temp_surf, color, (size // 2, size // 2), int(self.radius))
        surface.blit(temp_surf, (int(self.x + offset[0] - size // 2), int(self.y + offset[1] - size // 2)))

def create_wall(x, y, w, h):
    body = pymunk.Body(body_type=pymunk.Body.STATIC)
    body.position = (x + w / 2, y + h / 2)
    shape = pymunk.Poly.create_box(body, (w, h), radius=1)
    shape.friction = 0.2
    shape.elasticity = 0.95  
    shape.collision_type = WALL_COLLISION
    space.add(body, shape)
    return pygame.Rect(x, y, w, h)

# --- Waterfall / Marble Run Layout ---
walls = []

# Outer Boundaries
walls.append(create_wall(0, 0, 430, 40))    
walls.append(create_wall(0, 40, 20, 690))   
walls.append(create_wall(410, 40, 20, 690)) 
walls.append(create_wall(0, 730, 430, 70))  

# Alternating Stone Steps
# Platform 1: Gap on the right (x = 330 to 410)
walls.append(create_wall(20, 160, 310, 30)) 
# Platform 2: Gap on the left (x = 20 to 100)
walls.append(create_wall(100, 320, 310, 30)) 
# Platform 3: Gap on the right (x = 330 to 410)
walls.append(create_wall(20, 480, 310, 30)) 
# Platform 4: Funneling to the center gap (x = 160 to 270)
walls.append(create_wall(20, 640, 140, 30))
walls.append(create_wall(270, 640, 140, 30))

# --- Bamboo Gates (Horizontal Sliding Slabs) ---
class SlidingGate:
    def __init__(self, y, h, start_x, target_x, speed, previous_slab=None):
        self.w = 120 # Wide enough to cover the gaps
        self.h = h
        self.speed = speed
        self.target_x = target_x
        self.previous_slab = previous_slab
        self.is_closed = False
        
        self.body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.body.position = (start_x, y + h / 2)
        
        self.shape = pymunk.Poly.create_box(self.body, (self.w, self.h))
        self.shape.friction = 0.4
        self.shape.elasticity = 0.9 
        self.shape.collision_type = SLAB_COLLISION
        space.add(self.body, self.shape)

    def update(self, dt):
        if self.is_closed: return
        if self.previous_slab is not None and not self.previous_slab.is_closed: return
            
        dist = self.target_x - self.body.position.x
        if abs(dist) > 0.5:
            direction = 1 if dist > 0 else -1
            vel = self.speed * direction
            self.body.velocity = (vel, 0)
        else:
            self.body.velocity = (0, 0)
            self.body.position = (self.target_x, self.body.position.y)
            self.is_closed = True

    def draw(self, surface, offset):
        x = self.body.position.x - self.w / 2 + offset[0]
        y = self.body.position.y - self.h / 2 + offset[1]
        rect = pygame.Rect(int(x), int(y), self.w, self.h)
        
        pygame.draw.rect(surface, BAMBOO_SLAB, rect)
        pygame.draw.rect(surface, lighten(BAMBOO_SLAB, -40), rect, 2) # Darker border
        
        # Draw bamboo segmentation lines
        for i in range(1, 4):
            line_x = rect.x + (rect.w / 4) * i
            pygame.draw.line(surface, lighten(BAMBOO_SLAB, -60), (line_x, rect.y), (line_x, rect.bottom), 2)

slabs = []
prev_slab = None

# Slabs slide in horizontally to cover the gaps
slab_configs = [
    (160, 30, 500, 370), # Slides in from right to block right gap
    (320, 30, -100, 60), # Slides in from left to block left gap
    (480, 30, 500, 370), # Slides in from right to block right gap
]

for i, (y, h, start_x, target_x) in enumerate(slab_configs):
    speed = 50 + (i * 12) 
    new_slab = SlidingGate(y, h, start_x, target_x, speed, prev_slab)
    slabs.append(new_slab)
    prev_slab = new_slab 

# --- Paper Screen Gate (Breakable) ---
block_health = 18
block_active = True

block_body = pymunk.Body(body_type=pymunk.Body.STATIC)
block_body.position = (215, 655) # Centered in the bottom gap
block_shape = pymunk.Poly.create_box(block_body, (110, 30))
block_shape.elasticity = 0.5
block_shape.friction = 0.5
block_shape.collision_type = BLOCK_COLLISION
space.add(block_body, block_shape)

# --- Setup Balls ---
balls = []
SPAWN_X, SPAWN_Y = 60, 80 # Spawn top-left

for i, color in enumerate(BALL_COLORS):
    mass = 1
    radius = 11
    moment = pymunk.moment_for_circle(mass, 0, radius)
    body = pymunk.Body(mass, moment)
    body.position = (SPAWN_X, SPAWN_Y)
    body.velocity = (random.uniform(10, 60), random.uniform(-5, 5))
    
    shape = pymunk.Circle(body, radius)
    shape.elasticity = 0.95 
    shape.friction = 0.2 
    shape.collision_type = BALL_COLLISION
    space.add(body, shape)
    
    balls.append({"body": body, "shape": shape, "radius": radius, "color": color, "winner": False, "trail": [], "vertical_bounces": 0})

# --- Visuals & Audio ---
# Sakura Petals drifting downwards
sakura_particles = [
    {"x": random.randint(0, WIDTH), "y": random.randint(0, HEIGHT), 
     "radius": random.uniform(2, 5), "speed_y": random.uniform(20, 50), 
     "speed_x": random.uniform(-10, 10), "phase": random.uniform(0, math.tau)}
    for _ in range(50)
]

sparks = []
celebration_particles = []
screen_shake = 0
winner_found = False
winner_color = None
winner_ball = None
winner_time = 0
font_big = pygame.font.SysFont(None, 78, bold=True)
font_timer = pygame.font.SysFont("georgia", 24, bold=True)

def play_impact_sound(strength):
    if not bounce_sounds: return
    index = clamp(int(strength / 90), 0, len(bounce_sounds) - 1)
    sound = bounce_sounds[index]
    sound.set_volume(clamp(0.12 + strength / 800, 0.12, 0.70))
    sound.play()

def add_sparks(point, color, strength):
    count = clamp(int(strength / 25), 4, 18)
    for _ in range(count):
        sparks.append(Particle(point.x, point.y, color, speed=clamp(strength / 150, 0.5, 2.0), life=random.uniform(0.3, 0.6)))

# --- COLLISION HANDLERS ---
def collision_handler(arbiter, _space, _data):
    global screen_shake
    strength = arbiter.total_impulse.length
    if strength < 1.5: return True

    point = arbiter.contact_point_set.points[0].point_a
    normal = arbiter.contact_point_set.normal
    color = (255, 255, 255)
    ball_shape = next((shape for shape in arbiter.shapes if shape.collision_type == BALL_COLLISION), None)
    
    if ball_shape:
        for ball in balls:
            if ball["shape"] == ball_shape:
                color = ball["color"]
                current_vel = ball_shape.body.velocity
                ball_shape.body.velocity = pymunk.Vec2d(
                    current_vel.x + random.uniform(-5, 5), 
                    current_vel.y + random.uniform(-2, 2)
                )

                if abs(normal.x) < 0.2:
                    ball["vertical_bounces"] += 1
                else:
                    ball["vertical_bounces"] = 0

                if ball["vertical_bounces"] >= 4:
                    direction = random.choice([-1, 1])
                    kick_x = direction * random.uniform(100, 250) 
                    ball_shape.body.velocity = pymunk.Vec2d(current_vel.x + kick_x, current_vel.y)
                    ball["vertical_bounces"] = 0 
                break

    play_impact_sound(strength)
    if strength > 50:
        add_sparks(point, lighten(color, 25), strength)
        
    if strength > 300:
        screen_shake = max(screen_shake, clamp((strength - 300) / 90, 0, 3))
        
    return True

def block_hit_handler(arbiter, _space, _data):
    global block_health, screen_shake
    strength = arbiter.total_impulse.length
    
    ball_shape = next((shape for shape in arbiter.shapes if shape.collision_type == BALL_COLLISION), None)
    if ball_shape:
        current_vel = ball_shape.body.velocity
        ball_shape.body.velocity = pymunk.Vec2d(
            current_vel.x + random.uniform(-10, 10), 
            current_vel.y + random.uniform(-5, 5)
        )

    if strength > 5 and block_health > 0:
        block_health -= 1
        screen_shake = max(screen_shake, 1) 
        point = arbiter.contact_point_set.points[0].point_a
        add_sparks(point, (240, 240, 220), 100) # Paper scraps
        play_impact_sound(100)
        
    return True

space.on_collision(BALL_COLLISION, SLAB_COLLISION, post_solve=collision_handler)
space.on_collision(BALL_COLLISION, WALL_COLLISION, post_solve=collision_handler)
space.on_collision(BALL_COLLISION, BLOCK_COLLISION, post_solve=block_hit_handler)

# --- Main Loop ---
running = True
elapsed = 0
slow_motion_left = 0
win_fill = 0

while running:
    frame_dt = clock.tick(FPS) / 1000
    dt = min(frame_dt, 1 / 30)
    elapsed += dt

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- Block Destruction Logic ---
    if block_active and block_health <= 0:
        space.remove(block_body, block_shape)
        block_active = False
        play_impact_sound(600)
        screen_shake = 5 
        for _ in range(40):
            add_sparks(pymunk.Vec2d(215, 655), (250, 245, 230), 200)

    # --- Dramatic Winning Sequence Logic ---
    if winner_found:
        slow_motion_left = max(0, slow_motion_left - dt)
        physics_dt = dt * (0.15 if slow_motion_left > 0 else 0)
        winner_time += dt
        win_fill = clamp((winner_time - 0.25) / 2.1, 0, 1)
        
        # Pull ball into the pond
        if winner_ball:
            to_win = pymunk.Vec2d(215, 730) - winner_ball["body"].position
            winner_ball["body"].velocity = to_win * 4
            winner_ball["body"].angular_velocity *= 0.90
    else:
        physics_dt = dt
        for slab in slabs:
            slab.update(dt)

    # --- Physics Step ---
    if physics_dt > 0:
        for _ in range(2):
            space.step(physics_dt / 2)
            
        for ball in balls:
            if not ball["winner"]:
                speed = ball["body"].velocity.length
                
                if speed > 400:
                    ball["body"].velocity = ball["body"].velocity.normalized() * 400
                elif speed < 50 and not winner_found:
                    ball["body"].apply_impulse_at_local_point((random.uniform(-10, 10), random.uniform(-10, 10)))

    # --- Visual Updates ---
    for p in sakura_particles:
        p["y"] += p["speed_y"] * dt
        # Horizontal drift with sine wave for falling leaf effect
        p["x"] += (p["speed_x"] + math.sin(elapsed * 2.5 + p["phase"]) * 35) * dt
        if p["y"] > HEIGHT:
            p["y"] = -10
            p["x"] = random.randint(0, WIDTH)

    sparks = [particle for particle in sparks if particle.update(dt)]
    celebration_particles = [particle for particle in celebration_particles if particle.update(dt)]

    screen_shake = max(0, screen_shake - 30 * dt)
    shake_offset = (
        random.uniform(-screen_shake, screen_shake),
        random.uniform(-screen_shake, screen_shake),
    )

    # --- Drawing ---
    screen.blit(grid_surface, (int(shake_offset[0]), int(shake_offset[1])))
    
    # Path
    path_rect = pygame.Rect(20 + shake_offset[0], 40 + shake_offset[1], 390, 690)
    pygame.draw.rect(screen, PATH_COLOR, path_rect)

    # Draw Sakura Petals
    for p in sakura_particles:
        color = (255, 180, 195, 150) # Soft pink
        size = int(p["radius"])
        pygame.draw.ellipse(
            screen, color, 
            (int(p["x"] + shake_offset[0]), int(p["y"] + shake_offset[1]), size * 2, size)
        )

    # Start Point Indicator
    pygame.draw.circle(screen, (150, 150, 150), (60 + int(shake_offset[0]), 80 + int(shake_offset[1])), 20, 2)

    # Stone Walls
    for wall_rect in walls:
        wr = wall_rect.copy()
        wr.x += shake_offset[0]
        wr.y += shake_offset[1]
        pygame.draw.rect(screen, STONE_WALL, wr)
        # Texture dots for stone
        for _ in range(8):
            rx = random.randint(wr.x + 2, wr.right - 4)
            ry = random.randint(wr.y + 2, wr.bottom - 4)
            pygame.draw.rect(screen, lighten(STONE_WALL, 15), (rx, ry, 3, 3))
        pygame.draw.rect(screen, lighten(STONE_WALL, -30), wr, 1)

    # Koi Pond (Finish Zone)
    pond_w = 110
    pond_h = 60
    pond_rect = pygame.Rect(160 + shake_offset[0], 670 + shake_offset[1], pond_w, pond_h)
    pygame.draw.rect(screen, POND_WATER, pond_rect)
    
    # Draw water ripples in pond
    for i in range(3):
        ripple_radius = (elapsed * 20 + i * 15) % 40
        pygame.draw.circle(screen, lighten(POND_WATER, 30), pond_rect.center, int(ripple_radius), 1)
    
    pygame.draw.rect(screen, lighten(POND_WATER, -20), pond_rect, 2)
    
    # Breakable Paper Screen
    if block_active:
        block_rect = pygame.Rect(160 + shake_offset[0], 640 + shake_offset[1], 110, 30)
        pygame.draw.rect(screen, (250, 245, 235), block_rect) # Off-white paper
        # Wooden grid pattern
        pygame.draw.line(screen, (150, 120, 90), (block_rect.x, block_rect.centery), (block_rect.right, block_rect.centery), 2)
        pygame.draw.line(screen, (150, 120, 90), (block_rect.centerx, block_rect.top), (block_rect.centerx, block_rect.bottom), 2)
        pygame.draw.rect(screen, (130, 100, 70), block_rect, 3) # Frame
        
        counter_txt = font_timer.render(str(block_health), True, (80, 80, 80))
        screen.blit(counter_txt, counter_txt.get_rect(center=block_rect.center))

    # Slabs (Bamboo gates)
    for slab in slabs:
        slab.draw(screen, shake_offset)

    # Balls & Trails
    for ball in balls:
        pos = ball["body"].position
        radius = ball["radius"]
        
        ball["trail"].append((pos.x, pos.y))
        if len(ball["trail"]) > 20:
            ball["trail"].pop(0)

        # Trigger Win Condition (Falling into the pond x: 160 to 270)
        if not winner_found and (160) < pos.x < (270) and pos.y > 675:
            winner_found = True
            winner_color = ball["color"]
            winner_ball = ball
            ball["winner"] = True
            slow_motion_left = 2.0
            if victory_sound:
                victory_sound.set_volume(0.9)
                victory_sound.play()
            for _ in range(200):
                celebration_particles.append(Particle(pos.x, pos.y, ball["color"], speed=1.5, life=random.uniform(1.0, 2.5), radius=random.uniform(2, 6)))

        # Draw Trail (Like ink/watercolor streaks)
        for index, trail_pos in enumerate(ball["trail"]):
            alpha = int(15 + index * 6)
            trail_radius = max(2, int(radius * (index + 1) / len(ball["trail"])))
            trail_color = (*ball["color"], alpha)
            
            trail_surf = pygame.Surface((trail_radius * 2, trail_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, trail_color, (trail_radius, trail_radius), trail_radius)
            screen.blit(trail_surf, (int(trail_pos[0] + shake_offset[0] - trail_radius), int(trail_pos[1] + shake_offset[1] - trail_radius)))
        
        # Draw Ball
        pygame.draw.circle(screen, ball["color"], (int(pos.x + shake_offset[0]), int(pos.y + shake_offset[1])), radius)
        # Add a "Koi/Lotus" marking pattern to the ball
        pygame.draw.circle(screen, lighten(ball["color"], 80), (int(pos.x - 2 + shake_offset[0]), int(pos.y - 3 + shake_offset[1])), radius - 4)

    # Particles
    for particle in sparks + celebration_particles:
        particle.draw(screen, shake_offset)

    # Winner Screen Overlay
    if winner_found and winner_color:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((*winner_color, int(200 * win_fill)))
        screen.blit(overlay, (0, 0))
        scale = 1 + 0.05 * math.sin(elapsed * 4)
        text = font_big.render("HARMONY!", True, (255, 255, 255))
        text = pygame.transform.rotozoom(text, math.sin(elapsed * 2) * 2, scale)
        shadow = font_big.render("HARMONY!", True, (50, 50, 50))
        shadow = pygame.transform.rotozoom(shadow, math.sin(elapsed * 2) * 2, scale)
        rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(shadow, shadow.get_rect(center=(WIDTH // 2 + 3, HEIGHT // 2 + 4)))
        screen.blit(text, rect)

    pygame.display.flip()

pygame.quit()