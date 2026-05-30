import pygame
import pymunk
import random
import math

# =========================================================
# INIT
# =========================================================
pygame.init()

WIDTH = 360
HEIGHT = 640

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Gravity Portal Arena")

clock = pygame.time.Clock()

# =========================================================
# COLORS
# =========================================================
BLACK = (5, 5, 15)

CYAN = (0, 255, 255)

WHITE = (255, 255, 255)

RED = (255, 80, 80)
GREEN = (80, 255, 120)
BLUE = (80, 180, 255)
YELLOW = (255, 220, 80)

BALL_COLORS = [RED, GREEN, BLUE, YELLOW]

# =========================================================
# PHYSICS
# =========================================================
space = pymunk.Space()

space.gravity = (0, 900)

space.iterations = 30

# =========================================================
# SCREEN SHAKE
# =========================================================
shake_timer = 0

def trigger_shake(amount=10):

    global shake_timer

    shake_timer = amount

# =========================================================
# FADE EFFECT
# =========================================================
fade = pygame.Surface((WIDTH, HEIGHT))

fade.set_alpha(40)

fade.fill(BLACK)

# =========================================================
# WALLS
# =========================================================
WALL_SIZE = 20

walls = [

    # LEFT
    pymunk.Segment(
        space.static_body,
        (0, 0),
        (0, HEIGHT),
        WALL_SIZE
    ),

    # RIGHT
    pymunk.Segment(
        space.static_body,
        (WIDTH, 0),
        (WIDTH, HEIGHT),
        WALL_SIZE
    ),

    # BOTTOM
    pymunk.Segment(
        space.static_body,
        (0, HEIGHT),
        (WIDTH, HEIGHT),
        WALL_SIZE
    ),
]

# =========================================================
# TOP WALL WITH PORTAL GAP
# =========================================================
PORTAL_X = WIDTH - 60

GAP_SIZE = 45

gap_left = PORTAL_X - GAP_SIZE // 2
gap_right = PORTAL_X + GAP_SIZE // 2

# TOP LEFT WALL
walls.append(

    pymunk.Segment(
        space.static_body,
        (0, 0),
        (gap_left, 0),
        WALL_SIZE
    )
)

# TOP RIGHT WALL
walls.append(

    pymunk.Segment(
        space.static_body,
        (gap_right, 0),
        (WIDTH, 0),
        WALL_SIZE
    )
)

for wall in walls:

    wall.elasticity = 0.9
    wall.friction = 0.5

space.add(*walls)

# =========================================================
# PORTAL
# =========================================================
PORTAL_RADIUS = 18

portal_x = PORTAL_X
portal_y = 35

# =========================================================
# OBSTACLES
# =========================================================
obstacles = []

obstacle_data = [

    (WIDTH // 2, 120, 180, 16, 2),
    (WIDTH // 2, 230, 180, 16, -2.5),
    (WIDTH // 2, 340, 180, 16, 3),
    (WIDTH // 2, 450, 180, 16, -3.5),
]

for x, y, w, h, speed in obstacle_data:

    body = pymunk.Body(
        body_type=pymunk.Body.KINEMATIC
    )

    body.position = (x, y)

    shape = pymunk.Poly.create_box(
        body,
        (w, h)
    )

    shape.elasticity = 0.95
    shape.friction = 0.5

    body.angular_velocity = math.radians(
        speed * 50
    )

    space.add(body, shape)

    obstacles.append((body, shape))

# =========================================================
# BALLS
# =========================================================
balls = []

for i in range(4):

    mass = 1

    radius = 12

    moment = pymunk.moment_for_circle(
        mass,
        0,
        radius
    )

    body = pymunk.Body(mass, moment)

    body.position = (

        WIDTH // 2 + random.randint(-80, 80),

        HEIGHT - 120 - i * 30
    )

    body.velocity = (

        random.randint(-250, 250),

        random.randint(-250, 250)
    )

    shape = pymunk.Circle(body, radius)

    shape.elasticity = 0.92
    shape.friction = 0.4

    space.add(body, shape)

    balls.append({

        "body": body,

        "radius": radius,

        "color": BALL_COLORS[i],

        "trail": [],

        "winner": False
    })

# =========================================================
# GRAVITY
# =========================================================
gravity_modes = [

    ("DOWN", (0, 900)),

    ("UP", (0, -900)),
]

gravity_index = 0

gravity_timer = 0

GRAVITY_CHANGE_TIME = 1500

current_gravity_text = "DOWN"

# =========================================================
# WINNER
# =========================================================
winner_found = False

winner_color = None

winning_ball = None

# =========================================================
# PARTICLES
# =========================================================
particles = []

for i in range(100):

    particles.append({

        "x": random.randint(0, WIDTH),

        "y": random.randint(0, HEIGHT),

        "speed": random.uniform(1, 3),

        "size": random.randint(1, 3)
    })

# =========================================================
# MAIN LOOP
# =========================================================
running = True

while running:

    dt = 1 / 60

    clock.tick(60)

    # =====================================================
    # EVENTS
    # =====================================================
    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False

    # =====================================================
    # GRAVITY CHANGE
    # =====================================================
    gravity_timer += clock.get_time()

    if gravity_timer >= GRAVITY_CHANGE_TIME and not winner_found:

        gravity_timer = 0

        gravity_index = (
            gravity_index + 1
        ) % len(gravity_modes)

        current_gravity_text, gravity = gravity_modes[
            gravity_index
        ]

        space.gravity = gravity

        trigger_shake(12)

    # =====================================================
    # PHYSICS
    # =====================================================
    if not winner_found:

        for i in range(4):

            space.step(dt / 4)

    else:

        for i in range(2):

            space.step(dt / 4)

    # =====================================================
    # SHAKE OFFSET
    # =====================================================
    offset_x = 0
    offset_y = 0

    if shake_timer > 0:

        offset_x = random.randint(
            -shake_timer,
            shake_timer
        )

        offset_y = random.randint(
            -shake_timer,
            shake_timer
        )

        shake_timer -= 1

    # =====================================================
    # BACKGROUND
    # =====================================================
    screen.blit(fade, (0, 0))

    # =====================================================
    # PARTICLES
    # =====================================================
    for p in particles:

        p["y"] += p["speed"]

        if p["y"] > HEIGHT:

            p["y"] = 0

            p["x"] = random.randint(0, WIDTH)

        pygame.draw.circle(

            screen,

            (40, 40, 70),

            (
                int(p["x"]) + offset_x,
                int(p["y"]) + offset_y
            ),

            p["size"]
        )

    # =====================================================
    # GRID
    # =====================================================
    for x in range(0, WIDTH, 40):

        pygame.draw.line(

            screen,

            (20, 20, 40),

            (x + offset_x, 0),

            (x + offset_x, HEIGHT)
        )

    for y in range(0, HEIGHT, 40):

        pygame.draw.line(

            screen,

            (20, 20, 40),

            (0, y + offset_y),

            (WIDTH, y + offset_y)
        )

    # =====================================================
    # PORTAL
    # =====================================================
    pygame.draw.circle(

        screen,

        (180, 180, 180),

        (
            portal_x + offset_x,
            portal_y + offset_y
        ),

        PORTAL_RADIUS + 10
    )

    pygame.draw.circle(

        screen,

        WHITE,

        (
            portal_x + offset_x,
            portal_y + offset_y
        ),

        PORTAL_RADIUS
    )

    pygame.draw.circle(

        screen,

        BLACK,

        (
            portal_x + offset_x,
            portal_y + offset_y
        ),

        PORTAL_RADIUS - 5
    )

    # =====================================================
    # OBSTACLES
    # =====================================================
    for body, shape in obstacles:

        points = shape.get_vertices()

        points = [

            p.rotated(body.angle) + body.position

            for p in points
        ]

        points = [

            (
                int(p.x) + offset_x,

                int(p.y) + offset_y
            )

            for p in points
        ]

        pygame.draw.polygon(

            screen,

            (140, 140, 255),

            points
        )

    # =====================================================
    # BALLS
    # =====================================================
    MAX_SPEED = 850

    for ball in balls:

        body = ball["body"]

        vx, vy = body.velocity

        speed = (vx**2 + vy**2) ** 0.5

        if speed > MAX_SPEED:

            scale = MAX_SPEED / speed

            body.velocity = (

                vx * scale,

                vy * scale
            )

        # =================================================
        # SUCTION EFFECT
        # =================================================
        if winner_found and ball == winning_ball:

            dx = portal_x - body.position.x
            dy = portal_y - body.position.y

            body.velocity = (

                dx * 4,
                dy * 4
            )

            if ball["radius"] > 1:

                ball["radius"] *= 0.96

        x = int(body.position.x)
        y = int(body.position.y)

        r = int(ball["radius"])

        # =================================================
        # TRAIL
        # =================================================
        if not ball["winner"]:

            ball["trail"].append((x, y))

        if len(ball["trail"]) > 18:

            ball["trail"].pop(0)

        for i, pos in enumerate(ball["trail"]):

            pygame.draw.circle(

                screen,

                ball["color"],

                (
                    pos[0] + offset_x,

                    pos[1] + offset_y
                ),

                max(2, i // 3)
            )

        # =================================================
        # WIN DETECTION
        # =================================================
        distance = math.hypot(

            x - portal_x,

            y - portal_y
        )

        if distance < PORTAL_RADIUS - 4 and not winner_found:

            winner_found = True

            winner_color = ball["color"]

            winning_ball = ball

            ball["winner"] = True

            trigger_shake(30)

        # =================================================
        # HIDE AFTER FULLY INSIDE
        # =================================================
        if winner_found and ball == winning_ball:

            if ball["radius"] < 2:
                continue

        # =================================================
        # GLOW
        # =================================================
        pygame.draw.circle(

            screen,

            (40, 40, 80),

            (
                x + offset_x,

                y + offset_y
            ),

            r + 10
        )

        # =================================================
        # BALL
        # =================================================
        pygame.draw.circle(

            screen,

            ball["color"],

            (
                x + offset_x,

                y + offset_y
            ),

            r
        )

    # =====================================================
    # SMALL CENTER GRAVITY TEXT
    # =====================================================
    gravity_font = pygame.font.SysFont(
        "Arial",
        22,
        bold=True
    )

    gravity_text = gravity_font.render(

        current_gravity_text,

        True,

        CYAN
    )

    screen.blit(

        gravity_text,

        (
            WIDTH // 2
            - gravity_text.get_width() // 2,

            HEIGHT // 2 - 15
        )
    )

    # =====================================================
    # TIMER BAR
    # =====================================================
    remaining = (
        GRAVITY_CHANGE_TIME - gravity_timer
    )

    bar_width = int(

        (remaining / GRAVITY_CHANGE_TIME) * 220
    )

    pygame.draw.rect(

        screen,

        CYAN,

        (
            WIDTH // 2 - 110,

            85,

            bar_width,

            7
        )
    )

    # =====================================================
    # WINNER TEXT
    # =====================================================
    if winner_found:

        win_font = pygame.font.SysFont(
            "Arial",
            50,
            bold=True
        )

        text = win_font.render(

            "WINNER!",

            True,

            winner_color
        )

        screen.blit(

            text,

            (
                WIDTH // 2
                - text.get_width() // 2,

                HEIGHT // 2 - 100
            )
        )

    # =====================================================
    # UPDATE
    # =====================================================
    pygame.display.flip()

pygame.quit()