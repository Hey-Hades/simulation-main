import math
import random
import pygame
import pymunk

# --- Configuration ---
WIDTH = 800
HEIGHT = 800
FPS = 60

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Celestial Slingshot")
clock = pygame.time.Clock()

# --- Physics Space ---
space = pymunk.Space()
space.gravity = (0, 0) # Zero global gravity!
space.damping = 0.99   # Very slight damping to simulate space dust

# Collision Types
WALL_COLLISION = 1
PLANET_COLLISION = 2
COMET_COLLISION = 3
ASTEROID_COLLISION = 4
BLACK_HOLE_COLLISION = 5

# --- Aesthetics ---
BG_COLOR = (10, 12, 20)
STARS = [(random.randint(0, WIDTH), random.randint(0, HEIGHT), random.uniform(0.5, 2)) for _ in range(150)]
PLANET_COLORS = [(70, 130, 180), (180, 70, 70), (70, 180, 120), (180, 150, 70)]
COMET_COLORS = [(255, 80, 80), (80, 255, 80), (80, 80, 255), (255, 255, 80), (255, 80, 255)]

# --- Game Entities ---
planets = []
comets = []
asteroids = []
winner = None

def create_boundaries():
    # Keep things inside the screen
    thickness = 50
    static_lines = [
        pymunk.Segment(space.static_body, (-thickness, -thickness), (WIDTH+thickness, -thickness), thickness),
        pymunk.Segment(space.static_body, (WIDTH+thickness, -thickness), (WIDTH+thickness, HEIGHT+thickness), thickness),
        pymunk.Segment(space.static_body, (WIDTH+thickness, HEIGHT+thickness), (-thickness, HEIGHT+thickness), thickness),
        pymunk.Segment(space.static_body, (-thickness, HEIGHT+thickness), (-thickness, -thickness), thickness)
    ]
    for line in static_lines:
        line.elasticity = 0.8
        line.friction = 0.5
        line.collision_type = WALL_COLLISION
    space.add(*static_lines)

def setup_cosmos():
    global planets, comets, asteroids, winner
    
    # Clear existing bodies (Updated logic for sets/dicts)
    for c in comets: space.remove(c["body"], c["shape"])
    for a in asteroids: space.remove(a["body"], a["shape"])
    for p in planets: space.remove(p["body"], p["shape"])
    comets.clear()
    asteroids.clear()
    planets.clear()
    winner = None

    # 1. Create Planets
    planet_positions = [(200, 200), (600, 200), (200, 600), (600, 600)]
    for i, pos in enumerate(planet_positions):
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = pos
        radius = 40
        shape = pymunk.Circle(body, radius)
        shape.elasticity = 0.5
        shape.collision_type = PLANET_COLLISION
        space.add(body, shape)
        planets.append({"body": body, "shape": shape, "radius": radius, "color": PLANET_COLORS[i]})

    # 2. Create Asteroid Belt
    for _ in range(30):
        mass = 0.5
        radius = random.uniform(4, 10)
        moment = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, moment)
        
        # Place roughly in a ring around the center
        angle = random.uniform(0, math.tau)
        dist = random.uniform(150, 350)
        body.position = (WIDTH/2 + math.cos(angle)*dist, HEIGHT/2 + math.sin(angle)*dist)
        
        shape = pymunk.Circle(body, radius)
        shape.elasticity = 0.6
        shape.friction = 0.3
        shape.collision_type = ASTEROID_COLLISION
        
        # Add to space and our dictionary list (Updated)
        space.add(body, shape)
        asteroids.append({"body": body, "shape": shape, "radius": radius})

def launch_comets():
    global comets
    if comets: return # Don't launch if already flying
    
    start_positions = [
        (100, 100, 300, 50),   # x, y, vx, vy
        (700, 100, -50, 300),
        (100, 700, 50, -300),
        (700, 700, -300, -50),
        (400, 50, 400, 0)
    ]
    
    for i, (x, y, vx, vy) in enumerate(start_positions):
        mass = 1.5
        radius = 8
        moment = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, moment)
        body.position = (x, y)
        body.velocity = (vx, vy)
        
        shape = pymunk.Circle(body, radius)
        shape.elasticity = 0.9
        shape.friction = 0.1
        shape.collision_type = COMET_COLLISION
        space.add(body, shape)
        
        comets.append({
            "body": body, 
            "shape": shape, 
            "radius": radius, 
            "color": COMET_COLORS[i],
            "trail": [],
            "finished": False
        })

def apply_custom_gravity():
    G_PLANET = 8000000  # Gravitational constant for planets
    G_BLACK_HOLE = 1500000 # Gentle pull toward the center
    
    bh_pos = pymunk.Vec2d(WIDTH/2, HEIGHT/2)
    
    for comet in comets:
        if comet["finished"]: continue
        
        c_pos = comet["body"].position
        
        # 1. Pull toward Planets
        for planet in planets:
            p_pos = planet["body"].position
            # FIX: Use get_dist_sqrd() instead of get_dist_sq()
            dist_sq = c_pos.get_dist_sqrd(p_pos)
            
            # Prevent infinite force if they overlap
            if dist_sq > (planet["radius"] + comet["radius"])**2:
                force_mag = G_PLANET / dist_sq
                direction = (p_pos - c_pos).normalized()
                comet["body"].apply_force_at_local_point(direction * force_mag, (0, 0))
                
        # 2. Pull toward Black Hole
        # FIX: Use get_dist_sqrd() here too
        bh_dist_sq = c_pos.get_dist_sqrd(bh_pos)
        if bh_dist_sq > 400: # Don't apply if it's already basically inside
            force_mag = G_BLACK_HOLE / bh_dist_sq
            direction = (bh_pos - c_pos).normalized()
            comet["body"].apply_force_at_local_point(direction * force_mag, (0, 0))
            
        # Optional: Speed limit so they don't break the physics engine
        MAX_SPEED = 600
        if comet["body"].velocity.length > MAX_SPEED:
            comet["body"].velocity = comet["body"].velocity.normalized() * MAX_SPEED
# --- Setup ---
create_boundaries()
setup_cosmos()
font = pygame.font.SysFont("georgia", 48, bold=True)
small_font = pygame.font.SysFont("georgia", 18)

# --- Main Loop ---
running = True
while running:
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                launch_comets()
            elif event.key == pygame.K_r:
                setup_cosmos()

    # --- Physics Step ---
    apply_custom_gravity()
    space.step(dt)
    
    # Check Win Condition (Black hole logic)
    bh_pos = pymunk.Vec2d(WIDTH/2, HEIGHT/2)
    for comet in comets:
        if not comet["finished"]:
            if comet["body"].position.get_distance(bh_pos) < 30:
                comet["finished"] = True
                comet["body"].velocity = (0,0)
                if not winner:
                    winner = comet["color"]

    # --- Rendering ---
    screen.fill(BG_COLOR)
    
    # Draw Stars
    for sx, sy, sr in STARS:
        # Twinkle effect
        if random.random() < 0.05: sr = random.uniform(0.5, 3)
        pygame.draw.circle(screen, (150, 150, 180), (int(sx), int(sy)), sr)

    # Draw Asteroids (Updated to use dictionary keys)
    for ast in asteroids:
        pos = ast["body"].position
        pygame.draw.circle(screen, (120, 120, 120), (int(pos.x), int(pos.y)), int(ast["radius"]))

    # Draw Planets (with glowing halos)
    for planet in planets:
        pos = planet["body"].position
        r = planet["radius"]
        color = planet["color"]
        
        # Halo
        halo_surf = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
        pygame.draw.circle(halo_surf, (*color, 30), (r*2, r*2), r*1.8)
        screen.blit(halo_surf, (pos.x - r*2, pos.y - r*2))
        
        # Solid Planet
        pygame.draw.circle(screen, color, (int(pos.x), int(pos.y)), r)
        
    # Draw Black Hole
    bh_center = (WIDTH//2, HEIGHT//2)
    pygame.draw.circle(screen, (20, 0, 40), bh_center, 40)
    pygame.draw.circle(screen, (80, 40, 150), bh_center, 40, 3) # Event horizon
    pygame.draw.circle(screen, (0, 0, 0), bh_center, 30)

    # Draw Comets & Trails
    for comet in comets:
        pos = comet["body"].position
        
        if not comet["finished"]:
            comet["trail"].append((pos.x, pos.y))
            if len(comet["trail"]) > 30:
                comet["trail"].pop(0)
                
        # Draw Trail
        for i, (tx, ty) in enumerate(comet["trail"]):
            alpha = int(255 * (i / len(comet["trail"])))
            radius = max(1, int(comet["radius"] * (i / len(comet["trail"]))))
            
            trail_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (*comet["color"], alpha), (radius, radius), radius)
            screen.blit(trail_surf, (tx - radius, ty - radius))
            
        # Draw Comet Core
        if not comet["finished"]:
            pygame.draw.circle(screen, (255, 255, 255), (int(pos.x), int(pos.y)), comet["radius"])
            pygame.draw.circle(screen, comet["color"], (int(pos.x), int(pos.y)), comet["radius"]+2, 2)

    # Draw UI
    if winner:
        txt = font.render("WE HAVE A WINNER!", True, winner)
        shadow = font.render("WE HAVE A WINNER!", True, (0, 0, 0))
        rect = txt.get_rect(center=(WIDTH//2, HEIGHT//2 - 100))
        screen.blit(shadow, (rect.x + 2, rect.y + 2))
        screen.blit(txt, rect)
        
    instructions = small_font.render("SPACE to Launch | R to Reset", True, (200, 200, 200))
    screen.blit(instructions, (20, 20))

    pygame.display.flip()

pygame.quit()