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
pygame.display.set_caption("Motorized Pinball Maze - Brutalist")
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
space.gravity = (0, 300)      
space.damping = 0.98         

BALL_COLLISION = 1
WALL_COLLISION = 2
SLAB_COLLISION = 3
BLOCK_COLLISION = 4
PISTON_COLLISION = 5

# --- COLLISION FILTER CATEGORIES (Bitmasks) ---
CATEGORY_BALL = 0b0001
CATEGORY_ENVIRONMENT = 0b0010
CATEGORY_PISTON = 0b0100

# --- Exact Colors (Brutalist / Blood & Concrete) ---
GRID_GREEN = (20, 20, 20)       # Dark Charcoal
GRID_PURPLE = (26, 26, 26)      # Slightly Lighter Charcoal
PATH_PURPLE = (15, 15, 15)      # Near Black Void
WALL_PURPLE = (235, 235, 235)   # Stark Concrete White
SLAB_GREEN = (210, 15, 30)      # Blood Red
FINISH_GREEN = (255, 195, 0)    # Industrial Hazard Yellow
PISTON_COLOR = (210, 15, 30)    # Blood Red
BALL_COLORS = [(255, 255, 255), (210, 15, 30), (255, 195, 0), (100, 100, 100)]

# --- Background Grid ---
grid_surface = pygame.Surface((WIDTH, HEIGHT))
sz = 15
for x in range(0, WIDTH, sz):
    for y in range(0, HEIGHT, sz):
        color = GRID_GREEN if ((x // sz) + (y // sz)) % 2 == 0 else GRID_PURPLE
        pygame.draw.rect(grid_surface, color, (x, y, sz, sz))

# --- Helpers ---
def clamp(value, low, high):
    return max(low, min(high, value))

def mix(a, b, t):
    return clamp(int(a + (b - a) * t), 0, 255)

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
    shape.elasticity = 1.15  
    shape.collision_type = WALL_COLLISION
    shape.filter = pymunk.ShapeFilter(categories=CATEGORY_ENVIRONMENT)
    space.add(body, shape)
    return pygame.Rect(x, y, w, h)

def create_angled_wall(p1, p2, thickness=10):
    body = pymunk.Body(body_type=pymunk.Body.STATIC)
    shape = pymunk.Segment(body, p1, p2, thickness)
    shape.friction = 0.2
    shape.elasticity = 1.15  
    shape.collision_type = WALL_COLLISION
    shape.filter = pymunk.ShapeFilter(categories=CATEGORY_ENVIRONMENT)
    space.add(body, shape)
    return shape

# --- Base Layout ---
walls = []
angled_walls = []

# Outer Boundaries
walls.append(create_wall(0, 0, 430, 40))    
walls.append(create_wall(0, 40, 20, 690))   
walls.append(create_wall(410, 40, 20, 690)) 
walls.append(create_wall(0, 730, 430, 70))  

# Angled Funnels
angled_walls.append(create_angled_wall((20, 80), (100, 130), 8))
angled_walls.append(create_angled_wall((410, 80), (170, 130), 8))

angled_walls.append(create_angled_wall((20, 260), (250, 310), 8))
angled_walls.append(create_angled_wall((410, 260), (320, 310), 8))

angled_walls.append(create_angled_wall((410, 440), (170, 490), 8))
angled_walls.append(create_angled_wall((20, 440), (100, 490), 8))

# --- Small Safety Wall Over The Finish Line Area ---
walls.append(create_wall(20, 665, 120, 10))

# --- Motorized Descending Piston Setup ---
PISTON_WIDTH = 390
PISTON_HEIGHT = 20
piston_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
piston_body.position = (215, 45) 
piston_shape = pymunk.Poly.create_box(piston_body, (PISTON_WIDTH, PISTON_HEIGHT))
piston_shape.friction = 0.3
piston_shape.elasticity = 1.1
piston_shape.collision_type = PISTON_COLLISION

# The piston only masks/collides with BALLS (ignores turnstiles/walls)
piston_shape.filter = pymunk.ShapeFilter(
    categories=CATEGORY_PISTON,
    mask=CATEGORY_BALL
)
space.add(piston_body, piston_shape)

PISTON_SPEED = 10.0  
PISTON_MAX_Y = 640.0 

# --- Motorized Turnstiles (Propellers) ---
class Turnstile:
    def __init__(self, x, y, size=160, thickness=20, mass=12, motor_speed=0.0):
        moment = pymunk.moment_for_box(mass / 2, (size, thickness)) * 2
        self.body = pymunk.Body(mass, moment)
        self.body.position = (x, y)
        space.add(self.body)
        
        self.shape1 = pymunk.Poly.create_box(self.body, (size, thickness), radius=2)
        self.shape2 = pymunk.Poly.create_box(self.body, (thickness, size), radius=2)
        
        for shape in (self.shape1, self.shape2):
            shape.friction = 0.2
            shape.elasticity = 1.25 
            shape.collision_type = SLAB_COLLISION 
            
            shape.filter = pymunk.ShapeFilter(
                categories=CATEGORY_ENVIRONMENT,
                mask=pymunk.ShapeFilter.ALL_MASKS() ^ CATEGORY_PISTON
            )
            space.add(shape) 
            
        self.anchor_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        self.anchor_body.position = (x, y)
        
        self.pivot = pymunk.PivotJoint(self.anchor_body, self.body, (x, y))
        space.add(self.pivot)

        if motor_speed != 0:
            self.motor = pymunk.SimpleMotor(self.anchor_body, self.body, motor_speed)
            self.motor.max_force = 5000000 
            space.add(self.motor)
        
    def draw(self, surface, offset):
        for shape in (self.shape1, self.shape2):
            pts = [shape.body.local_to_world(v) for v in shape.get_vertices()]
            pts = [(int(p.x + offset[0]), int(p.y + offset[1])) for p in pts]
            pygame.draw.polygon(surface, SLAB_GREEN, pts)
            pygame.draw.polygon(surface, (0, 0, 0), pts, 2)
            
        cx = int(self.body.position.x + offset[0])
        cy = int(self.body.position.y + offset[1])
        pygame.draw.circle(surface, (80, 80, 80), (cx, cy), 12)
        pygame.draw.circle(surface, (0, 0, 0), (cx, cy), 12, 2)
        pygame.draw.circle(surface, (150, 150, 150), (cx, cy), 4)

turnstiles = []
turnstiles.append(Turnstile(290, 210, motor_speed=1.5))   
turnstiles.append(Turnstile(135, 390, motor_speed=-1.5))  
turnstiles.append(Turnstile(250, 600, motor_speed=-1.5))   

# --- Breakable Gate Block ---
block_health = 25
block_active = True

block_body = pymunk.Body(body_type=pymunk.Body.STATIC)
block_body.position = (125, 700) 
block_shape = pymunk.Poly.create_box(block_body, (30, 60))
block_shape.elasticity = 1.1
block_shape.friction = 0.2
block_shape.collision_type = BLOCK_COLLISION
block_shape.filter = pymunk.ShapeFilter(categories=CATEGORY_ENVIRONMENT)
space.add(block_body, block_shape)

# --- Setup Balls ---
balls = []
SPAWN_X, SPAWN_Y = 70, 70

for i, color in enumerate(BALL_COLORS):
    mass = 1
    radius = 10
    moment = pymunk.moment_for_circle(mass, 0, radius)
    body = pymunk.Body(mass, moment)
    
    body.position = (SPAWN_X, SPAWN_Y)
    body.velocity = (random.uniform(-50, 50), random.uniform(-10, 10))
    
    shape = pymunk.Circle(body, radius)
    shape.elasticity = 1.15  
    shape.friction = 0.05 
    shape.collision_type = BALL_COLLISION
    
    # Balls collide with everything
    shape.filter = pymunk.ShapeFilter(
        categories=CATEGORY_BALL,
        mask=pymunk.ShapeFilter.ALL_MASKS()
    )
    space.add(body, shape)
    
    balls.append({"body": body, "shape": shape, "radius": radius, "color": color, "winner": False, "trail": [], "vertical_bounces": 0})

# --- Visuals & Audio ---
background_particles = [
    {"x": random.randint(0, WIDTH), "y": random.randint(0, HEIGHT), "radius": random.randint(1, 3), "speed": random.uniform(8, 34)}
    for _ in range(80)
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
    sound.set_volume(clamp(0.16 + strength / 650, 0.16, 0.85))
    sound.play()

def add_sparks(point, color, strength):
    count = clamp(int(strength / 22), 5, 22)
    for _ in range(count):
        sparks.append(Particle(point.x, point.y, color, speed=clamp(strength / 150, 0.5, 2.2), life=random.uniform(0.28, 0.75)))

# --- COLLISION PIPELINE MANIPULATION ---
def collision_handler(arbiter, _space, _data):
    global screen_shake
    strength = arbiter.total_impulse.length
    if strength < 5: return True

    point = arbiter.contact_point_set.points[0].point_a
    normal = arbiter.contact_point_set.normal
    color = (120, 190, 255)
    ball_shape = next((shape for shape in arbiter.shapes if shape.collision_type == BALL_COLLISION), None)
    
    if ball_shape:
        for ball in balls:
            if ball["shape"] == ball_shape:
                color = ball["color"]
                current_vel = ball_shape.body.velocity
                
                ball_shape.body.velocity = pymunk.Vec2d(
                    current_vel.x + random.uniform(-15, 15), 
                    current_vel.y + random.uniform(-5, 5)
                )

                if abs(normal.x) < 0.2:
                    ball["vertical_bounces"] += 1
                else:
                    ball["vertical_bounces"] = 0

                if ball["vertical_bounces"] >= 4:
                    direction = random.choice([-1, 1])
                    ball_shape.body.velocity = pymunk.Vec2d(current_vel.x + (direction * random.uniform(150, 300)), -100)
                    ball["vertical_bounces"] = 0 
                break

    play_impact_sound(strength)
    if strength > 50:
        add_sparks(point, lighten(color, 25), strength)
    if strength > 300:
        screen_shake = max(screen_shake, clamp((strength - 300) / 80, 0, 4))
        
    return True

def block_hit_handler(arbiter, _space, _data):
    global block_health, screen_shake
    strength = arbiter.total_impulse.length
    
    ball_shape = next((shape for shape in arbiter.shapes if shape.collision_type == BALL_COLLISION), None)
    if ball_shape:
        current_vel = ball_shape.body.velocity
        ball_shape.body.velocity = pymunk.Vec2d(
            current_vel.x + random.uniform(-20, 20), 
            current_vel.y + random.uniform(-10, 10)
        )

    if strength > 3 and block_health > 0:
        block_health -= 1
        screen_shake = max(screen_shake, 2.5) 
        point = arbiter.contact_point_set.points[0].point_a
        add_sparks(point, (255, 255, 255), 150)
        play_impact_sound(180)
        
    return True

def ball_to_ball_handler(arbiter, _space, _data):
    strength = arbiter.total_impulse.length
    if strength > 15:
        point = arbiter.contact_point_set.points[0].point_a
        play_impact_sound(strength * 0.5)
        add_sparks(point, (255, 255, 255), strength * 0.4)
    return True

# --- REGISTER COLLISION HANDLERS ---
space.on_collision(BALL_COLLISION, SLAB_COLLISION, post_solve=collision_handler)
space.on_collision(BALL_COLLISION, WALL_COLLISION, post_solve=collision_handler)
space.on_collision(BALL_COLLISION, BLOCK_COLLISION, post_solve=block_hit_handler)
space.on_collision(BALL_COLLISION, BALL_COLLISION, post_solve=ball_to_ball_handler)
space.on_collision(BALL_COLLISION, PISTON_COLLISION, post_solve=collision_handler)

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
        play_impact_sound(800)
        screen_shake = 7 
        for _ in range(50):
            add_sparks(pymunk.Vec2d(125, 700), (180, 230, 180), 300)

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

    # --- Piston Kinetic Movement Control ---
    if not winner_found and piston_body.position.y < PISTON_MAX_Y:
        piston_body.velocity = (0, PISTON_SPEED)
    else:
        piston_body.velocity = (0, 0)

    # --- Physics Step ---
    if physics_dt > 0:
        for _ in range(2):
            space.step(physics_dt / 2)
            
        for ball in balls:
            if not ball["winner"]:
                speed = ball["body"].velocity.length
                if speed > 550:
                    ball["body"].velocity = ball["body"].velocity.normalized() * 550
                elif speed < 40 and not winner_found:
                    ball["body"].apply_impulse_at_local_point((random.uniform(-30, 30), random.uniform(-30, 30)))

    # --- Visual Updates ---
    for particle in background_particles:
        particle["y"] += particle["speed"] * dt
        if particle["y"] > HEIGHT:
            particle["y"] = 0
            particle["x"] = random.randint(0, WIDTH)

    sparks = [particle for particle in sparks if particle.update(dt)]
    celebration_particles = [particle for particle in celebration_particles if particle.update(dt)]

    screen_shake = max(0, screen_shake - 35 * dt)
    shake_offset = (
        random.uniform(-screen_shake, screen_shake),
        random.uniform(-screen_shake, screen_shake),
    )

    # --- Drawing ---
    screen.blit(grid_surface, (int(shake_offset[0]), int(shake_offset[1])))
    path_rect = pygame.Rect(20 + shake_offset[0], 40 + shake_offset[1], 390, 690)
    pygame.draw.rect(screen, PATH_PURPLE, path_rect)

    for particle in background_particles:
        pygame.draw.circle(
            screen,
            (255, 100, 180, 100), 
            (int(particle["x"] + shake_offset[0]), int(particle["y"] + shake_offset[1])),
            particle["radius"],
        )

    pygame.draw.line(screen, (255, 0, 0), (20 + shake_offset[0], 40 + shake_offset[1]), (410 + shake_offset[0], 40 + shake_offset[1]), 2)

    for wall_rect in walls:
        wr = wall_rect.copy()
        wr.x += shake_offset[0]
        wr.y += shake_offset[1]
        pygame.draw.rect(screen, WALL_PURPLE, wr)
        for _ in range(15):
            rx = random.randint(wr.x, wr.right - 2)
            ry = random.randint(wr.y, wr.bottom - 2)
            pygame.draw.rect(screen, (100, 40, 140), (rx, ry, 2, 2))
        pygame.draw.rect(screen, (0, 0, 0), wr, 1)

    for seg in angled_walls:
        p2 = (int(seg.b.x + shake_offset[0]), int(seg.b.y + shake_offset[1]))
        radius = int(seg.radius)
        pygame.draw.line(screen, WALL_PURPLE, (int(seg.a.x + shake_offset[0]), int(seg.a.y + shake_offset[1])), p2, radius * 2)
        pygame.draw.circle(screen, WALL_PURPLE, (int(seg.a.x + shake_offset[0]), int(seg.a.y + shake_offset[1])), radius)
        pygame.draw.circle(screen, WALL_PURPLE, p2, radius)

    # --- Draw Descending Piston ---
    py = int(piston_body.position.y + shake_offset[1])
    px = int(piston_body.position.x + shake_offset[0] - PISTON_WIDTH / 2)
    piston_rect = pygame.Rect(px, int(py - PISTON_HEIGHT / 2), PISTON_WIDTH, PISTON_HEIGHT)
    pygame.draw.rect(screen, PISTON_COLOR, piston_rect)
    pygame.draw.rect(screen, (0, 0, 0), piston_rect, 2)
    for tx in range(px + 10, px + PISTON_WIDTH, 20):
        pygame.draw.line(screen, (150, 40, 40), (tx, piston_rect.top + 2), (tx + 5, piston_rect.bottom - 2), 2)

    finish_h = 60
    fz_rect = pygame.Rect(20 + shake_offset[0], 670 + shake_offset[1], 60, finish_h)
    pygame.draw.rect(screen, FINISH_GREEN, fz_rect)
    pygame.draw.rect(screen, (0, 0, 0), fz_rect, 2)
    
    sq = 15
    start_y = 670 + int(shake_offset[1])
    for y in range(start_y, start_y + 60, sq):
        color = (0, 0, 0) if ((y-start_y) // sq) % 2 == 0 else (255, 255, 255)
        pygame.draw.rect(screen, color, (80 + shake_offset[0], y, 15, sq))
        pygame.draw.rect(screen, (255, 255, 255) if color == (0,0,0) else (0,0,0), (95 + shake_offset[0], y, 15, sq))
    
    if block_active:
        block_rect = pygame.Rect(110 + shake_offset[0], 670 + shake_offset[1], 30, finish_h)
        pygame.draw.rect(screen, (180, 230, 180), block_rect)
        pygame.draw.rect(screen, (0, 0, 0), block_rect, 2)
        
        counter_txt = font_timer.render(str(block_health), True, (0, 0, 0))
        screen.blit(counter_txt, counter_txt.get_rect(center=block_rect.center))

    for turnstile in turnstiles:
        turnstile.draw(screen, shake_offset)

    for ball in balls:
        pos = ball["body"].position
        radius = ball["radius"]
        
        ball["trail"].append((pos.x, pos.y))
        if len(ball["trail"]) > 18:
            ball["trail"].pop(0)

        # Win Trigger verification condition (Health must be <= 0 AND ball inside the bounds)
        if not winner_found and block_health <= 0 and pos.x < 100 and pos.y > 670:
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
            trail_color = (*ball["color"], alpha)
            
            trail_surf = pygame.Surface((trail_radius * 2, trail_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, trail_color, (trail_radius, trail_radius), trail_radius)
            screen.blit(trail_surf, (int(trail_pos[0] + shake_offset[0] - trail_radius), int(trail_pos[1] + shake_offset[1] - trail_radius)))

        portal_light = clamp(pos.y / 730, 0, 1) 
        glow_color = tuple(clamp(int(ball["color"][i] + 120 * portal_light), 0, 255) for i in range(3))
        glow_radius = radius + 12
        ball_glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(ball_glow_surf, (*glow_color, 60), (glow_radius, glow_radius), glow_radius)
        screen.blit(ball_glow_surf, (int(pos.x + shake_offset[0] - glow_radius), int(pos.y + shake_offset[1] - glow_radius)))
        
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