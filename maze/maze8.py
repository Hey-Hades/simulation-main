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
pygame.display.set_caption("Motorized Pinball Maze - Toxic Factory")
clock = pygame.time.Clock()

# --- Sounds ---
try:
    pygame.mixer.music.load("sounds/viacheslavstarostin-gaming-game-video-game-music-474517.mp3")
    pygame.mixer.music.set_volume(0.25)
    pygame.mixer.music.play(-1)
except pygame.error:
    pass

bounce_sounds = []
for folder in ("../sounds/sp_notes", "sounds/notes"):
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
space.gravity = (0, 350)      
space.damping = 0.98         

# --- Collision Types ---
BALL_COLLISION = 1
WALL_COLLISION = 2
BLOCK_COLLISION = 4
BUMPER_COLLISION = 6
CONVEYOR_COLLISION = 7
SWEEPER_COLLISION = 8

# --- Filters ---
CATEGORY_BALL = 0b0001
CATEGORY_ENVIRONMENT = 0b0010

# --- Colors (Toxic Factory Theme) ---
BG_DARK = (15, 20, 15)          # Deep murky green
BG_GRID = (22, 30, 22)          # Slightly lighter grid
WALL_GRAY = (120, 130, 120)     # Industrial metal
BUMPER_PINK = (255, 20, 147)    # Neon Pink
CONVEYOR_CYAN = (0, 200, 255)   # Neon Cyan
SWEEPER_ORANGE = (255, 100, 0)  # Hazard Orange
FINISH_GREEN = (50, 255, 50)    # Success Green
BALL_COLORS = [(255, 255, 255), (0, 255, 255), (255, 100, 0), (255, 20, 147)]

# --- Background Grid ---
grid_surface = pygame.Surface((WIDTH, HEIGHT))
sz = 20
for x in range(0, WIDTH, sz):
    for y in range(0, HEIGHT, sz):
        color = BG_DARK if ((x // sz) + (y // sz)) % 2 == 0 else BG_GRID
        pygame.draw.rect(grid_surface, color, (x, y, sz, sz))

# --- Helpers ---
def clamp(value, low, high):
    return max(low, min(high, value))

def lighten(color, amount=70):
    return tuple(clamp(c + amount, 0, 255) for c in color)

class Particle:
    def __init__(self, x, y, color, speed=1.0, life=0.8, radius=None):
        angle = random.uniform(0, math.tau)
        power = random.uniform(35, 210) * speed
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * power
        self.vy = math.sin(angle) * power - random.uniform(10, 90) * speed
        self.color = color
        self.life = life
        self.max_life = life
        self.radius = radius if radius is not None else random.uniform(1.5, 4.5)

    def update(self, dt):
        self.life -= dt
        self.vy += 190 * dt
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
    shape.elasticity = 0.8  
    shape.collision_type = WALL_COLLISION
    shape.filter = pymunk.ShapeFilter(categories=CATEGORY_ENVIRONMENT)
    space.add(body, shape)
    return pygame.Rect(x, y, w, h)

# --- ENVIRONMENT ARCHITECTURE ---
walls = []
bumpers = []
conveyors = []

# Outer Boundaries
walls.append(create_wall(0, 0, 430, 40))    
walls.append(create_wall(0, 40, 20, 690))   
walls.append(create_wall(410, 40, 20, 690)) 
walls.append(create_wall(0, 730, 430, 70))  
walls.append(create_wall(20, 665, 120, 10))

# 1. High-Restitution Bumpers (Pachinko Style Top)
def create_bumper(x, y, radius=12):
    body = pymunk.Body(body_type=pymunk.Body.STATIC)
    body.position = (x, y)
    shape = pymunk.Circle(body, radius)
    shape.elasticity = 1.8 # Very bouncy
    shape.friction = 0.5
    shape.collision_type = BUMPER_COLLISION
    space.add(body, shape)
    bumpers.append({"pos": (x, y), "radius": radius, "flash": 0})

bumper_positions = [
    (150, 120), (280, 120),
    (100, 180), (215, 180), (330, 180),
    (150, 240), (280, 240)
]
for pos in bumper_positions:
    create_bumper(pos[0], pos[1])

# 2. Conveyor Belts (Surface Velocity Mechanics)
def create_conveyor(p1, p2, speed, thickness=12):
    body = pymunk.Body(body_type=pymunk.Body.STATIC)
    shape = pymunk.Segment(body, p1, p2, thickness)
    shape.friction = 1.5 # High friction to grip the ball
    # surface_velocity pushes objects touching the surface
    shape.surface_velocity = (speed, 0) 
    shape.elasticity = 0.2
    shape.collision_type = CONVEYOR_COLLISION
    space.add(body, shape)
    
    # Pre-calculate rendering points
    length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    conveyors.append({"p1": p1, "p2": p2, "speed": speed, "thickness": thickness, "length": length, "angle": angle})

create_conveyor((20, 350), (330, 400), speed=250)   # Pushes Right
create_conveyor((410, 480), (100, 530), speed=-250) # Pushes Left

# 3. The Kinematic Sweeper Pendulum
sweeper_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
sweeper_body.position = (215, 620)
sweeper_shape = pymunk.Poly.create_box(sweeper_body, (220, 24), radius=2)
sweeper_shape.friction = 0.5
sweeper_shape.elasticity = 1.2
sweeper_shape.collision_type = SWEEPER_COLLISION
space.add(sweeper_body, sweeper_shape)

# --- Breakable Glass Block Stack ---
glass_blocks = []
block_w, block_h = 24, 20
start_x, start_y = 125, 710

for i in range(3):
    b_body = pymunk.Body(body_type=pymunk.Body.STATIC)
    b_body.position = (start_x, start_y - (i * block_h))
    b_shape = pymunk.Poly.create_box(b_body, (block_w, block_h))
    b_shape.elasticity = 0.5
    b_shape.friction = 0.5
    b_shape.collision_type = BLOCK_COLLISION
    space.add(b_body, b_shape)
    glass_blocks.append({"body": b_body, "shape": b_shape, "health": 12, "active": True})

# --- Setup Balls ---
balls = []
SPAWN_X, SPAWN_Y = 70, 70

for i, color in enumerate(BALL_COLORS):
    mass = 1
    radius = 10
    moment = pymunk.moment_for_circle(mass, 0, radius)
    body = pymunk.Body(mass, moment)
    body.position = (SPAWN_X + random.uniform(-10, 10), SPAWN_Y)
    body.velocity = (random.uniform(-50, 50), random.uniform(-10, 10))
    
    shape = pymunk.Circle(body, radius)
    shape.elasticity = 0.9  
    shape.friction = 0.8 # Higher friction to stick to conveyors
    shape.collision_type = BALL_COLLISION
    space.add(body, shape)
    
    balls.append({"body": body, "shape": shape, "radius": radius, "color": color, "winner": False, "trail": []})

# --- Visuals & Audio ---
background_particles = []
sparks = []
celebration_particles = []
screen_shake = 0
winner_found = False
winner_color = None
winner_ball = None
winner_time = 0
font_big = pygame.font.SysFont(None, 78, bold=True)
font_small = pygame.font.SysFont("georgia", 16, bold=True)

def play_impact_sound(strength, high_pitch=False):
    if not bounce_sounds: return
    index = clamp(int(strength / 90), 0, len(bounce_sounds) - 1)
    if high_pitch: index = min(index + 2, len(bounce_sounds) - 1)
    sound = bounce_sounds[index]
    sound.set_volume(clamp(0.16 + strength / 650, 0.16, 0.85))
    sound.play()

def add_sparks(point, color, strength):
    count = clamp(int(strength / 22), 5, 22)
    for _ in range(count):
        sparks.append(Particle(point.x, point.y, color, speed=clamp(strength / 150, 0.5, 2.2), life=random.uniform(0.28, 0.75)))

# --- COLLISION HANDLERS ---
def general_collision_handler(arbiter, _space, _data):
    global screen_shake
    strength = arbiter.total_impulse.length
    if strength < 10: return True

    point = arbiter.contact_point_set.points[0].point_a
    color = (200, 200, 200)
    
    # Bumper logic
    is_bumper = any(s.collision_type == BUMPER_COLLISION for s in arbiter.shapes)
    if is_bumper:
        color = BUMPER_PINK
        play_impact_sound(strength * 2, high_pitch=True)
        # Visual flash for bumper
        for b in bumpers:
            if math.hypot(b["pos"][0] - point.x, b["pos"][1] - point.y) < b["radius"] * 2:
                b["flash"] = 1.0
    else:
        play_impact_sound(strength)

    if strength > 50: add_sparks(point, lighten(color, 25), strength)
    if strength > 400: screen_shake = max(screen_shake, clamp((strength - 400) / 80, 0, 5))
    return True

def block_hit_handler(arbiter, _space, _data):
    global screen_shake
    strength = arbiter.total_impulse.length
    if strength < 5: return True

    point = arbiter.contact_point_set.points[0].point_a
    block_shape = next((shape for shape in arbiter.shapes if shape.collision_type == BLOCK_COLLISION), None)
    
    if block_shape:
        for block in glass_blocks:
            if block["shape"] == block_shape and block["active"]:
                block["health"] -= 1
                screen_shake = max(screen_shake, 2.0) 
                add_sparks(point, (150, 200, 255), 150)
                play_impact_sound(200)
                break
    return True

space.on_collision(BALL_COLLISION, WALL_COLLISION, post_solve=general_collision_handler)
space.on_collision(BALL_COLLISION, BUMPER_COLLISION, post_solve=general_collision_handler)
space.on_collision(BALL_COLLISION, SWEEPER_COLLISION, post_solve=general_collision_handler)
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
        if event.type == pygame.QUIT: running = False

    # --- Sweeper Kinematics ---
    if not winner_found:
        # Sine wave to swing back and forth
        sweeper_body.angular_velocity = math.cos(elapsed * 2.5) * 4.0
    else:
        sweeper_body.angular_velocity *= 0.95

    # --- Block Destruction Logic ---
    for block in glass_blocks:
        if block["active"] and block["health"] <= 0:
            space.remove(block["body"], block["shape"])
            block["active"] = False
            play_impact_sound(800)
            screen_shake = max(screen_shake, 6)
            pos = block["body"].position
            for _ in range(30):
                add_sparks(pos, (180, 230, 255), 300)

    # --- Winning Sequence Logic ---
    if winner_found:
        slow_motion_left = max(0, slow_motion_left - dt)
        physics_dt = dt * (0.18 if slow_motion_left > 0 else 0)
        winner_time += dt
        win_fill = clamp((winner_time - 0.25) / 2.1, 0, 1)
        
        if winner_ball:
            to_win = pymunk.Vec2d(50, 700) - winner_ball["body"].position
            winner_ball["body"].velocity = to_win * 5
            winner_ball["body"].angular_velocity *= 0.95
    else:
        physics_dt = dt

    # --- Physics Step ---
    if physics_dt > 0:
        for _ in range(2): space.step(physics_dt / 2)
            
        for ball in balls:
            if not ball["winner"]:
                speed = ball["body"].velocity.length
                if speed > 650: ball["body"].velocity = ball["body"].velocity.normalized() * 650

    # --- Visual Updates ---
    sparks = [particle for particle in sparks if particle.update(dt)]
    celebration_particles = [particle for particle in celebration_particles if particle.update(dt)]
    for b in bumpers: b["flash"] = max(0, b["flash"] - dt * 3)

    screen_shake = max(0, screen_shake - 35 * dt)
    shake_offset = (random.uniform(-screen_shake, screen_shake), random.uniform(-screen_shake, screen_shake))

    # --- Drawing ---
    screen.blit(grid_surface, (int(shake_offset[0]), int(shake_offset[1])))

    for wall_rect in walls:
        wr = wall_rect.copy()
        wr.x += shake_offset[0]
        wr.y += shake_offset[1]
        pygame.draw.rect(screen, WALL_GRAY, wr)
        pygame.draw.rect(screen, (0, 0, 0), wr, 2)

    # Draw Conveyors
    for conv in conveyors:
        p1 = (conv["p1"][0] + shake_offset[0], conv["p1"][1] + shake_offset[1])
        p2 = (conv["p2"][0] + shake_offset[0], conv["p2"][1] + shake_offset[1])
        pygame.draw.line(screen, (40, 40, 40), p1, p2, conv["thickness"] * 2)
        pygame.draw.line(screen, CONVEYOR_CYAN, p1, p2, 4)
        
        # Animate treads
        tread_spacing = 20
        offset = (elapsed * conv["speed"]) % tread_spacing
        for d in range(int(offset), int(conv["length"]), tread_spacing):
            tx = p1[0] + math.cos(conv["angle"]) * d
            ty = p1[1] + math.sin(conv["angle"]) * d
            nx = math.cos(conv["angle"] + math.pi/2) * conv["thickness"]
            ny = math.sin(conv["angle"] + math.pi/2) * conv["thickness"]
            pygame.draw.line(screen, CONVEYOR_CYAN, (tx - nx, ty - ny), (tx + nx, ty + ny), 2)

    # Draw Bumpers
    for b in bumpers:
        bx = int(b["pos"][0] + shake_offset[0])
        by = int(b["pos"][1] + shake_offset[1])
        br = b["radius"]
        
        if b["flash"] > 0:
            glow_r = int(br + 10 * b["flash"])
            surf = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*BUMPER_PINK, int(150 * b["flash"])), (glow_r, glow_r), glow_r)
            screen.blit(surf, (bx - glow_r, by - glow_r))
            
        pygame.draw.circle(screen, BUMPER_PINK, (bx, by), br)
        pygame.draw.circle(screen, (255, 255, 255), (bx - 3, by - 3), 3)
        pygame.draw.circle(screen, (0, 0, 0), (bx, by), br, 2)

    # Draw Sweeper Pendulum
    pts = [sweeper_shape.body.local_to_world(v) for v in sweeper_shape.get_vertices()]
    pts = [(int(p.x + shake_offset[0]), int(p.y + shake_offset[1])) for p in pts]
    pygame.draw.polygon(screen, SWEEPER_ORANGE, pts)
    pygame.draw.polygon(screen, (0, 0, 0), pts, 2)
    # Pivot joint visual
    pygame.draw.circle(screen, (50, 50, 50), (int(sweeper_body.position.x + shake_offset[0]), int(sweeper_body.position.y + shake_offset[1])), 10)

    # Finish Zone
    fz_rect = pygame.Rect(20 + shake_offset[0], 670 + shake_offset[1], 60, 60)
    pygame.draw.rect(screen, FINISH_GREEN, fz_rect)
    pygame.draw.rect(screen, (0, 0, 0), fz_rect, 2)
    
    # Draw Glass Blocks
    for block in glass_blocks:
        if block["active"]:
            bx = int(block["body"].position.x - block_w/2 + shake_offset[0])
            by = int(block["body"].position.y - block_h/2 + shake_offset[1])
            rect = pygame.Rect(bx, by, block_w, block_h)
            pygame.draw.rect(screen, (180, 230, 255), rect)
            pygame.draw.rect(screen, (255, 255, 255), rect, 1) # Glass highlight
            
            # Health indicator
            health_color = (0, 0, 0) if block["health"] > 4 else (255, 0, 0)
            txt = font_small.render(str(block["health"]), True, health_color)
            screen.blit(txt, txt.get_rect(center=rect.center))

    # Draw Balls
    for ball in balls:
        pos = ball["body"].position
        radius = ball["radius"]
        
        ball["trail"].append((pos.x, pos.y))
        if len(ball["trail"]) > 15: ball["trail"].pop(0)

        # Win Trigger
        blocks_cleared = all(not b["active"] for b in glass_blocks)
        if not winner_found and blocks_cleared and pos.x < 100 and pos.y > 670:
            winner_found = True
            winner_color = ball["color"]
            winner_ball = ball
            ball["winner"] = True
            slow_motion_left = 2.0
            if victory_sound:
                victory_sound.set_volume(0.9)
                victory_sound.play()
            for _ in range(260):
                celebration_particles.append(Particle(pos.x, pos.y, ball["color"], speed=1.8, life=random.uniform(1.1, 2.8), radius=random.uniform(2, 6)))

        for index, trail_pos in enumerate(ball["trail"]):
            alpha = int(20 + index * 8)
            trail_radius = max(2, int(radius * (index + 1) / len(ball["trail"])))
            trail_surf = pygame.Surface((trail_radius * 2, trail_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (*ball["color"], alpha), (trail_radius, trail_radius), trail_radius)
            screen.blit(trail_surf, (int(trail_pos[0] + shake_offset[0] - trail_radius), int(trail_pos[1] + shake_offset[1] - trail_radius)))

        pygame.draw.circle(screen, ball["color"], (int(pos.x + shake_offset[0]), int(pos.y + shake_offset[1])), radius)
        pygame.draw.circle(screen, (255, 255, 255), (int(pos.x - 3 + shake_offset[0]), int(pos.y - 4 + shake_offset[1])), 3)

    for particle in sparks + celebration_particles:
        particle.draw(screen, shake_offset)

    if winner_found and winner_color:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((*winner_color, int(215 * win_fill)))
        screen.blit(overlay, (0, 0))
        scale = 1 + 0.08 * math.sin(elapsed * 8)
        text = font_big.render("WINNER!", True, (255, 255, 255))
        text = pygame.transform.rotozoom(text, math.sin(elapsed * 4) * 3, scale)
        shadow = font_big.render("WINNER!", True, winner_color)
        shadow = pygame.transform.rotozoom(shadow, math.sin(elapsed * 4) * 3, scale)
        rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(shadow, shadow.get_rect(center=(WIDTH // 2 + 3, HEIGHT // 2 + 4)))
        screen.blit(text, rect)

    pygame.display.flip()

pygame.quit()