
import pygame
import pymunk
import random
import math

pygame.init()
pygame.mixer.init()

WIDTH = 90*4;
HEIGHT = 160*4

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pymunk Obstacle Race")

clock = pygame.time.Clock()

background_music = pygame.mixer.music.load("sounds/short1.mp3"
)

pygame.mixer.music.play(-1)

bounce_sound = pygame.mixer.Sound("sounds/sound.mp3")

# Physics world
space = pymunk.Space()
space.gravity = (0, 100)

# Trail effect
fade = pygame.Surface((WIDTH, HEIGHT))
fade.set_alpha(25)
fade.fill((5, 5, 15))

# Finish line
FINISH_Y = 80

# Walls
# Finish gap
gap_left = WIDTH // 2 - 80
gap_right = WIDTH // 2 + 80

walls = [

    # Left wall
    pymunk.Segment(
        space.static_body,
        (0, 0),
        (0, HEIGHT),
        5
    ),

    # Right wall
    pymunk.Segment(
        space.static_body,
        (WIDTH, 0),
        (WIDTH, HEIGHT),
        5
    ),

    # Bottom wall
    pymunk.Segment(
        space.static_body,
        (0, HEIGHT),
        (WIDTH, HEIGHT),
        5
    ),

    # Top finish wall LEFT
    pymunk.Segment(
        space.static_body,
        (0, FINISH_Y),
        (gap_left, FINISH_Y),
        5
    ),

    # Top finish wall RIGHT
    pymunk.Segment(
        space.static_body,
        (gap_right, FINISH_Y),
        (WIDTH, FINISH_Y),
        5
    )
]

for wall in walls:
    wall.elasticity = 1
    wall.friction = 0.5

space.add(*walls)# Rotating obstacles
obstacles = []

obstacle_data = [

    (WIDTH // 2, 520, 200, 10, 1),
    (WIDTH // 2, 420, 200, 10, -1.5),
    (WIDTH // 2, 320, 200, 10, 2),
    (WIDTH // 2, 220, 200, 10, -2.5),

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
    radius = 10

    moment = pymunk.moment_for_circle(
        mass,
        0,
        radius
    )

    body = pymunk.Body(mass, moment)

    body.position = (
    WIDTH // 2 + random.randint(-70, 70),
    HEIGHT - 80 - i * 30
)
    body.velocity = (
    random.uniform(-120, 120),
    random.uniform(-450, -320))
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

background_particles = []

for i in range(80):

    particle = {
        "x": random.randint(0, WIDTH),
        "y": random.randint(0, HEIGHT),
        "radius": random.randint(1, 3),
        "speed": random.uniform(0.2, 1.2)
    }

    background_particles.append(particle)

while running:

    dt = 1 / 60

    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Physics update
    space.step(dt)

    screen.blit(fade, (0, 0))

    # Background particles
    for particle in background_particles:

        particle["y"] += particle["speed"]

        # Reset when leaving screen
        if particle["y"] > HEIGHT:

            particle["y"] = 0
            particle["x"] = random.randint(0, WIDTH)

        pygame.draw.circle(
            screen,
            (40, 40, 70),
            (int(particle["x"]), int(particle["y"])),
            particle["radius"]
        )

    #Grid 
    for x in range(0, WIDTH, 40):
        pygame.draw.line(screen, (20,20,40), (x,0), (x,HEIGHT))

    for y in range(0, HEIGHT, 40):
        pygame.draw.line(screen, (20,20,40), (0,y), (WIDTH,y))

    # Finish line

    pygame.draw.line(
        screen,
        (0, 255, 255),
        (0, FINISH_Y),
        (gap_left, FINISH_Y),
        8
    )

    pygame.draw.line(
            screen,
            (0, 255, 255),
            (gap_right, FINISH_Y),
            (WIDTH, FINISH_Y),
            8
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
        if y - 2*r <= FINISH_Y and gap_left < x < gap_right and not winner_found:

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
