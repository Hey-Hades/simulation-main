import math
import os
import random

import pygame
import pymunk

pygame.init()
pygame.mixer.init()

WIDTH = 430
HEIGHT = 800
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pymunk Portal Piston Race")
clock = pygame.time.Clock()

try:
    pygame.mixer.music.load("sounds/viacheslavstarostin-gaming-game-video-game-music-474517.mp3")
    pygame.mixer.music.set_volume(0.25)
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

space = pymunk.Space()
space.gravity = (0, 155)
space.damping = 0.99 

BALL_COLLISION = 1
WALL_COLLISION = 2
PLATFORM_COLLISION = 3

WIN_Y = 104 

grid_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

for x in range(0, WIDTH, 40):
    pygame.draw.line(grid_surface, (18, 24, 45, 75), (x, 0), (x, HEIGHT))
for y in range(0, HEIGHT, 40):
    pygame.draw.line(grid_surface, (18, 24, 45, 75), (0, y), (WIDTH, y))


def clamp(value, low, high):
    return max(low, min(high, value))


def mix(a, b, t):
    return clamp(int(a + (b - a) * t), 0, 255)


def draw_gradient(surface, elapsed):
    top = (
        255 - int(10 * math.sin(elapsed * 0.35)),
        150 + int(20 * math.sin(elapsed * 0.27 + 1.4)),
        255 - int(12 * math.sin(elapsed * 0.31 + 2.2)),
    )
    bottom = (
        255 - int(16 * math.sin(elapsed * 0.23 + 0.5)),
        180 + int(30 * math.sin(elapsed * 0.41)),
        255 - int(22 * math.sin(elapsed * 0.19 + 1.1)),
    )
    for y in range(HEIGHT):
        t = y / HEIGHT
        pygame.draw.line(
            surface,
            (mix(top[0], bottom[0], t), mix(top[1], bottom[1], t), mix(top[2], bottom[2], t)),
            (0, y),
            (WIDTH, y),
        )


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


class MovingPlatform:
    def __init__(self, y, gap_size, speed, phase, color):
        self.y = y
        self.gap_size = gap_size
        self.base_speed = speed
        self.phase = phase
        self.color = color
        self.body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)

        self.part_width = WIDTH
        self.height = 30

        left_verts = [
            (-self.part_width - gap_size/2, -self.height/2),
            (-gap_size/2, -self.height/2),
            (-gap_size/2, self.height/2),
            (-self.part_width - gap_size/2, self.height/2)
        ]
        right_verts = [
            (gap_size/2, -self.height/2),
            (self.part_width + gap_size/2, -self.height/2),
            (self.part_width + gap_size/2, self.height/2),
            (gap_size/2, self.height/2)
        ]

        self.shape_left = pymunk.Poly(self.body, left_verts)
        self.shape_right = pymunk.Poly(self.body, right_verts)

        for shape in (self.shape_left, self.shape_right):
            shape.elasticity = 1.05
            shape.friction = 0.2
            shape.collision_type = PLATFORM_COLLISION

        self.last_pos = pymunk.Vec2d(WIDTH / 2, y)
        self.body.position = self.last_pos
        space.add(self.body, self.shape_left, self.shape_right)

    def update(self, elapsed, difficulty, dt):
        max_offset = (WIDTH / 2) - (self.gap_size / 2) - 15
        wave = math.sin(elapsed * self.base_speed * difficulty + self.phase)
        x_offset = wave * max_offset

        new_pos = pymunk.Vec2d(WIDTH / 2 + x_offset, self.y)
        self.body.velocity = (new_pos - self.last_pos) / max(dt, 0.0001)
        self.body.position = new_pos
        self.last_pos = new_pos

    def draw(self, surface, offset, elapsed):
        x = self.body.position.x + offset[0]
        y = self.body.position.y + offset[1]

        rect_left = pygame.Rect(0, 0, self.part_width, self.height)
        rect_left.center = (int(x - self.part_width / 2 - self.gap_size / 2), int(y))
        pygame.draw.rect(surface, self.color, rect_left)
        pygame.draw.rect(surface, (0, 0, 0), rect_left, 2) 

        rect_right = pygame.Rect(0, 0, self.part_width, self.height)
        rect_right.center = (int(x + self.part_width / 2 + self.gap_size / 2), int(y))
        pygame.draw.rect(surface, self.color, rect_right)
        pygame.draw.rect(surface, (0, 0, 0), rect_right, 2)


class RisingFloor:
    def __init__(self, start_y, speed, color):
        self.start_y = start_y
        self.speed = speed
        self.color = color
        self.height = 200 
        self.body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.shape = pymunk.Poly.create_box(self.body, (WIDTH + 10, self.height))
        self.shape.elasticity = 1.05
        self.shape.friction = 0.5
        self.shape.collision_type = WALL_COLLISION
        self.last_pos = pymunk.Vec2d(WIDTH / 2, start_y)
        self.body.position = self.last_pos
        space.add(self.body, self.shape)

    def update(self, elapsed, dt):
        delay = 5.0
        if elapsed > delay:
            target_y = max(WIN_Y + self.height/2 + 20, self.start_y - self.speed * (elapsed - delay))
            new_pos = pymunk.Vec2d(WIDTH / 2, target_y)
            self.body.velocity = (new_pos - self.last_pos) / max(dt, 0.0001)
            self.body.position = new_pos
            self.last_pos = new_pos

    def draw(self, surface, offset, elapsed):
        x = self.body.position.x + offset[0]
        y = self.body.position.y + offset[1]
        rect = pygame.Rect(0, 0, WIDTH, self.height)
        rect.center = (int(x), int(y))
        
        glow_surf = pygame.Surface((WIDTH, 30), pygame.SRCALPHA)
        pulse = 40 + abs(math.sin(elapsed * 5)) * 120
        pygame.draw.rect(glow_surf, (*self.color, int(pulse)), glow_surf.get_rect())
        surface.blit(glow_surf, (0, rect.top - 30))

        pygame.draw.rect(surface, (clamp(self.color[0]-80, 0, 255), 10, 25), rect)
        pygame.draw.rect(surface, self.color, rect, width=4)
        
        for i in range(-100, WIDTH, 50):
            offset_x = (elapsed * 45) % 50
            pygame.draw.line(surface, (*self.color, 150), (i + offset_x, rect.top), (i + offset_x - 30, rect.bottom), 12)


def draw_finish_line(surface, offset):
    top_y = int(offset[1])
    
    for y in range(80):
        c = mix(50, 220, y / 80)
        pygame.draw.line(surface, (50, c, 80), (0, top_y + y), (WIDTH, top_y + y))
        
    sq_size = 12
    for x in range(0, WIDTH, sq_size):
        c1 = (0, 0, 0) if (x // sq_size) % 2 == 0 else (255, 255, 255)
        pygame.draw.rect(surface, c1, (x + int(offset[0]), top_y + 80, sq_size, sq_size))
        
        c2 = (255, 255, 255) if (x // sq_size) % 2 == 0 else (0, 0, 0)
        pygame.draw.rect(surface, c2, (x + int(offset[0]), top_y + 80 + sq_size, sq_size, sq_size))
        
    pygame.draw.line(surface, (0, 0, 0), (0, top_y + 80), (WIDTH, top_y + 80), 2)
    pygame.draw.line(surface, (0, 0, 0), (0, top_y + 104), (WIDTH, top_y + 104), 2)


walls = [
    pymunk.Segment(space.static_body, (0, 0), (0, HEIGHT), 5),
    pymunk.Segment(space.static_body, (WIDTH, 0), (WIDTH, HEIGHT), 5),
    pymunk.Segment(space.static_body, (0, HEIGHT), (WIDTH, HEIGHT), 5),
    pymunk.Segment(space.static_body, (0, 0), (WIDTH, 0), 5),
]

for wall in walls:
    wall.elasticity = 1.05
    wall.friction = 0.45
    wall.collision_type = WALL_COLLISION
space.add(*walls)

platform_color = (25, 125, 145) 
platforms = [
    MovingPlatform(160, 45, 2.6, 1.1, platform_color), 
    MovingPlatform(260, 65, 1.2, 0.0, platform_color),
    MovingPlatform(360, 75, 1.5, 2.1, platform_color),
    MovingPlatform(460, 60, 1.1, 4.3, platform_color),
    MovingPlatform(560, 80, 1.7, 1.2, platform_color),
    MovingPlatform(660, 70, 1.3, 3.5, platform_color),
]

rising_floor = RisingFloor(HEIGHT + 100, 18.0, (255, 50, 50))

balls = []
colors = [(255, 80, 80), (80, 255, 120), (80, 180, 255), (255, 220, 80)]

for i, color in enumerate(colors):
    mass = 1
    radius = 10
    moment = pymunk.moment_for_circle(mass, 0, radius)
    body = pymunk.Body(mass, moment)
    body.position = (WIDTH // 2 + random.randint(-62, 62), HEIGHT - 50 - i * 24)
    body.velocity = (random.uniform(-95, 95), random.uniform(0, 45))
    shape = pymunk.Circle(body, radius)
    shape.elasticity = 1.05 
    shape.friction = 0.1 
    shape.collision_type = BALL_COLLISION
    space.add(body, shape)
    balls.append({"body": body, "shape": shape, "radius": radius, "color": color, "winner": False, "trail": []})

sparks = []
celebration_particles = []
screen_shake = 0
winner_found = False
winner_color = None
winner_ball = None
winner_time = 0
font_big = pygame.font.SysFont(None, 78, bold=True)


def play_impact_sound(strength):
    if not bounce_sounds:
        return
    index = clamp(int(strength / 90), 0, len(bounce_sounds) - 1)
    sound = bounce_sounds[index]
    sound.set_volume(clamp(0.16 + strength / 650, 0.16, 0.85))
    sound.play()


def add_sparks(point, color, strength):
    count = clamp(int(strength / 22), 5, 22)
    for _ in range(count):
        sparks.append(Particle(point.x, point.y, color, speed=clamp(strength / 150, 0.5, 2.2), life=random.uniform(0.28, 0.75)))


def collision_handler(arbiter, _space, _data):
    global screen_shake
    strength = arbiter.total_impulse.length
    
    if strength < 1.5:
        return True

    point = arbiter.contact_point_set.points[0].point_a
    shapes = arbiter.shapes
    ball_shape = next((shape for shape in shapes if shape.collision_type == BALL_COLLISION), None)

    color = (120, 190, 255)
    if ball_shape:
        for ball in balls:
            if ball["shape"] == ball_shape:
                color = ball["color"]
                break

    play_impact_sound(strength)
    
    # NEW THRESHOLDS: Only trigger visuals/shake on actual hard hits, ignoring trapped/rolling balls
    if strength > 50:
        add_sparks(point, lighten(color, 25), strength)
        
    if strength > 300:
        screen_shake = max(screen_shake, clamp((strength - 300) / 40, 0, 10))
        
    return True


space.on_collision(BALL_COLLISION, PLATFORM_COLLISION, begin=collision_handler)
space.on_collision(BALL_COLLISION, WALL_COLLISION, begin=collision_handler)

background_particles = [
    {
        "x": random.randint(0, WIDTH),
        "y": random.randint(0, HEIGHT),
        "radius": random.randint(1, 3),
        "speed": random.uniform(8, 34),
    }
    for _ in range(80)
]

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

    difficulty = 1 + int(elapsed // 10) * 0.22

    if winner_found:
        slow_motion_left = max(0, slow_motion_left - dt)
        physics_dt = dt * (0.18 if slow_motion_left > 0 else 0)
        winner_time += dt
        win_fill = clamp((winner_time - 0.25) / 2.1, 0, 1)
        if winner_ball:
            to_win = pymunk.Vec2d(WIDTH // 2, 40) - winner_ball["body"].position
            winner_ball["body"].velocity = to_win * 5
            winner_ball["body"].angular_velocity *= 0.95
    else:
        physics_dt = dt
        for p in platforms:
            p.update(elapsed, difficulty, dt)
        
        rising_floor.update(elapsed, dt)

    if physics_dt > 0:
        for _ in range(2):
            space.step(physics_dt / 2)
            
        for ball in balls:
            if not ball["winner"]:
                speed = ball["body"].velocity.length
                
                if speed > 450:
                    ball["body"].velocity = ball["body"].velocity.normalized() * 450
                
                elif speed < 80 and not winner_found:
                    ball["body"].apply_impulse_at_local_point((random.uniform(-15, 15), -25))

    closest_to_win = min((ball["body"].position.y for ball in balls), default=HEIGHT)
    music_intensity = clamp(1 - (closest_to_win - WIN_Y) / (HEIGHT - WIN_Y), 0, 1)
    try:
        pygame.mixer.music.set_volume(0.22 + music_intensity * 0.55)
    except pygame.error:
        pass

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

    draw_gradient(screen, elapsed)
    screen.blit(grid_surface, (int(shake_offset[0]), int(shake_offset[1])))
    
    draw_finish_line(screen, shake_offset)

    for particle in background_particles:
        pygame.draw.circle(
            screen,
            (255, 100, 180, 100), 
            (int(particle["x"] + shake_offset[0]), int(particle["y"] + shake_offset[1])),
            particle["radius"],
        )

    for p in platforms:
        p.draw(screen, shake_offset, elapsed)
    
    rising_floor.draw(screen, shake_offset, elapsed)

    for ball in balls:
        body = ball["body"]
        pos = body.position
        radius = ball["radius"]
        ball["trail"].append((pos.x, pos.y))
        if len(ball["trail"]) > 18:
            ball["trail"].pop(0)

        if not winner_found and pos.y <= WIN_Y:
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

        portal_light = clamp(1 - (pos.y - WIN_Y) / 160, 0, 1)
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