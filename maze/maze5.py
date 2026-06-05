import math
import random
import pygame
import pymunk

pygame.init()

# --- Configuration ---
WIDTH = 430
HEIGHT = 700
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Square Spiral - Advancing Blue Flood")
clock = pygame.time.Clock()

# --- Physics Space ---
space = pymunk.Space()
# EXACTLY ZERO GRAVITY. Top-down physics view.
space.gravity = (0, 0)
space.damping = 0.95 

WALL_COLLISION = 1
BLOCK_COLLISION = 2
FLOOD_COLLISION = 3

# --- Colors ---
BG_SAND = (240, 215, 160)
WALL_ORANGE = (245, 155, 45)
FLOOD_BLUE = (30, 80, 255)
FINISH_GREEN = (110, 215, 90)

COMPETITORS = [
    {"color": (220, 40, 40)},   # Red
    {"color": (240, 220, 40)},  # Yellow
    {"color": (40, 140, 40)},   # Green
    {"color": (40, 40, 220)},   # Blue
]

# --- Static Maze Generation ---
walls = []
def create_wall(x, y, w, h):
    body = pymunk.Body(body_type=pymunk.Body.STATIC)
    body.position = (x + w / 2, y + h / 2)
    shape = pymunk.Poly.create_box(body, (w, h), radius=1)
    shape.friction = 0.2
    shape.elasticity = 0.9 
    shape.collision_type = WALL_COLLISION
    space.add(body, shape)
    walls.append(pygame.Rect(x, y, w, h))

# Building the precise continuous square spiral
# Corridor Width = 40, Wall Thickness = 20
create_wall(30, 90, 260, 20)   # Top Outer (Leaves a 40px gap on the right for entry!)
create_wall(330, 90, 20, 460)  # Right Outer
create_wall(30, 530, 320, 20)  # Bottom Outer
create_wall(30, 150, 20, 400)  # Left Outer

create_wall(90, 150, 200, 20)  # Top Inner 1
create_wall(270, 150, 20, 340) # Right Inner 1
create_wall(90, 470, 200, 20)  # Bottom Inner 1
create_wall(90, 210, 20, 280)  # Left Inner 1

create_wall(150, 210, 80, 20)  # Top Inner 2
create_wall(210, 210, 20, 240) # Right Inner 2
create_wall(150, 410, 80, 20)  # Bottom Inner 2
create_wall(150, 270, 20, 160) # Left Inner 2
create_wall(150, 270, 60, 20)  # Center Dead-end Cap

# --- The "Blue Flood" Manager ---
# This system slides a massive kinematic wall through each corridor sequentially.
class FloodManager:
    def __init__(self):
        # Define the exact corridors the flood needs to travel through in order
        # Format: (Direction, Visual_Rect, Start_Coordinate, End_Coordinate)
        self.stages = [
            ('D', pygame.Rect(290, 50, 40, 480), 50, 530),   # 1. Down right side
            ('L', pygame.Rect(50, 490, 280, 40), 330, 50),   # 2. Left along bottom
            ('U', pygame.Rect(50, 170, 40, 320), 490, 170),  # 3. Up left side
            ('R', pygame.Rect(90, 170, 180, 40), 50, 270),   # 4. Right along top inner
            ('D', pygame.Rect(230, 210, 40, 260), 170, 470), # 5. Down right inner
            ('L', pygame.Rect(110, 430, 160, 40), 270, 110), # 6. Left along bottom inner
            ('U', pygame.Rect(110, 230, 40, 200), 430, 230), # 7. Up left inner
            ('R', pygame.Rect(150, 230, 40, 40), 110, 190)   # 8. Right into center finish
        ]
        self.speed = 60 # Pixels per second
        self.current_stage = 0
        self.front = self.stages[0][2]
        
        self.piston_body = None
        self.piston_shape = None
        self.static_fills = [] # Stores completed corridors
        self.setup_piston()

    def setup_piston(self):
        if self.piston_body:
            space.remove(self.piston_body, self.piston_shape)
            
        if self.current_stage >= len(self.stages):
            return

        # Create a massive 1000x1000 kinematic block. We only care about its flat front edge pushing the balls.
        self.piston_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.piston_shape = pymunk.Poly.create_box(self.piston_body, (1000, 1000))
        self.piston_shape.friction = 0.0
        self.piston_shape.elasticity = 1.0 # Bouncy wall!
        self.piston_shape.collision_type = FLOOD_COLLISION
        space.add(self.piston_body, self.piston_shape)
        self.update_piston_position()

    def update_piston_position(self):
        if not self.piston_body: return
        direction, rect, _, _ = self.stages[self.current_stage]
        
        # Align the 1000x1000 box so its front edge perfectly matches the 'self.front' coordinate
        if direction == 'D':
            self.piston_body.position = (rect.centerx, self.front - 500)
            self.piston_body.velocity = (0, self.speed)
        elif direction == 'L':
            self.piston_body.position = (self.front + 500, rect.centery)
            self.piston_body.velocity = (-self.speed, 0)
        elif direction == 'U':
            self.piston_body.position = (rect.centerx, self.front + 500)
            self.piston_body.velocity = (0, -self.speed)
        elif direction == 'R':
            self.piston_body.position = (self.front - 500, rect.centery)
            self.piston_body.velocity = (self.speed, 0)

    def update(self, dt):
        if self.current_stage >= len(self.stages): return
        
        direction, rect, start, target = self.stages[self.current_stage]
        
        # Advance the front line
        if direction in ['D', 'R']:
            self.front += self.speed * dt
            if self.front >= target:
                self.front = target
                self.advance_stage(rect)
        else: # 'L', 'U'
            self.front -= self.speed * dt
            if self.front <= target:
                self.front = target
                self.advance_stage(rect)
                
        self.update_piston_position()

    def advance_stage(self, rect):
        # Lock in the completely filled corridor as a static object so balls can never slip backwards
        static_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        static_body.position = (rect.centerx, rect.centery)
        static_shape = pymunk.Poly.create_box(static_body, (rect.width, rect.height))
        static_shape.elasticity = 1.0
        space.add(static_body, static_shape)
        self.static_fills.append(rect)
        
        self.current_stage += 1
        if self.current_stage < len(self.stages):
            self.front = self.stages[self.current_stage][2]
        self.setup_piston()

    def draw(self, surface):
        # Draw all fully flooded corridors
        for r in self.static_fills:
            pygame.draw.rect(surface, FLOOD_BLUE, r)
            
        # Draw the currently growing flood
        if self.current_stage < len(self.stages):
            direction, rect, start, _ = self.stages[self.current_stage]
            partial_rect = rect.copy()
            
            if direction == 'D':
                partial_rect.height = self.front - rect.top
            elif direction == 'L':
                partial_rect.width = rect.right - self.front
                partial_rect.left = self.front
            elif direction == 'U':
                partial_rect.height = rect.bottom - self.front
                partial_rect.top = self.front
            elif direction == 'R':
                partial_rect.width = self.front - rect.left
                
            pygame.draw.rect(surface, FLOOD_BLUE, partial_rect)

# --- Initialize Blocks ---
blocks = []
spawn_y = 40
for comp in COMPETITORS:
    size = 18
    mass = 1
    moment = pymunk.moment_for_box(mass, (size, size))
    body = pymunk.Body(mass, moment)
    
    # Spawn in the top-right entry gap
    body.position = (random.uniform(295, 325), spawn_y)
    body.velocity = (random.uniform(-100, 100), random.uniform(50, 150))
    spawn_y -= 30 
    
    shape = pymunk.Poly.create_box(body, (size, size))
    shape.elasticity = 1.05 # highly bouncy
    shape.friction = 0.1
    shape.collision_type = BLOCK_COLLISION
    space.add(body, shape)
    
    blocks.append({"body": body, "size": size, "color": comp["color"], "trail": []})

flood_system = FloodManager()

# --- Main Loop ---
running = True

while running:
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 1. Update the Advancing Flood Wall
    flood_system.update(dt)

    # 2. Physics Step
    space.step(dt)

    # 3. Block Logic (Maintain kinetic energy since there's zero gravity)
    for b in blocks:
        speed = b["body"].velocity.length
        # Add random nudges if they get stuck or too slow, keeping the chaos alive
        if speed < 80:
            b["body"].apply_impulse_at_local_point((random.uniform(-30, 30), random.uniform(-30, 30)))
        # Speed limit
        elif speed > 400:
            b["body"].velocity = b["body"].velocity.normalized() * 400
            
        b["trail"].append((b["body"].position.x, b["body"].position.y))
        if len(b["trail"]) > 15:
            b["trail"].pop(0)

    # --- Drawing ---
    screen.fill((200, 200, 200))
    
    # Background Grid Pattern
    tile_size = 15
    for x in range(0, WIDTH, tile_size):
        for y in range(0, HEIGHT, tile_size):
            color = (80, 120, 200) if ((x // tile_size) + (y // tile_size)) % 2 == 0 else (180, 180, 80)
            pygame.draw.rect(screen, color, (x, y, tile_size, tile_size))
            pygame.draw.rect(screen, (50, 50, 50), (x, y, tile_size, tile_size), 1)

    # Main Sand Area
    sand_rect = pygame.Rect(10, 70, 360, 500)
    pygame.draw.rect(screen, BG_SAND, sand_rect)
    pygame.draw.rect(screen, (0, 0, 0), sand_rect, 2)

    # Watermark
    font = pygame.font.SysFont("courier", 16, bold=True)
    watermark = font.render("@simulando2d", True, (180, 160, 130))
    screen.blit(watermark, (130, 490))

    # Draw the Advancing Blue Flood
    flood_system.draw(screen)

    # Draw Center Finish Line (Green + Checkers)
    finish_rect = pygame.Rect(190, 230, 20, 40)
    pygame.draw.rect(screen, FINISH_GREEN, finish_rect)
    for cx in range(190, 210, 5):
        for cy in range(230, 240, 5):
            color = (0, 0, 0) if ((cx // 5) + (cy // 5)) % 2 == 0 else (255, 255, 255)
            pygame.draw.rect(screen, color, (cx, cy, 5, 5))

    # Draw Static Walls
    for wall in walls:
        pygame.draw.rect(screen, WALL_ORANGE, wall)
        pygame.draw.rect(screen, (0, 0, 0), wall, 1)

    # Draw Competitor Blocks & Trails
    for b in blocks:
        color = b["color"]
        size = b["size"]
        pos = b["body"].position
        angle = b["body"].angle

        # Draw Fading Trail
        if len(b["trail"]) > 2:
            for i in range(len(b["trail"]) - 1):
                alpha = int(255 * (i / len(b["trail"])))
                trail_color = (*color, alpha)
                trail_radius = max(2, int((size/2) * (i / len(b["trail"]))))
                
                t_surf = pygame.Surface((trail_radius*2, trail_radius*2), pygame.SRCALPHA)
                pygame.draw.rect(t_surf, trail_color, (0, 0, trail_radius*2, trail_radius*2))
                screen.blit(t_surf, (b["trail"][i][0] - trail_radius, b["trail"][i][1] - trail_radius))

        # Draw Physics Square (Rotated)
        poly = pygame.Surface((size + 2, size + 2), pygame.SRCALPHA)
        pygame.draw.rect(poly, color, (1, 1, size, size))
        pygame.draw.rect(poly, (0, 0, 0), (1, 1, size, size), 2)
        
        rotated_poly = pygame.transform.rotate(poly, math.degrees(-angle))
        rect = rotated_poly.get_rect(center=(int(pos.x), int(pos.y)))
        screen.blit(rotated_poly, rect)

    pygame.display.flip()

pygame.quit()