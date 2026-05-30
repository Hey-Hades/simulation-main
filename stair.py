import pygame
import random

pygame.init()
pygame.mixer.init()

WIDTH = 900
HEIGHT = 700

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Stair Music Simulation")

clock = pygame.time.Clock()

# Load musical notes
notes = [
    pygame.mixer.Sound("sounds/sound.mp3"),
    pygame.mixer.Sound("sounds/sound.mp3"),
    pygame.mixer.Sound("sounds/sound.mp3"),
    pygame.mixer.Sound("sounds/sound.mp3"),
    pygame.mixer.Sound("sounds/sound.mp3"),
]

# Trail effect
fade = pygame.Surface((WIDTH, HEIGHT))
fade.set_alpha(30)
fade.fill((5, 5, 15))

# Stair settings
stairs = []

STAIR_WIDTH = 120
STAIR_HEIGHT = 35

for i in range(8):

    stair = pygame.Rect(
        120 + i * 90,
        150 + i * 55,
        STAIR_WIDTH,
        STAIR_HEIGHT
    )

    stairs.append(stair)

# Ball settings
balls = []

for i in range(12):

    ball = {
        "x": 100 + i * 20,
        "y": 50 - i * 80,
        "vx": random.uniform(1, 3),
        "vy": 0,
        "radius": 15,
        "color": (
            random.randint(120, 255),
            random.randint(120, 255),
            random.randint(120, 255)
        ),
        "note_index": i % len(notes)
    }

    balls.append(ball)

# Music progression
collision_count = 0
speed_multiplier = 1

running = True

while running:

    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.blit(fade, (0, 0))

    # Increase chaos over time
    if collision_count > 30:
        speed_multiplier = 1.2

    if collision_count > 60:
        speed_multiplier = 1.5

    if collision_count > 100:
        speed_multiplier = 2

    for ball in balls:

        # Gravity
        ball["vy"] += 0.25

        # Apply progression speed
        ball["x"] += ball["vx"] * speed_multiplier
        ball["y"] += ball["vy"] * speed_multiplier

        r = ball["radius"]

        # Stair collisions
        for stair in stairs:

            if stair.collidepoint(ball["x"], ball["y"] + r):

                # Snap above stair
                ball["y"] = stair.top - r

                # Bounce
                ball["vy"] *= -0.75

                # Slight horizontal push
                ball["vx"] += random.uniform(-0.3, 0.3)

                # Play musical note
                note = notes[ball["note_index"]]

                volume = min(abs(ball["vy"]) / 15, 1)
                note.set_volume(volume)
                note.play()

                collision_count += 1

        # Wall bounce
        if ball["x"] - r <= 0 or ball["x"] + r >= WIDTH:
            ball["vx"] *= -1

        # Floor bounce
        if ball["y"] + r >= HEIGHT:

            ball["y"] = HEIGHT - r
            ball["vy"] *= -0.7

            # Tiny movement stop
            if abs(ball["vy"]) < 0.5:
                ball["vy"] = 0

        # Draw glow
        glow_radius = r + 10

        pygame.draw.circle(
            screen,
            (40, 40, 80),
            (int(ball["x"]), int(ball["y"])),
            glow_radius
        )

        # Draw actual ball
        pygame.draw.circle(
            screen,
            ball["color"],
            (int(ball["x"]), int(ball["y"])),
            r
        )

    # Draw stairs
    for stair in stairs:

        pygame.draw.rect(
            screen,
            (120, 120, 180),
            stair,
            border_radius=10
        )

    pygame.display.flip()

pygame.quit()
