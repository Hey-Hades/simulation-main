import pygame
import sys
import math
import os  

# --- 1. Initialize Pygame ---
pygame.init()

# --- 2. Constants & Setup ---
WIDTH, HEIGHT = 430, 800  
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Viral Flag Simulation")
clock = pygame.time.Clock()

# --- Load Assets (Background & Ball) ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Background
try:
    bg_path = os.path.join(SCRIPT_DIR, "grass_background.png")
    bg_image = pygame.image.load(bg_path).convert()
    bg_image = pygame.transform.scale(bg_image, (WIDTH, HEIGHT))
except Exception as e:
    print(f"Warning: Could not load grass_background.png. {e}")
    bg_image = pygame.Surface((WIDTH, HEIGHT))
    bg_image.fill((90, 191, 89))

# --- 4. Environment Variables ---
lime_radius = 185  
y_pos = HEIGHT // 2 + 50   
left_x = 0          # Center locked exactly on the left edge
right_x = WIDTH     # Center locked exactly on the right edge
lime_angle = 0.0
rotation_speed = 0.01 

# --- 5. Object Variables (The Football) ---
ball_radius = 26.37 
ball_x, ball_y = WIDTH // 2, 170 
ball_vx, ball_vy = 4.5, 0 
ball_angle_degrees = 0.0 
gravity = 0.40
bounce_retention = 1.02 

# Gameplay Variables
last_touched = None
winner = None

# 2. The Ball Sprite
try:
    ball_path = os.path.join(SCRIPT_DIR, "ball.png")
    original_ball_img = pygame.image.load(ball_path).convert_alpha()
    original_ball_img = pygame.transform.smoothscale(original_ball_img, (int(ball_radius * 2), int(ball_radius * 2)))
    use_image_ball = True
except Exception as e:
    print(f"Warning: Could not load ball.png. Falling back to drawn ball. {e}")
    use_image_ball = False

# --- Cross-Platform Font Fixing ---
text_fonts = ["arial", "dejavusans", "liberationsans", "sans"]
font_huge_text = pygame.font.SysFont(text_fonts, 50, bold=True) 
font_large_text = pygame.font.SysFont(text_fonts, 34, bold=True) 
font_small_text = pygame.font.SysFont(text_fonts, 22, bold=True)

emoji_fonts = ["segoeuiemoji", "notocoloremoji", "applecoloremoji", "dejavusans"]
font_large_emoji = pygame.font.SysFont(emoji_fonts, 35) 
font_small_emoji = pygame.font.SysFont(emoji_fonts, 24)

# --- 3. Pre-Render Watermark ---
part1 = font_small_text.render("@ B o u n c e ", True, (245, 245, 245)) 
part2 = font_small_text.render("C u l t", True, (255, 210, 70))
total_watermark_width = part1.get_width() + part2.get_width()
max_watermark_height = max(part1.get_height(), part2.get_height())
watermark_start_x = (WIDTH - total_watermark_width) // 2
watermark_start_y = HEIGHT - max_watermark_height - 100

# --- Custom Drawing Functions ---
def apply_circular_mask(surface, radius):
    mask = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    mask.fill((0, 0, 0, 0))
    pygame.draw.circle(mask, (255, 255, 255, 255), (radius, radius), radius)
    
    masked_surface = surface.copy()
    masked_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return masked_surface

def create_canada_flag(radius):
    """Draws an accurate stylized 11-point Canadian maple leaf, scaled correctly."""
    w = h = radius * 2
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    
    # Background (Red - White - Red in 1:2:1 approximate circular space)
    pygame.draw.rect(surf, (255, 0, 0), (0, 0, w // 4, h))
    pygame.draw.rect(surf, (255, 255, 255), (w // 4, 0, w // 2, h))
    pygame.draw.rect(surf, (255, 0, 0), (3 * w // 4, 0, w // 4, h))

    # Center and scaling
    cx, cy = w // 2, h // 2
    scale = radius * 0.75  # The standard is the leaf fits in a 1/2 of the height

    # Stylized 11-point maple leaf points (normalized for scaling)
    # Origin is at the leaf's bounding box center, y-up. Stem is at bottom.
    points = [
        (0.0, 1.0),   # Top tip
        (0.12, 0.70),  # Inner right top
        (0.48, 0.88),  # Right upper tip
        (0.36, 0.50),  # Inner right middle
        (0.80, 0.38),  # Right far tip
        (0.60, 0.10),  # Inner right lower
        (0.68, -0.32), # Right lower tip
        (0.18, 0.00),  # Bottom inner right
        (0.08, -1.00), # Stem right top
        (-0.08, -1.00), # Stem left top
        (-0.18, 0.00), # Bottom inner left
        (-0.68, -0.32), # Left lower tip
        (-0.60, 0.10),  # Inner left lower
        (-0.80, 0.38),  # Left far tip
        (-0.36, 0.50),  # Inner left middle
        (-0.48, 0.88),  # Left upper tip
        (-0.12, 0.70)  # Inner left top
    ]
    
    # Convert points with scaling and transform to Pygame's y-down
    leaf_points = [(cx + int(px * scale), cy - int(py * scale)) for px, py in points]
    pygame.draw.polygon(surf, (255, 0, 0), leaf_points)

    return apply_circular_mask(surf, radius)

def create_bosnia_flag(radius):
    """Draws the Bosnia and Herzegovina flag."""
    w = h = radius * 2
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    
    # Blue background
    surf.fill((0, 35, 149))
    
    # Yellow Triangle
    pygame.draw.polygon(surf, (254, 203, 14), [(w * 0.25, h * 0.15), (w * 0.85, h * 0.15), (w * 0.85, h * 0.75)])
    
    def draw_star(surface, x, y, size):
        star_points = []
        for i in range(5):
            angle_outer = math.radians(i * 72 - 90)
            px = x + size * math.cos(angle_outer)
            py = y + size * math.sin(angle_outer)
            star_points.append((px, py))
            
            angle_inner = math.radians(i * 72 + 36 - 90)
            px_inner = x + (size * 0.4) * math.cos(angle_inner)
            py_inner = y + (size * 0.4) * math.sin(angle_inner)
            star_points.append((px_inner, py_inner))
        pygame.draw.polygon(surface, (255, 255, 255), star_points)
        
    # Draw stars parallel to the hypotenuse
    num_stars = 7
    start_x, start_y = w * 0.15, h * 0.2
    end_x, end_y = w * 0.75, h * 0.8
    
    for i in range(num_stars):
        fraction = i / (num_stars - 1)
        sx = start_x + fraction * (end_x - start_x)
        sy = start_y + fraction * (end_y - start_y)
        draw_star(surf, sx, sy, radius * 0.09)

    return apply_circular_mask(surf, radius)

flag_canada = create_canada_flag(lime_radius)
flag_bosnia = create_bosnia_flag(lime_radius)

def draw_goal(surface):
    goal_w = 200
    goal_h = 80
    goal_x = (WIDTH - goal_w) // 2
    goal_y = HEIGHT - goal_h
    
    pygame.draw.rect(surface, (255, 255, 255), (goal_x, goal_y, goal_w, goal_h), 6)
    
    for i in range(10, goal_w, 15):
        pygame.draw.line(surface, (200, 200, 200), (goal_x + i, goal_y), (goal_x + i, HEIGHT), 2)
    for i in range(10, goal_h, 15):
        pygame.draw.line(surface, (200, 200, 200), (goal_x, goal_y + i), (goal_x + goal_w, goal_y + i), 2)

def draw_drawn_football_fallback(surface, x, y, radius, angle):
    """The old math-based ball, just in case the image fails to load."""
    pygame.draw.circle(surface, (245, 245, 245), (int(x), int(y)), int(radius))
    pygame.draw.circle(surface, (20, 20, 20), (int(x), int(y)), int(radius), 2)
    pentagon_radius = radius * 0.45
    pentagon_points = []
    for i in range(5):
        theta = angle + math.radians(i * 72 - 18) 
        px = x + pentagon_radius * math.cos(theta)
        py = y + pentagon_radius * math.sin(theta)
        pentagon_points.append((px, py))
    pygame.draw.polygon(surface, (20, 20, 20), pentagon_points)
    for px, py in pentagon_points:
        dx, dy = px - x, py - y
        length = math.hypot(dx, dy)
        if length != 0:
            nx, ny = dx / length, dy / length
            ex = x + nx * radius
            ey = y + ny * radius
            pygame.draw.line(surface, (20, 20, 20), (px, py), (ex, ey), 2)

def resolve_collision(bx, by, bvx, bvy, cx, cy, R):
    dx = bx - cx
    dy = by - cy
    dist = math.hypot(dx, dy)
    
    if dist < R + ball_radius:
        overlap = (R + ball_radius) - dist
        nx = dx / dist 
        ny = dy / dist 
        bx += nx * overlap
        by += ny * overlap
        
        dot_product = bvx * nx + bvy * ny
        
        if dot_product < 0:
            bvx -= 2 * dot_product * nx
            bvy -= 2 * dot_product * ny
            bvx *= bounce_retention
            bvy *= bounce_retention
            return bx, by, bvx, bvy, True 
            
    return bx, by, bvx, bvy, False 

def draw_rotating_flag(surface, flag_img, x, y, radius, angle_radians, is_left):
    angle_degrees = math.degrees(angle_radians)
    rotated_image = pygame.transform.rotate(flag_img, angle_degrees)
    new_rect = rotated_image.get_rect(center=(int(x), int(y)))
    
    if is_left:
        surface.set_clip(pygame.Rect(int(x), int(y) - radius, radius, radius * 2))
    else:
        surface.set_clip(pygame.Rect(int(x) - radius, int(y) - radius, radius, radius * 2))
        
    surface.blit(rotated_image, new_rect.topleft)
    pygame.draw.circle(surface, (255, 255, 255), (int(x), int(y)), radius, 8)
    surface.set_clip(None)

# --- 6. Main Game Loop ---
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    if not winner:
        lime_angle += rotation_speed
        ball_vy += gravity
        ball_x += ball_vx
        ball_y += ball_vy
        ball_angle_degrees -= ball_vx * 0.5 

        if ball_x - ball_radius < 0: 
            ball_x = ball_radius
            ball_vx *= -1
        elif ball_x + ball_radius > WIDTH:
            ball_x = WIDTH - ball_radius
            ball_vx *= -1
            
        if ball_y > HEIGHT - 40: 
            if last_touched:
                winner = last_touched
            else:
                ball_y = -50
                ball_vy = 0
                ball_x = WIDTH // 2

        # SWAPPED: Left hit is now Bosnia & Herzegovina
        ball_x, ball_y, ball_vx, ball_vy, hit_left = resolve_collision(
            ball_x, ball_y, ball_vx, ball_vy, left_x, y_pos, lime_radius
        )
        if hit_left:
            last_touched = "Bosnia & Herzegovina"
            
        # SWAPPED: Right hit is now Canada
        ball_x, ball_y, ball_vx, ball_vy, hit_right = resolve_collision(
            ball_x, ball_y, ball_vx, ball_vy, right_x, y_pos, lime_radius
        )
        if hit_right:
            last_touched = "Canada"

    screen.blit(bg_image, (0, 0))
    draw_goal(screen)
    
    # SWAPPED: Draw Bosnia on the Left, Canada on the Right
    draw_rotating_flag(screen, flag_bosnia, left_x, y_pos, lime_radius, -lime_angle, is_left=True)
    draw_rotating_flag(screen, flag_canada, right_x, y_pos, lime_radius, lime_angle, is_left=False)

    if use_image_ball:
        rotated_ball = pygame.transform.rotate(original_ball_img, ball_angle_degrees)
        ball_rect = rotated_ball.get_rect(center=(int(ball_x), int(ball_y)))
        screen.blit(rotated_ball, ball_rect.topleft)
    else:
        draw_drawn_football_fallback(screen, ball_x, ball_y, ball_radius, math.radians(ball_angle_degrees))

    # Updated hook text to match the new order
    h1_text = font_small_text.render("Bosnia & Herzegovina vs Canada!", True, (255, 0, 0))
    h1_shadow = font_small_text.render("Bosnia & Herzegovina vs Canada!", False, (0, 0, 0))
    h1_rect = h1_text.get_rect(center=(WIDTH // 2, 45))
    screen.blit(h1_shadow, (h1_rect.x + 2, h1_rect.y + 2))
    screen.blit(h1_text, h1_rect)

    h2_str = font_small_text.render("First to drop wins the World Cup! ", True, (255, 210, 70))
    h2_shadow = font_small_text.render("First to drop wins the World Cup! ", True, (0, 0, 0))
    h2_emoji = font_small_emoji.render("\U0001F3C6", True, (255, 255, 255))
    
    h2_w = h2_str.get_width() + h2_emoji.get_width()
    h2_x = (WIDTH - h2_w) // 2
    h2_y = 75

    screen.blit(h2_shadow, (h2_x + 2, h2_y + 2))
    screen.blit(h2_str, (h2_x, h2_y))
    screen.blit(h2_emoji, (h2_x + h2_str.get_width(), h2_y - 2))

    if winner:
        win_text = font_huge_text.render(f"{winner} Won!", True, (255, 210, 70)) 
        win_rect = win_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        shadow = font_huge_text.render(f"{winner} Won!", True, (0, 0, 0))
        screen.blit(shadow, (win_rect.x + 4, win_rect.y + 4))
        screen.blit(win_text, win_rect)

    screen.blit(part1, (watermark_start_x, watermark_start_y))
    screen.blit(part2, (watermark_start_x + part1.get_width(), watermark_start_y))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()