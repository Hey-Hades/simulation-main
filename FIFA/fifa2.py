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
# Decreased radius so the two edge-centered disks leave a gap in the middle
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

def create_korea_flag(radius):
    """Draws an accurate Republic of Korea flag with a perfectly circular Taegeuk."""
    w = h = radius * 2
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((255, 255, 255)) 
    
    cx, cy = w // 2, h // 2
    
    # 1. Draw Central Taegeuk (S-curve)
    t_radius = int(radius * 0.42)
    taegeuk_surf = pygame.Surface((t_radius * 2, t_radius * 2), pygame.SRCALPHA)
    
    pygame.draw.circle(taegeuk_surf, (0, 71, 160), (t_radius, t_radius), t_radius)
    
    taegeuk_surf.set_clip(pygame.Rect(0, 0, t_radius * 2, t_radius))
    pygame.draw.circle(taegeuk_surf, (205, 46, 58), (t_radius, t_radius), t_radius)
    taegeuk_surf.set_clip(None) 
    
    pygame.draw.circle(taegeuk_surf, (0, 71, 160), (t_radius // 2, t_radius), t_radius // 2)
    pygame.draw.circle(taegeuk_surf, (205, 46, 58), (t_radius + t_radius // 2, t_radius), t_radius // 2)
    
    rotated_taegeuk = pygame.transform.rotate(taegeuk_surf, -45)
    taegeuk_rect = rotated_taegeuk.get_rect(center=(cx, cy))
    surf.blit(rotated_taegeuk, taegeuk_rect.topleft)
    
    # 2. Draw Trigrams
    bar_w = int(radius * 0.22)
    bar_h = int(radius * 0.035)
    bar_gap = int(radius * 0.015)
    space_gap = int(radius * 0.02) 
    
    def make_trigram(bars):
        total_th = 3 * bar_h + 2 * bar_gap
        tsurf = pygame.Surface((bar_w, total_th), pygame.SRCALPHA)
        y = 0
        for is_solid in bars:
            if is_solid:
                pygame.draw.rect(tsurf, (30, 30, 30), (0, y, bar_w, bar_h))
            else:
                half_w = (bar_w - space_gap) // 2
                pygame.draw.rect(tsurf, (30, 30, 30), (0, y, half_w, bar_h))
                pygame.draw.rect(tsurf, (30, 30, 30), (half_w + space_gap, y, half_w, bar_h))
            y += bar_h + bar_gap
        return tsurf

    geon = make_trigram([True, True, True])
    gam = make_trigram([False, True, False])
    ri = make_trigram([True, False, True])
    gon = make_trigram([False, False, False])
    
    dist = radius * 0.68 
    
    def blit_trigram(tsurf, angle_deg, corner_angle_rad):
        tx = cx + dist * math.cos(corner_angle_rad)
        ty = cy + dist * math.sin(corner_angle_rad)
        rot_surf = pygame.transform.rotate(tsurf, angle_deg)
        rect = rot_surf.get_rect(center=(int(tx), int(ty)))
        surf.blit(rot_surf, rect.topleft)
        
    blit_trigram(geon, 45, math.radians(225))   
    blit_trigram(gam, -45, math.radians(315))   
    blit_trigram(ri, 135, math.radians(135))    
    blit_trigram(gon, -135, math.radians(45))   
    
    return apply_circular_mask(surf, radius)

def create_czechia_flag(radius):
    """Draws the Czechia flag."""
    w = h = radius * 2
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    
    pygame.draw.rect(surf, (255, 255, 255), (0, 0, w, h//2))
    pygame.draw.rect(surf, (215, 20, 26), (0, h//2, w, h//2))
    pygame.draw.polygon(surf, (17, 69, 126), [(0, 0), (0, h), (w//2, h//2)])
    
    return apply_circular_mask(surf, radius)

flag_korea = create_korea_flag(lime_radius)
flag_czechia = create_czechia_flag(lime_radius)

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
        # --- Update Environment ---
        # The disks are fixed to the sides, so we only rotate them
        lime_angle += rotation_speed

        # --- Update Ball ---
        ball_vy += gravity
        ball_x += ball_vx
        ball_y += ball_vy
        
        ball_angle_degrees -= ball_vx * 0.5 

        # Wall Bounces
        if ball_x - ball_radius < 0: 
            ball_x = ball_radius
            ball_vx *= -1
        elif ball_x + ball_radius > WIDTH:
            ball_x = WIDTH - ball_radius
            ball_vx *= -1
            
        # Win Condition: Ball drops into the goal net
        if ball_y > HEIGHT - 40: 
            if last_touched:
                winner = last_touched
            else:
                ball_y = -50
                ball_vy = 0
                ball_x = WIDTH // 2

        # --- Collision Logic ---
        ball_x, ball_y, ball_vx, ball_vy, hit_left = resolve_collision(
            ball_x, ball_y, ball_vx, ball_vy, left_x, y_pos, lime_radius
        )
        if hit_left:
            last_touched = "Republic of Korea"
            
        ball_x, ball_y, ball_vx, ball_vy, hit_right = resolve_collision(
            ball_x, ball_y, ball_vx, ball_vy, right_x, y_pos, lime_radius
        )
        if hit_right:
            last_touched = "Czechia"

    # --- Drawing ---
    screen.blit(bg_image, (0, 0))
    draw_goal(screen)

    # Draw Flags 
    draw_rotating_flag(screen, flag_korea, left_x, y_pos, lime_radius, -lime_angle, is_left=True)
    draw_rotating_flag(screen, flag_czechia, right_x, y_pos, lime_radius, lime_angle, is_left=False)

    # Draw Ball (Image Sprite vs Fallback)
    if use_image_ball:
        rotated_ball = pygame.transform.rotate(original_ball_img, ball_angle_degrees)
        ball_rect = rotated_ball.get_rect(center=(int(ball_x), int(ball_y)))
        screen.blit(rotated_ball, ball_rect.topleft)
    else:
        draw_drawn_football_fallback(screen, ball_x, ball_y, ball_radius, math.radians(ball_angle_degrees))

    # --- DRAW TOP HOOK TEXT ---
    h1_text = font_small_text.render("Republic of Korea vs Czechia!", True, (255, 0, 0))
    h1_shadow = font_small_text.render("Republic of Korea vs Czechia!", False, (0, 0, 0))
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

    # --- Draw Dynamic Text Content ---
    if winner:
        win_text = font_huge_text.render(f"{winner} Won!", True, (255, 210, 70)) 
        win_rect = win_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        shadow = font_huge_text.render(f"{winner} Won!", True, (0, 0, 0))
        screen.blit(shadow, (win_rect.x + 4, win_rect.y + 4))
        screen.blit(win_text, win_rect)

    # --- Draw Watermark (Bottom Center) ---
    screen.blit(part1, (watermark_start_x, watermark_start_y))
    screen.blit(part2, (watermark_start_x + part1.get_width(), watermark_start_y))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()