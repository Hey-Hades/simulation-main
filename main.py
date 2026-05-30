import pygame
import random
import math

pygame.init()
pygame.mixer.init()

WIDTH = 800
HEIGHT = 600

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Multi Ball Simulation")

clock = pygame.time.Clock()

bounce_sound = pygame.mixer.Sound("sounds/sound.mp3")

# Trail effect
fade = pygame.Surface((WIDTH, HEIGHT))
fade.set_alpha(25)
fade.fill((10, 10, 20))

BALL_COUNT = 8

balls = []

for _ in range(BALL_COUNT):

    radius = random.randint(15, 30)

    ball = {
        "x": random.randint(radius, WIDTH - radius),
        "y": random.randint(radius, HEIGHT - radius),
        "vx": random.uniform(-4, 4),
        "vy": random.uniform(-4, 4),
        "radius": radius,
        "color": (
            random.randint(100, 255),
            random.randint(100, 255),
            random.randint(100, 255),
        )
    }

    balls.append(ball)

sound_timer = 0

running = True

while running:

    clock.tick(60)

    sound_timer -= 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.blit(fade, (0, 0))

    # Update balls
    for ball in balls:

        # Apply gravity only if ball is not resting
        if not (
            ball["y"] + ball["radius"] >= HEIGHT
            and ball["vy"] == 0
        ):
            ball["vy"] += 0.15

        # Air resistance
        ball["vx"] *= 0.999
        ball["vy"] *= 0.999

        ball["x"] += ball["vx"]
        ball["y"] += ball["vy"]

        r = ball["radius"]

        collision = False

        # Left/right wall collisions
        if ball["x"] - r <= 0:
            ball["x"] = r
            ball["vx"] *= -0.95
            collision = True

        if ball["x"] + r >= WIDTH:
            ball["x"] = WIDTH - r
            ball["vx"] *= -0.95
            collision = True

        # Floor collision
        if ball["y"] + r >= HEIGHT:

            # Snap to floor
            ball["y"] = HEIGHT - r

            # Bounce
            ball["vy"] *= -0.95

            # Stop tiny bouncing
            if abs(ball["vy"]) < 0.5:
                ball["vy"] = 0

            collision = True

        # Ceiling collision
        if ball["y"] - r <= 0:
            ball["y"] = r
            ball["vy"] *= -0.95
            collision = True

        # Stop tiny drifting
        if abs(ball["vx"]) < 0.05:
            ball["vx"] = 0

        if abs(ball["vy"]) < 0.05:
            ball["vy"] = 0

        # Play sound with cooldown
        if collision and sound_timer <= 0:
            bounce_sound.play()
            sound_timer = 5

    # Ball-to-ball collisions
    for i in range(len(balls)):
        for j in range(i + 1, len(balls)):

            b1 = balls[i]
            b2 = balls[j]

            dx = b2["x"] - b1["x"]
            dy = b2["y"] - b1["y"]

            distance = math.sqrt(dx * dx + dy * dy)

            min_distance = b1["radius"] + b2["radius"]

            if distance < min_distance and distance != 0:

                # Swap velocities
                b1["vx"], b2["vx"] = b2["vx"], b1["vx"]
                b1["vy"], b2["vy"] = b2["vy"], b1["vy"]

                # Lose energy slightly
                b1["vx"] *= 0.98
                b1["vy"] *= 0.98
                b2["vx"] *= 0.98
                b2["vy"] *= 0.98

                # Push balls apart
                overlap = min_distance - distance

                nx = dx / distance
                ny = dy / distance

                b1["x"] -= nx * overlap / 2
                b1["y"] -= ny * overlap / 2

                b2["x"] += nx * overlap / 2
                b2["y"] += ny * overlap / 2

                if sound_timer <= 0:
                    bounce_sound.play()
                    sound_timer = 5

    # Draw balls
    for ball in balls:

        pygame.draw.circle(
            screen,
            ball["color"],
            (int(ball["x"]), int(ball["y"])),
            ball["radius"]
        )

    pygame.display.flip()

pygame.quit()
