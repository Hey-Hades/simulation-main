import pygame
import sys
import math

# --- 1. Initialize Pygame ---
pygame.init()

# --- 2. Constants & Setup ---
WIDTH, HEIGHT = 450, 800  
FPS = 60
BG_COLOR = (0, 0, 0)       

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Viral Lime Simulation")
clock = pygame.time.Clock()

# --- Cross-Platform Font Fixing ---
text_fonts = ["arial", "dejavusans", "liberationsans", "sans"]
font_large_text = pygame.font.SysFont(text_fonts, 34, bold=True) 
font_small_text = pygame.font.SysFont(text_fonts, 22, bold=True)

emoji_fonts = ["segoeuiemoji", "notocoloremoji", "applecoloremoji", "dejavusans"]
font_large_emoji = pygame.font.SysFont(emoji_fonts, 35) 
font_like_emoji = pygame.font.SysFont(emoji_fonts, 31)  

# --- 3. Pre-Render Watermark ---
part1 = font_small_text.render("@ B o u n c e ", True, (245, 245, 245)) 
part2 = font_small_text.render("C u l t", True, (255, 210, 70))
total_watermark_width = part1.get_width() + part2.get_width()
max_watermark_height = max(part1.get_height(), part2.get_height())
watermark_start_x = (WIDTH - total_watermark_width) // 2
watermark_start_y = HEIGHT - max_watermark_height - 100

# --- 4. Environment Variables (The Limes) ---
min_gap = 53      
# Dynamically calculate radius so centers on the edges maintain the exact gap: (430 - 55) / 2 = 187.5
lime_radius = (WIDTH - min_gap) / 2  
y_pos = HEIGHT // 2 + 50 

# Start slightly off-screen so they visually slide inward at launch
left_x = -lime_radius // 2
right_x = WIDTH + lime_radius // 2
lime_speed = 0.8
lime_angle = 0.0      
rotation_speed = 0.01 

# --- 5. Object Variables (The Like Button) ---
ball_radius = 26.50 
INITIAL_X, INITIAL_Y = WIDTH // 2, 120
INITIAL_VX, INITIAL_VY = 4.5, 0

ball_x, ball_y = INITIAL_X, INITIAL_Y 
ball_vx, ball_vy = INITIAL_VX, INITIAL_VY 
gravity = 0.36

# Counter
likes = 0 

# --- Helper Functions ---
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
            # Perfect elastic bounce (Speed is kept perfectly constant)
            bvx -= 2 * dot_product * nx
            bvy -= 2 * dot_product * ny
            return bx, by, bvx, bvy, True 
            
    return bx, by, bvx, bvy, False 

def draw_rotating_lime(surface, x, y, radius, angle, is_left):
    rind_color = (77, 139, 49)      
    flesh_color = (160, 223, 93)    
    line_color = (217, 240, 196)    
    
    # Cast radius to int to ensure clean drawing circles
    int_rad = int(radius)
    pygame.draw.circle(surface, flesh_color, (int(x), int(y)), int_rad)
    pygame.draw.circle(surface, rind_color, (int(x), int(y)), int_rad, 15)
    
    for i in range(8):
        theta = angle + i * (math.pi / 4)
        end_x = x + radius * math.cos(theta)
        end_y = y + radius * math.sin(theta)
        pygame.draw.line(surface, line_color, (x, y), (end_x, end_y), 5)
        
    if is_left:
        pygame.draw.rect(surface, BG_COLOR, (int(x) - int_rad - 20, y - int_rad - 20, int_rad + 20, int_rad * 2 + 40))
    else:
        pygame.draw.rect(surface, BG_COLOR, (int(x), y - int_rad - 20, int_rad + 20, int_rad * 2 + 40))

# --- 6. Main Game Loop ---
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- Update Environment ---
    if left_x < 0:
        left_x += lime_speed
        right_x -= lime_speed
    else:
        left_x = 0
        right_x = WIDTH

    lime_angle += rotation_speed

    # --- Update Ball ---
    ball_vy += gravity
    ball_x += ball_vx
    ball_y += ball_vy

    # Top Imaginary Boundary Collision
    if ball_y - ball_radius < 0:
        ball_y = ball_radius
        ball_vy *= -1

    # Left and Right Wall Collisions
    if ball_x - ball_radius < 0:
        ball_x = ball_radius
        ball_vx *= -1
    elif ball_x + ball_radius > WIDTH:
        ball_x = WIDTH - ball_radius
        ball_vx *= -1
        
    # Bottom Reset Logic
    if ball_y - ball_radius > HEIGHT:
        ball_x = INITIAL_X
        ball_y = INITIAL_Y
        ball_vx = INITIAL_VX
        ball_vy = INITIAL_VY
        likes = 0  # <--- Resets counter back to "?" when it falls off screen

    # --- Collision & Likes Logic ---
    ball_x, ball_y, ball_vx, ball_vy, hit_left = resolve_collision(
        ball_x, ball_y, ball_vx, ball_vy, left_x, y_pos, lime_radius
    )
    ball_x, ball_y, ball_vx, ball_vy, hit_right = resolve_collision(
        ball_x, ball_y, ball_vx, ball_vy, right_x, y_pos, lime_radius
    )
    
    if hit_left or hit_right:
        likes += 1 

    # --- Drawing ---
    screen.fill(BG_COLOR)

    # Draw Limes
    draw_rotating_lime(screen, left_x, y_pos, lime_radius, lime_angle, is_left=True)
    draw_rotating_lime(screen, right_x, y_pos, lime_radius, -lime_angle, is_left=False)

    # Draw Ball
    pygame.draw.circle(screen, (59, 89, 152), (int(ball_x), int(ball_y)), int(ball_radius))
    thumb_text = font_like_emoji.render("\U0001F44D", True, (255, 255, 255)) 
    screen.blit(thumb_text, thumb_text.get_rect(center=(int(ball_x), int(ball_y))))

    # Draw Center Text
    text_part = font_large_text.render("I don't think it will ", True, (255, 255, 255))
    emoji_part = font_large_emoji.render("\U0001F97A", True, (255, 255, 255)) 
    
    center_text_width = text_part.get_width() + emoji_part.get_width()
    center_start_x = (WIDTH - center_text_width) // 2
    center_y = HEIGHT // 2
    
    screen.blit(text_part, (center_start_x, center_y - text_part.get_height() // 2))
    screen.blit(emoji_part, (center_start_x + text_part.get_width(), center_y - emoji_part.get_height() // 2))

    # Draw Top Text (Likes)
    prefix_text = font_small_text.render("This video will get ", True, (255, 255, 255))
    if likes == 0:
        k_text = font_large_text.render("? ", True, (232, 192, 81)) 
    else:
        k_text = font_large_text.render(f"{likes}", True, (232, 192, 81)) 
    suffix_text = font_small_text.render(" subscribers!", True, (255, 255, 255))

    total_width = prefix_text.get_width() + k_text.get_width() + suffix_text.get_width()
    start_x = (WIDTH - total_width) // 2
    
    screen.blit(prefix_text, (start_x, 120))
    screen.blit(k_text, (start_x + prefix_text.get_width(), 110)) 
    screen.blit(suffix_text, (start_x + prefix_text.get_width() + k_text.get_width(), 120))

    # --- Draw Watermark (Bottom Center) ---
    screen.blit(part1, (watermark_start_x, watermark_start_y))
    screen.blit(part2, (watermark_start_x + part1.get_width(), watermark_start_y))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()