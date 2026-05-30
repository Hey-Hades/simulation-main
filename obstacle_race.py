import pygame
import random

pygame.init()
pygame.mixer.init()

WIDTH = 1000
HEIGHT = 700

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Obstacle Race Simulation")

clock = pygame.time.Clock()

bounce_sound = pygame.mixer.Sound("sounds/sound.mp3")

# Trail effect
fade = pygame.Surface((WIDTH, HEIGHT))
fade.set_alpha(25)
fade.fill((5, 5, 15))

# Finish line
FINISH_X = WIDTH - 80

# Obstacles
obstacles = [
    pygame.Rect(250, 120, 40, 300),
    pygame.Rect(450, 300, 40, 300),
    pygame.Rect(650, 100, 40, 300),
    pygame.Rect(820, 250, 40, 300),
]

# Balls
balls = []

colors = [
    (255, 80, 80),
    (80, 255, 120),
    (80, 180, 255),
    (255, 220, 80)
]

for i in range(4):

    ball = {
        "x": 60,
        "y": 120 + i * 120,
        "vx": random.uniform(3, 5),
        "vy": random.uniform(-1, 1),
        "radius": 18,
        "color": colors[i],
        "winner": False
    }

    balls.append(ball)

winner_found = False
winner_color = None

running = True

while running:

    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.blit(fade, (0, 0))

    # Draw finish line
    pygame.draw.rect(
        screen,
        (255, 255, 255),
        (FINISH_X, 0, 8, HEIGHT)
    )

    # Draw obstacles
    for obstacle in obstacles:

        pygame.draw.rect(
            screen,
            (120, 120, 180),
            obstacle,
            border_radius=10
        )

    for ball in balls:

        # Stop everything after winner
        if winner_found:
            ball["vx"] *= 0.96
            ball["vy"] *= 0.96

            if abs(ball["vx"]) < 0.05:
                ball["vx"] = 0

            if abs(ball["vy"]) < 0.05:
                ball["vy"] = 0

        else:
            # Random movement
            ball["vy"] += random.uniform(-0.15, 0.15)

        # Move
        ball["x"] += ball["vx"]
        ball["y"] += ball["vy"]

        r = ball["radius"]

        # Top/bottom boundaries
        if ball["y"] - r <= 0:
            ball["y"] = r
            ball["vy"] *= -1
            bounce_sound.play()

        if ball["y"] + r >= HEIGHT:
            ball["y"] = HEIGHT - r
            ball["vy"] *= -1
            bounce_sound.play()

        # Left boundary
        if ball["x"] - r <= 0:
            ball["x"] = r
            ball["vx"] *= -1
            bounce_sound.play()

        # Obstacle collisions
        ball_rect = pygame.Rect(
            ball["x"] - r,
            ball["y"] - r,
            r * 2,
            r * 2
        )

        for obstacle in obstacles:

            if ball_rect.colliderect(obstacle):

                # Push back
                ball["x"] -= ball["vx"] * 2
                ball["y"] -= ball["vy"] * 2

                # Bounce
                ball["vx"] *= -1
                ball["vy"] *= -1

                # Random deflection
                ball["vy"] += random.uniform(-2, 2)

                bounce_sound.play()

        # Winner detection
        if ball["x"] + r >= FINISH_X and not winner_found:

            winner_found = True
            winner_color = ball["color"]
            ball["winner"] = True

        # Glow
        pygame.draw.circle(
            screen,
            (40, 40, 80),
            (int(ball["x"]), int(ball["y"])),
            r + 10
        )

        # Ball
        pygame.draw.circle(
            screen,
            ball["color"],
            (int(ball["x"]), int(ball["y"])),
            r
        )

    # Winner text
    if winner_found:

        font = pygame.font.SysFont(None, 60)

        text = font.render("WINNER!", True, winner_color)

        screen.blit(text, (WIDTH // 2 - 100, 40))

    pygame.display.flip()

pygame.quit()
