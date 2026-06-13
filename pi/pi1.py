import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Set figure size to exactly 430x800 pixels
fig, ax = plt.subplots(figsize=(4.3, 8.0), dpi=100)
fig.patch.set_facecolor('black')
ax.set_facecolor('black')
ax.set_aspect('equal')
ax.axis('off')

ax.set_title("Visualization of Pi being Irrational", color='white', fontsize=12, pad=15)

# --- NEW: Visual marker for the starting point ---
# This draws a subtle green ring at (2, 0) so you can see it almost close the loop!
start_point, = ax.plot([2], [0], 'o', markeredgecolor='#00FF00', markerfacecolor='none', 
                       markersize=6, lw=1.0, alpha=0.6)

# Initialize the lines
arm_line, = ax.plot([], [], 'o-', color='white', lw=1.0, markersize=3, alpha=0.7)
trace_line, = ax.plot([], [], '-', color='white', lw=0.8, alpha=0.9)

equation_text = ax.text(0, -4.0, r'$z(\theta) = e^{\theta i} + e^{\pi \theta i}$', 
                        color='white', fontsize=14, ha='center')

# Variables to store the drawn path
trace_x, trace_y = [], []

# Animation & Speed parameters
frames = 4500               # Extended to give the slow-mo time to play out
base_theta_step = 0.05      
slow_theta_step = 0.0005    # Extremely smooth and slow

# --- THE MATH MAGIC ---
# The first time the arm almost touches the start point is at Theta = 14 * Pi
# At normal speed, this happens around frame 880. We start the slow-mo at frame 840.
zoom_start_frame = 840
zoom_end_frame = 870
base_x_range = 5.0
base_y_range = base_x_range * (800 / 430) 
target_x_range = 0.25       # Extreme close-up
target_y_range = target_x_range * (800 / 430)

# Pre-calculate angles (Bullet-Time Logic)
thetas = np.zeros(frames)
current_theta = 0.0

for i in range(frames):
    if i < zoom_start_frame:
        step = base_theta_step
    elif i >= zoom_end_frame:
        step = slow_theta_step
    else:
        # Smooth transition to slow motion
        t = (i - zoom_start_frame) / (zoom_end_frame - zoom_start_frame)
        progress = t * t * (3 - 2 * t)
        step = base_theta_step + (slow_theta_step - base_theta_step) * progress
        
    current_theta += step
    thetas[i] = current_theta

def init():
    """Initialize the animation with empty data."""
    arm_line.set_data([], [])
    trace_line.set_data([], [])
    ax.set_xlim(-base_x_range/2, base_x_range/2)
    ax.set_ylim(-base_y_range/2, base_y_range/2)
    return arm_line, trace_line, equation_text, start_point

def update(frame):
    """Calculate vectors, update plot, and handle extreme camera zoom."""
    theta = thetas[frame]
    
    # Calculate vector positions
    x1 = np.cos(theta)
    y1 = np.sin(theta)
    
    x2 = x1 + np.cos(np.pi * theta)
    y2 = y1 + np.sin(np.pi * theta)
    
    trace_x.append(x2)
    trace_y.append(y2)
    
    arm_line.set_data([0, x1, x2], [0, y1, y2])
    trace_line.set_data(trace_x, trace_y)
    
    # Extreme camera zoom logic
    if frame < zoom_start_frame:
        progress = 0.0
    elif frame >= zoom_end_frame:
        progress = 1.0
    else:
        t = (frame - zoom_start_frame) / (zoom_end_frame - zoom_start_frame)
        progress = t * t * (3 - 2 * t)
        
    curr_x_range = base_x_range + (target_x_range - base_x_range) * progress
    curr_y_range = base_y_range + (target_y_range - base_y_range) * progress
    
    cx = 0.0 + (x2 - 0.0) * progress
    cy = 0.0 + (y2 - 0.0) * progress
    
    ax.set_xlim(cx - curr_x_range / 2, cx + curr_x_range / 2)
    ax.set_ylim(cy - curr_y_range / 2, cy + curr_y_range / 2)
    
    # Fade out text
    if progress > 0.05:
        equation_text.set_alpha(max(0, 1.0 - progress * 2.5))
        ax.title.set_alpha(max(0, 1.0 - progress * 2.5))
    
    return arm_line, trace_line, equation_text, start_point

# Create the animation
ani = animation.FuncAnimation(
    fig, update, frames=frames, init_func=init, 
    interval=20, blit=False, repeat=False
)

plt.show()