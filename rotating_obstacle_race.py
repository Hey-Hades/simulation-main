import pygame
import pymunk
import random
import math

pygame.init()
pygame.mixer.init()

WIDTH = 1000
HEIGHT = 700

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pymunk Obstacle Race")

clock = pygame.time.Clock()

bounce_sound = pygame.mixer.Sound("sounds/sound.mp3")

# Physics world
space = pymunk.Space()
space.gravity = (0, 0)

# Trail effect
fade = pygame.Surface((WIDTH, HEIGHT))
fade.set_alpha(25)
fade.fill((5, 5, 15))

# Finish line
FINISH_X = WIDTH - 80

# Walls
walls = [
    pymunk.Segment(space.static_body, (0, 0), (0, HEIGHT), 5),
    pymunk.Segment(space.static_body, (0, 0), (WIDTH, 0), 5),
    pymunk.Segment(space.static_body, (0, HEIGHT), (WIDTH, HEIGHT), 5),
]

for wall in walls:
    wall.elasticity = 1
    wall.friction = 0.5

space.add(*walls)

# Rotating obstacles
obstacles = []

obstacle_data = [
    (250, 250, 40, 300, 1),
    (450, 450, 40, 300, -2),
    (650, 250, 40, 300, 1.5),
    (820, 400, 40, 300, -1),
]

for x, y, w, h, speed in obstacle_data:

    body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    body.position = x, y

    shape = pymunk.Poly.create_box(body, (w, h))

    shape.elasticity = 1
    shape.friction = 0.5

    body.angular_velocity = math.radians(speed * 50)

    space.add(body, shape)

    obstacles.append((body, shape, w, h))

# Balls
balls = []

colors = [
    (255, 80, 80),
    (80, 255, 120),
    (80, 180, 255),
    (255, 220, 80)
]

for i in range(4):

    mass = 1
    radius = 18

    moment = pymunk.moment_for_circle(
        mass,
        0,
        radius
    )

    body = pymunk.Body(mass, moment)

    body.position = (60, 120 + i * 120)

    body.velocity = (
        random.uniform(250, 350),
        random.uniform(-50, 50)
    )

    shape = pymunk.Circle(body, radius)

    shape.elasticity = 0.95
    shape.friction = 0.5

    space.add(body, shape)

    balls.append({
        "body": body,
        "shape": shape,
        "radius": radius,
        "color": colors[i],
        "winner": False
    })

winner_found = False
winner_color = None

# Collision sound handler
def collision_handler(arbiter, space, data):

    bounce_sound.play()

    return True

space.on_collision(
    None,
    None,
    begin=collision_handler
)

running = True

while running:

    dt = 1 / 60

    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Physics update
    space.step(dt)

    screen.blit(fade, (0, 0))

    # Finish line
    pygame.draw.rect(
        screen,
        (255, 255, 255),
        (FINISH_X, 0, 8, HEIGHT)
    )

    # Draw rotating obstacles
    for body, shape, w, h in obstacles:

        points = shape.get_vertices()

        points = [
            p.rotated(body.angle) + body.position
            for p in points
        ]

        points = [
            (int(p.x), int(p.y))
            for p in points
        ]

        pygame.draw.polygon(
            screen,
            (120, 120, 220),
            points
        )

    # Draw balls
    for ball in balls:

        body = ball["body"]

        x = int(body.position.x)
        y = int(body.position.y)

        r = ball["radius"]

        # Winner detection
        if x + r >= FINISH_X and not winner_found:

            winner_found = True
            winner_color = ball["color"]

            ball["winner"] = True

        # Slow after winner
        if winner_found:

            body.velocity = (
                body.velocity.x * 0.98,
                body.velocity.y * 0.98
            )

        # Glow
        pygame.draw.circle(
            screen,
            (40, 40, 80),
            (x, y),
            r + 10
        )

        # Ball
        pygame.draw.circle(
            screen,
            ball["color"],
            (x, y),
            r
        )

    # Winner text
    if winner_found:

        font = pygame.font.SysFont(None, 60)

        text = font.render(
            "WINNER!",
            True,
            winner_color
        )

        screen.blit(
            text,
            (WIDTH // 2 - 100, 40)
        )

    pygame.display.flip()

pygame.quit()
