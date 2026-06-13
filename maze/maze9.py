import math
import os
import random

import pygame
import pymunk

pygame.init()
pygame.mixer.init()

# --- Configuration ---
WIDTH = 600
HEIGHT = 800
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Physics Sandbox - The Anomaly Reactor")
clock = pygame.time.Clock()

# --- Sounds (Failsafe included) ---
bounce_sounds = []
try:
    # Try to load local sounds if you have them, otherwise it stays silent
    bounce_sounds.append(pygame.mixer.Sound("../sounds/sound.mp3"))
except:
    pass

def play_impact_sound(strength, high_pitch=False):
    if not bounce_sounds: return
    try:
        sound = bounce_sounds[0]
        sound.set_volume(clamp(0.1 + strength / 1000, 0.1, 1.0))
        sound.play()
    except:
        pass

# --- Physics Space ---
space = pymunk.Space()
# ZERO GLOBAL GRAVITY. The Black Hole handles it.
space.gravity = (0, 0)      
space.damping = 0.99 # Slight drag to prevent infinite acceleration        

# --- Collision Types ---
BALL_COLLISION = 1
WALL_COLLISION = 2
MINE_COLLISION = 3

# --- Colors (Neon Cyber-Core Theme) ---
VOID_BG = (8, 5, 12)            # Deep space purple/black
GRID_LINE = (20, 15, 30)
CYAN_NEON = (0, 255, 255)
MAGENTA_NEON = (255, 0, 255)
MINE_CORE = (255, 200, 255)
EVENT_HORIZON = (5, 0, 10)
BALL_COLORS = [(255, 255, 255), (0, 255, 255), (255, 0, 255), (255, 255, 0), (100, 255, 100)]

# --- Background Grid ---
grid_surface = pygame.Surface((WIDTH, HEIGHT))
grid_surface.fill(VOID_BG)
sz = 30
for x in range(0, WIDTH, sz):
    pygame.draw.line(grid_surface, GRID_LINE, (x, 0), (x, HEIGHT))
for y in range(0, HEIGHT, sz):
    pygame.draw.line(grid_surface, GRID_LINE, (0, y), (WIDTH, y))

# --- Helpers ---
def clamp(value, low, high):
    return max(low, min(high, value))

class Particle:
    def __init__(self, x, y, color, speed=1.0, life=1.0, radius=None):
        angle = random.uniform(0, math.tau)
        power = random.uniform(50, 300) * speed
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * power
        self.vy = math.sin(angle) * power
        self.color = color
        self.life = life
        self.max_life = life
        self.radius = radius if radius is not None else random.uniform(2, 6)

    def update(self, dt):
        self.life -= dt
        # Particles drag quickly in the void
        self.vx *= 0.95
        self.vy *= 0.95
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

def create_angled_wall(p1, p2, thickness=10):
    body = pymunk.Body(body_type=pymunk.Body.STATIC)
    shape = pymunk.Segment(body, p1, p2, thickness)
    shape.friction = 0.2
    shape.elasticity = 0.8  
    shape.collision_type = WALL_COLLISION
    space.add(body, shape)
    return shape

def create_repulsor_mine(x, y, radius=18):
    body = pymunk.Body(body_type=pymunk.Body.STATIC)
    body.position = (x, y)
    shape = pymunk.Circle(body, radius)
    # 2.5 Elasticity creates a multiplied kinetic explosion on impact
    shape.elasticity = 2.5 
    shape.friction = 0.1
    shape.collision_type = MINE_COLLISION
    space.add(body, shape)
    return {"pos": (x, y), "radius": radius, "flash": 0}

# --- ARCHITECTURE ---
angled_walls = []
mines = []
BH_POS = pymunk.Vec2d(WIDTH // 2, HEIGHT // 2)

# Floating Asteroid Deflectors
angled_walls.append(create_angled_wall((100, 150), (250, 100), 8))
angled_walls.append(create_angled_wall((500, 150), (350, 100), 8))
angled_walls.append(create_angled_wall((100, 650), (250, 700), 8))
angled_walls.append(create_angled_wall((500, 650), (350, 700), 8))

# Ring of Repulsor Mines
mine_radius = 200
for i in range(6):
    angle = i * (math.tau / 6)
    mx = BH_POS.x + math.cos(angle) * mine_radius
    my = BH_POS.y + math.sin(angle) * mine_radius
    mines.append(create_repulsor_mine(mx, my))

# --- Setup Balls ---
balls = []
for i in range(25): # Drop 25 balls into the chaos
    mass = 1
    radius = 8
    moment = pymunk.moment_for_circle(mass, 0, radius)
    body = pymunk.Body(mass, moment)
    
    # Spawn in a ring around the edges
    spawn_angle = random.uniform(0, math.tau)
    body.position = (BH_POS.x + math.cos(spawn_angle) * 350, BH_POS.y + math.sin(spawn_angle) * 350)
    
    # Give them an initial tangential velocity to start an orbit
    tangent = spawn_angle + math.pi/2
    speed = random.uniform(100, 300)
    body.velocity = (math.cos(tangent) * speed, math.sin(tangent) * speed)
    
    shape = pymunk.Circle(body, radius)
    shape.elasticity = 0.9  
    shape.friction = 0.1 
    shape.collision_type = BALL_COLLISION
    space.add(body, shape)
    
    color = random.choice(BALL_COLORS)
    balls.append({"body": body, "shape": shape, "radius": radius, "color": color, "trail": []})

# --- Visuals & Audio ---
sparks = []
screen_shake = 0
elapsed = 0

# --- COLLISION HANDLERS ---
def mine_hit_handler(arbiter, _space, _data):
    global screen_shake
    strength = arbiter.total_impulse.length
    if strength < 10: return True

    point = arbiter.contact_point_set.points[0].point_a
    
    # Flash the mine
    for m in mines:
        if math.hypot(m["pos"][0] - point.x, m["pos"][1] - point.y) < m["radius"] * 3:
            m["flash"] = 1.0

    play_impact_sound(strength, high_pitch=True)
    add_sparks(point, MAGENTA_NEON, strength * 1.5)
    
    if strength > 300: 
        screen_shake = max(screen_shake, clamp((strength - 300) / 50, 0, 8))
    return True

def wall_hit_handler(arbiter, _space, _data):
    strength = arbiter.total_impulse.length
    if strength > 50:
        point = arbiter.contact_point_set.points[0].point_a
        play_impact_sound(strength)
        add_sparks(point, CYAN_NEON, strength * 0.5)
    return True

space.on_collision(BALL_COLLISION, MINE_COLLISION, post_solve=mine_hit_handler)
space.on_collision(BALL_COLLISION, WALL_COLLISION, post_solve=wall_hit_handler)

def add_sparks(point, color, strength):
    count = clamp(int(strength / 20), 5, 30)
    for _ in range(count):
        sparks.append(Particle(point.x, point.y, color, speed=clamp(strength / 100, 0.5, 3.0), life=random.uniform(0.2, 0.6)))

# --- Main Loop ---
running = True

while running:
    frame_dt = clock.tick(FPS) / 1000
    dt = min(frame_dt, 1 / 30)
    elapsed += dt

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False

    # --- CUSTOM PHYSICS: THE BLACK HOLE ---
    G_FORCE = 6000000 # Tune this to change gravity strength
    
    for ball in balls:
        pos = ball["body"].position
        dist_sq = BH_POS.get_dist_sqrd(pos)
        
        # Apply attractive force if outside the event horizon
        if dist_sq > 25**2:
            force_mag = G_FORCE / dist_sq
            direction = (BH_POS - pos).normalized()
            ball["body"].apply_force_at_world_point(direction * force_mag, pos)
            
        # --- CUSTOM PHYSICS: WARP PORTALS ---
        # If a ball flies off screen, wrap it to the other side
        if pos.x < -20: ball["body"].position = (WIDTH + 15, pos.y)
        elif pos.x > WIDTH + 20: ball["body"].position = (-15, pos.y)
        
        if pos.y < -20: ball["body"].position = (pos.x, HEIGHT + 15)
        elif pos.y > HEIGHT + 20: ball["body"].position = (pos.x, -15)

        # Speed limit so physics don't break
        if ball["body"].velocity.length > 1200:
            ball["body"].velocity = ball["body"].velocity.normalized() * 1200

    # --- Physics Step ---
    for _ in range(2): space.step(dt / 2)

    # --- Visual Updates ---
    sparks = [particle for particle in sparks if particle.update(dt)]
    for m in mines: m["flash"] = max(0, m["flash"] - dt * 2)

    screen_shake = max(0, screen_shake - 30 * dt)
    shake = (random.uniform(-screen_shake, screen_shake), random.uniform(-screen_shake, screen_shake))

    # --- Drawing ---
    screen.blit(grid_surface, (int(shake[0]), int(shake[1])))

    # Draw Asteroid Deflectors
    for seg in angled_walls:
        p1 = (int(seg.a.x + shake[0]), int(seg.a.y + shake[1]))
        p2 = (int(seg.b.x + shake[0]), int(seg.b.y + shake[1]))
        radius = int(seg.radius)
        pygame.draw.line(screen, CYAN_NEON, p1, p2, radius * 2)
        pygame.draw.circle(screen, CYAN_NEON, p1, radius)
        pygame.draw.circle(screen, CYAN_NEON, p2, radius)
        # Inner core
        pygame.draw.line(screen, (255, 255, 255), p1, p2, 2)

    # Draw Repulsor Mines
    for m in mines:
        mx = int(m["pos"][0] + shake[0])
        my = int(m["pos"][1] + shake[1])
        mr = m["radius"]
        
        # Flash aura
        if m["flash"] > 0:
            glow_r = int(mr + 20 * m["flash"])
            surf = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*MAGENTA_NEON, int(150 * m["flash"])), (glow_r, glow_r), glow_r)
            screen.blit(surf, (mx - glow_r, my - glow_r))
            
        pygame.draw.circle(screen, MAGENTA_NEON, (mx, my), mr)
        pygame.draw.circle(screen, MINE_CORE, (mx, my), int(mr * 0.6))

    # Draw Black Hole (The Anomaly)
    bhx = int(BH_POS.x + shake[0])
    bhy = int(BH_POS.y + shake[1])
    
    # Pulsing accretion disk
    pulse = math.sin(elapsed * 5) * 5
    pygame.draw.circle(screen, (30, 0, 50), (bhx, bhy), int(45 + pulse))
    pygame.draw.circle(screen, MAGENTA_NEON, (bhx, bhy), int(40 + pulse), 2)
    pygame.draw.circle(screen, CYAN_NEON, (bhx, bhy), 30, 1)
    pygame.draw.circle(screen, EVENT_HORIZON, (bhx, bhy), 25)

    # Draw Balls
    for ball in balls:
        pos = ball["body"].position
        radius = ball["radius"]
        
        ball["trail"].append((pos.x, pos.y))
        if len(ball["trail"]) > 10: ball["trail"].pop(0)

        for index, trail_pos in enumerate(ball["trail"]):
            alpha = int(25 + index * 15)
            trail_radius = max(1, int(radius * (index + 1) / len(ball["trail"])))
            trail_surf = pygame.Surface((trail_radius * 2, trail_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (*ball["color"], alpha), (trail_radius, trail_radius), trail_radius)
            screen.blit(trail_surf, (int(trail_pos[0] + shake[0] - trail_radius), int(trail_pos[1] + shake[1] - trail_radius)))

        pygame.draw.circle(screen, ball["color"], (int(pos.x + shake[0]), int(pos.y + shake[1])), radius)

    # Draw Sparks
    for particle in sparks:
        particle.draw(screen, shake)

    pygame.display.flip()

pygame.quit()