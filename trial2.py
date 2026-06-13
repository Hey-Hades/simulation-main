import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pygame


WIDTH, HEIGHT = 450, 800
CENTER = np.array([WIDTH / 2.0, HEIGHT / 2.0], dtype=np.float64)
MARGIN = 42
BG = (0, 0, 0)
MAIN_TEXT = (245, 245, 255)
SUB_TEXT = (170, 170, 190)
HIGHLIGHT = (255, 230, 80)
BOUNDARY_COLOR = (235, 245, 255)
INITIAL_RAY_SPEED = 50.0
SPEED_GAIN_PER_COLLISION = 2.0
MAX_RAY_SPEED = 1000.0
EPSILON = 1e-5
MAX_BOUNCES_PER_FRAME = 12
CURRENT_RAY_RADIUS = 1
INTRO_DURATION = 5.0
INTRO_PARTICLE_COUNT = 900

PALETTE = [
    (255, 35, 35),
    (255, 145, 20),
    (255, 235, 40),
    (35, 255, 90),
    (30, 235, 255),
    (40, 95, 255),
    (155, 45, 255),
    (255, 55, 205),
]


@dataclass(frozen=True)
class SimulationConfig:
    shape_type: str
    ray_count: int
    sides: int | None = None
    acceleration_curve: str = "linear"


def prompt_choice(prompt, options, default=None):
    normalized = {option.lower(): option for option in options}
    first_letters = {option[0].lower(): option for option in options}
    while True:
        value = input(prompt).strip().lower()
        if not value and default is not None:
            return default
        if value in normalized:
            return normalized[value]
        if value in first_letters:
            return first_letters[value]
        print(f"Choose one of: {', '.join(options)}")


def prompt_int(prompt, minimum, maximum=None):
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("Enter a whole number.")
            continue
        if value < minimum:
            print(f"Minimum is {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Maximum is {maximum}.")
            continue
        return value


def load_config():
    print("\nRay Pattern Accumulator")
    print("Shape: circle or polygon")
    shape_type = prompt_choice("Shape type [circle/polygon]: ", ["circle", "polygon"])
    ray_count = prompt_int("Number of rays [10-6000]: ", 10, 6000)
    sides = None
    if shape_type == "polygon":
        sides = prompt_int("Number of polygon sides [minimum 3]: ", 3)
    curve = prompt_choice(
        "Acceleration curve [linear/exponential/logarithmic, default linear]: ",
        ["linear", "exponential", "logarithmic"],
        default="linear",
    )
    return SimulationConfig(shape_type, ray_count, sides, curve)


class Boundary:
    def trace(self, x, y, dx, dy, travel):
        raise NotImplementedError

    def draw(self, surface):
        raise NotImplementedError

    def outline_points(self, count):
        raise NotImplementedError


class CircleBoundary(Boundary):
    def __init__(self, center, radius):
        self.cx = float(center[0])
        self.cy = float(center[1])
        self.radius = float(radius)

    def trace(self, x, y, dx, dy, travel):
        segments = []
        remaining = np.full_like(x, travel)

        for _ in range(MAX_BOUNCES_PER_FRAME):
            active = remaining > EPSILON
            if not np.any(active):
                break

            start_x = x.copy()
            start_y = y.copy()
            px = x - self.cx
            py = y - self.cy

            # Ray-circle intersection. For a unit direction d and interior point
            # p, solve |p + t*d|^2 = r^2 and use the positive root.
            b = px * dx + py * dy
            c = px * px + py * py - self.radius * self.radius
            disc = np.maximum(0.0, b * b - c)
            hit_t = -b + np.sqrt(disc)
            hit = active & (hit_t <= remaining + EPSILON)
            step = np.where(hit, hit_t, remaining)

            x += dx * step
            y += dy * step
            segments.append((start_x, start_y, x.copy(), y.copy(), active.copy(), hit.copy()))
            remaining = np.where(hit, remaining - hit_t, 0.0)

            if not np.any(hit):
                break

            nx = (x - self.cx) / self.radius
            ny = (y - self.cy) / self.radius

            # Perfect specular reflection:
            # r = d - 2(d.n)n, where n is the surface normal at the hit point.
            dot = dx * nx + dy * ny
            dx[hit] -= 2.0 * dot[hit] * nx[hit]
            dy[hit] -= 2.0 * dot[hit] * ny[hit]
            length = np.hypot(dx[hit], dy[hit])
            dx[hit] /= length
            dy[hit] /= length
            x[hit] += dx[hit] * EPSILON
            y[hit] += dy[hit] * EPSILON

        return segments

    def draw(self, surface):
        pygame.draw.circle(
            surface,
            BOUNDARY_COLOR,
            (int(self.cx), int(self.cy)),
            int(self.radius),
            2,
        )

    def outline_points(self, count):
        angles = np.linspace(-math.pi / 2, math.tau - math.pi / 2, count, endpoint=False)
        x = self.cx + np.cos(angles) * self.radius
        y = self.cy + np.sin(angles) * self.radius
        return np.column_stack((x, y))


class PolygonBoundary(Boundary):
    def __init__(self, center, radius, sides):
        self.cx = float(center[0])
        self.cy = float(center[1])
        self.radius = float(radius)
        self.sides = sides
        start_angle = -math.pi / 2
        angles = np.linspace(start_angle, start_angle + math.tau, sides, endpoint=False)
        self.vx = self.cx + np.cos(angles) * self.radius
        self.vy = self.cy + np.sin(angles) * self.radius
        self.wx = np.roll(self.vx, -1)
        self.wy = np.roll(self.vy, -1)
        self.ex = self.wx - self.vx
        self.ey = self.wy - self.vy
        edge_len = np.hypot(self.ex, self.ey)
        self.nx = -self.ey / edge_len
        self.ny = self.ex / edge_len
        self.points = [(int(self.vx[i]), int(self.vy[i])) for i in range(sides)]

    def trace(self, x, y, dx, dy, travel):
        segments = []
        remaining = np.full_like(x, travel)

        for _ in range(MAX_BOUNCES_PER_FRAME):
            active = remaining > EPSILON
            if not np.any(active):
                break

            start_x = x.copy()
            start_y = y.copy()
            best_t = np.full_like(x, np.inf)
            best_nx = np.zeros_like(x)
            best_ny = np.zeros_like(x)

            for ax, ay, ex, ey, nx, ny in zip(self.vx, self.vy, self.ex, self.ey, self.nx, self.ny):
                denom = dx * ey - dy * ex
                valid = np.abs(denom) > 1e-12
                apx = ax - x
                apy = ay - y
                t_num = apx * ey - apy * ex
                u_num = apx * dy - apy * dx
                t = np.divide(t_num, denom, out=np.full_like(x, np.inf), where=valid)
                u = np.divide(u_num, denom, out=np.full_like(x, np.inf), where=valid)
                on_segment = valid & (t > EPSILON) & (u >= -1e-9) & (u <= 1.0 + 1e-9)
                finite_best = np.isfinite(best_t)
                t_delta = np.full_like(x, np.inf)
                np.subtract(t, best_t, out=t_delta, where=on_segment & finite_best)
                same_vertex_hit = on_segment & finite_best & (np.abs(t_delta) <= 1e-7)
                best_nx = np.where(same_vertex_hit, best_nx + nx, best_nx)
                best_ny = np.where(same_vertex_hit, best_ny + ny, best_ny)
                candidate = on_segment & (t < best_t - 1e-7)
                best_t = np.where(candidate, t, best_t)
                best_nx = np.where(candidate, nx, best_nx)
                best_ny = np.where(candidate, ny, best_ny)

            normal_length = np.hypot(best_nx, best_ny)
            has_normal = normal_length > 1e-12
            best_nx = np.divide(best_nx, normal_length, out=best_nx, where=has_normal)
            best_ny = np.divide(best_ny, normal_length, out=best_ny, where=has_normal)

            hit = active & (best_t <= remaining + EPSILON)
            step = np.where(hit, best_t, remaining)
            x += dx * step
            y += dy * step
            segments.append((start_x, start_y, x.copy(), y.copy(), active.copy(), hit.copy()))
            remaining = np.where(hit, remaining - best_t, 0.0)

            if not np.any(hit):
                break

            # Reversing the normal gives the same mirror result, so edge normal
            # orientation does not matter for perfect reflection.
            dot = dx * best_nx + dy * best_ny
            dx[hit] -= 2.0 * dot[hit] * best_nx[hit]
            dy[hit] -= 2.0 * dot[hit] * best_ny[hit]
            length = np.hypot(dx[hit], dy[hit])
            dx[hit] /= length
            dy[hit] /= length
            x[hit] += dx[hit] * EPSILON
            y[hit] += dy[hit] * EPSILON

        return segments

    def draw(self, surface):
        pygame.draw.polygon(surface, BOUNDARY_COLOR, self.points, 2)

    def outline_points(self, count):
        edge_lengths = np.hypot(self.ex, self.ey)
        perimeter = float(np.sum(edge_lengths))
        distances = np.linspace(0.0, perimeter, count, endpoint=False)
        cumulative = np.cumsum(edge_lengths)
        edge_indices = np.searchsorted(cumulative, distances, side="right")
        edge_start_dist = np.concatenate(([0.0], cumulative[:-1]))[edge_indices]
        amount = (distances - edge_start_dist) / edge_lengths[edge_indices]
        x = self.vx[edge_indices] + self.ex[edge_indices] * amount
        y = self.vy[edge_indices] + self.ey[edge_indices] * amount
        return np.column_stack((x, y))


class RayField:
    def __init__(self, config):
        self.config = config
        self.colors = [PALETTE[i % len(PALETTE)] for i in range(config.ray_count)]
        self.reset()

    def reset(self):
        angles = np.linspace(0.0, math.tau, self.config.ray_count, endpoint=False)
        self.x = np.full(self.config.ray_count, CENTER[0], dtype=np.float64)
        self.y = np.full(self.config.ray_count, CENTER[1], dtype=np.float64)
        self.dx = np.cos(angles).astype(np.float64)
        self.dy = np.sin(angles).astype(np.float64)
        self.speed = np.full(self.config.ray_count, INITIAL_RAY_SPEED, dtype=np.float64)
        self.collision_count = np.zeros(self.config.ray_count, dtype=np.int32)
        self.charge = np.zeros(self.config.ray_count, dtype=np.float64)

    def apply_speed_progression(self, segments):
        for *_, hit in segments:
            if np.any(hit):
                self.collision_count[hit] += 1

        if self.config.acceleration_curve == "exponential":
            normalized = np.expm1(self.collision_count * 0.018) / np.expm1(9.0)
            target_speed = INITIAL_RAY_SPEED + (MAX_RAY_SPEED - INITIAL_RAY_SPEED) * normalized
        elif self.config.acceleration_curve == "logarithmic":
            normalized = np.log1p(self.collision_count * 0.18) / np.log1p(85.5)
            target_speed = INITIAL_RAY_SPEED + (MAX_RAY_SPEED - INITIAL_RAY_SPEED) * normalized
        else:
            target_speed = INITIAL_RAY_SPEED + self.collision_count * SPEED_GAIN_PER_COLLISION

        np.minimum(target_speed, MAX_RAY_SPEED, out=self.speed)
        self.charge = (self.speed - INITIAL_RAY_SPEED) / (MAX_RAY_SPEED - INITIAL_RAY_SPEED)

    def update(self, boundary, dt):
        segments = boundary.trace(self.x, self.y, self.dx, self.dy, self.speed * dt)
        self.apply_speed_progression(segments)
        return segments


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


class IntroAnimation:
    def __init__(self, config, boundary):
        self.config = config
        self.boundary = boundary
        self.title_font = pygame.font.SysFont("arial", 36, bold=True)
        self.subtitle_font = pygame.font.SysFont("arial", 17)
        self.title = self.make_title()
        self.subtitles = [
            "Every ray starts at the center.",
            "Every wall is perfectly reflective.",
            "The pattern records every path forever.",
        ]
        self.title_surface = self.title_font.render(self.title, True, MAIN_TEXT)
        self.title_rect = self.title_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 55))
        self.text_points = self.sample_title_points(INTRO_PARTICLE_COUNT)
        self.shape_points = self.boundary.outline_points(INTRO_PARTICLE_COUNT)
        self.colors = [PALETTE[i % len(PALETTE)] for i in range(INTRO_PARTICLE_COUNT)]
        self.bloom = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    def make_title(self):
        if self.config.shape_type == "polygon":
            return f"{self.config.ray_count} Rays in a Perfect Polygon"
        return "Ray Reflection Patterns"

    def sample_title_points(self, count):
        alpha = pygame.surfarray.array_alpha(self.title_surface)
        ys, xs = np.nonzero(alpha > 20)
        if len(xs) == 0:
            return np.repeat(CENTER.reshape(1, 2), count, axis=0)

        order = np.linspace(0, len(xs) - 1, count, dtype=np.int32)
        sampled_x = xs[order] + self.title_rect.left
        sampled_y = ys[order] + self.title_rect.top
        points = np.column_stack((sampled_x, sampled_y)).astype(np.float64)

        # Keep particles from collapsing into scanline order by rotating the
        # sampled text points through a deterministic modular stride.
        stride = 37
        permutation = (np.arange(count) * stride) % count
        return points[permutation]

    def draw_text_reveal(self, surface, elapsed):
        reveal = smoothstep(elapsed / 1.35)
        width = max(1, int(self.title_surface.get_width() * reveal))
        source_rect = pygame.Rect(0, 0, width, self.title_surface.get_height())
        surface.blit(self.title_surface, self.title_rect, source_rect)

        subtitle_index = min(len(self.subtitles) - 1, int(max(0.0, elapsed - 0.8) / 0.7))
        subtitle_progress = smoothstep((elapsed - 0.8 - subtitle_index * 0.7) / 0.6)
        subtitle_text = self.subtitles[subtitle_index]
        subtitle_surface = self.subtitle_font.render(subtitle_text, True, SUB_TEXT)
        subtitle_surface.set_alpha(int(255 * subtitle_progress))
        subtitle_rect = subtitle_surface.get_rect(center=(WIDTH // 2, self.title_rect.bottom + 28))
        surface.blit(subtitle_surface, subtitle_rect)

    def draw_particles(self, surface, elapsed):
        morph_t = smoothstep((elapsed - 2.05) / 2.25)
        points = self.text_points + (self.shape_points - self.text_points) * morph_t
        particle_alpha = int(40 + 215 * smoothstep((elapsed - 1.35) / 0.75))
        radius = 1 if morph_t < 0.88 else 2

        self.bloom.fill((0, 0, 0, 0))
        for idx, point in enumerate(points):
            color = self.colors[idx]
            pos = (int(point[0]), int(point[1]))
            pygame.draw.circle(self.bloom, (color[0], color[1], color[2], 45), pos, radius + 3)
            pygame.draw.circle(surface, (color[0], color[1], color[2], particle_alpha), pos, radius)

        surface.blit(self.bloom, (0, 0), special_flags=pygame.BLEND_ADD)

    def draw_source_glow(self, surface, elapsed):
        source_t = smoothstep((elapsed - 4.15) / 0.65)
        if source_t <= 0:
            return
        center = (int(CENTER[0]), int(CENTER[1]))
        for radius, alpha in ((34, 22), (20, 48), (8, 180)):
            scaled = max(1, int(radius * source_t))
            pygame.draw.circle(surface, (255, 245, 180, int(alpha * source_t)), center, scaled)

    def draw_boundary_emergence(self, surface, elapsed):
        alpha = int(255 * smoothstep((elapsed - 3.9) / 0.7))
        if alpha <= 0:
            return
        boundary_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.boundary.draw(boundary_layer)
        boundary_layer.set_alpha(alpha)
        surface.blit(boundary_layer, (0, 0))

    def draw(self, surface, elapsed):
        surface.fill(BG)
        if elapsed < 2.1:
            self.draw_text_reveal(surface, elapsed)
        else:
            ghost = self.title_surface.copy()
            ghost.set_alpha(int(90 * max(0.0, 1.0 - smoothstep((elapsed - 2.1) / 0.9))))
            surface.blit(ghost, self.title_rect)

        if elapsed >= 1.2:
            self.draw_particles(surface, elapsed)

        self.draw_boundary_emergence(surface, elapsed)
        self.draw_source_glow(surface, elapsed)
        pygame.display.flip()

    @property
    def complete(self):
        return False


class AccumulatorRenderer:
    def __init__(self, screen, config, boundary):
        self.screen = screen
        self.config = config
        self.boundary = boundary
        self.accumulation = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.dynamic = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.small_font = pygame.font.SysFont("arial", 15)
        self.watermark_font = pygame.font.SysFont("arial", 26)
        self.use_aa = config.ray_count <= 1400

    def clear(self):
        self.accumulation.fill((0, 0, 0, 0))
        self.dynamic.fill((0, 0, 0, 0))

    def draw_accumulated_segments(self, segments, colors, charge):
        line = pygame.draw.aaline if self.use_aa else pygame.draw.line
        for sx, sy, ex, ey, active, _hit in segments:
            active_indices = np.flatnonzero(active)
            for idx in active_indices:
                base = colors[idx]
                alpha = min(255, int(135 + charge[idx] * 100))
                color = (base[0], base[1], base[2], alpha)
                p0 = (int(sx[idx]), int(sy[idx]))
                p1 = (int(ex[idx]), int(ey[idx]))
                line(self.accumulation, color, p0, p1)

    def draw_current_rays(self, x, y, colors, charge):
        self.dynamic.fill((0, 0, 0, 0))
        active_count = len(x)
        step = 1 if active_count <= 1800 else max(1, active_count // 1800)
        for idx in range(0, active_count, step):
            base = colors[idx]
            radius = CURRENT_RAY_RADIUS + int(charge[idx] > 0.72)
            color = (base[0], base[1], base[2], 230)
            pygame.draw.circle(self.dynamic, color, (int(x[idx]), int(y[idx])), radius)

    def draw_ui(self, elapsed, paused):
        shape_text = self.config.shape_type.title()
        if self.config.sides is not None:
            shape_text = f"{shape_text} ({self.config.sides} sides)"
        status = "Paused" if paused else "Accumulating"
        info = [
            f"Shape: {shape_text}",
            f"Rays: {self.config.ray_count}",
            f"Curve: {self.config.acceleration_curve.title()}",
            f"Time: {elapsed:5.1f}s",
            status,
        ]

        y = 18
        for item in info:
            label = self.small_font.render(item, True, MAIN_TEXT)
            self.screen.blit(label, (18, y))
            y += 22

        part1 = self.watermark_font.render("@ B o u n c e ", True, SUB_TEXT)
        part2 = self.watermark_font.render("C u l t", True, HIGHLIGHT)
        total_width = part1.get_width() + part2.get_width()
        start_x = (WIDTH // 2) - (total_width // 2)
        y_pos = HEIGHT - 58
        self.screen.blit(part1, (start_x, y_pos))
        self.screen.blit(part2, (start_x + part1.get_width(), y_pos))

    def present(self, rays, elapsed, paused):
        self.screen.fill(BG)
        self.screen.blit(self.accumulation, (0, 0), special_flags=pygame.BLEND_ADD)
        self.draw_current_rays(rays.x, rays.y, rays.colors, rays.charge)
        self.screen.blit(self.dynamic, (0, 0), special_flags=pygame.BLEND_ADD)
        self.boundary.draw(self.screen)
        self.draw_ui(elapsed, paused)
        pygame.display.flip()


class Simulation:
    def __init__(self, config):
        pygame.init()
        pygame.display.set_caption("BounceCult Ray Pattern Accumulator")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        radius = min(WIDTH, HEIGHT) / 2 - MARGIN
        if config.shape_type == "circle":
            self.boundary = CircleBoundary(CENTER, radius)
        else:
            self.boundary = PolygonBoundary(CENTER, radius, config.sides)
        self.config = config
        self.rays = RayField(config)
        self.renderer = AccumulatorRenderer(self.screen, config, self.boundary)
        self.paused = False
        self.elapsed = 0.0
        self.running = True

    def reset(self):
        self.rays.reset()
        self.renderer.clear()
        self.elapsed = 0.0

    def save_screenshot(self):
        output_dir = Path("screenshots")
        output_dir.mkdir(exist_ok=True)
        path = output_dir / f"ray_pattern_accumulator_{pygame.time.get_ticks()}.png"
        pygame.image.save(self.screen, str(path))
        print(f"Saved screenshot: {path}")

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_r:
                    self.reset()
                elif event.key == pygame.K_s:
                    self.save_screenshot()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            self.handle_events()

            if not self.paused:
                self.elapsed += dt
                segments = self.rays.update(self.boundary, dt)
                self.renderer.draw_accumulated_segments(segments, self.rays.colors, self.rays.charge)

            self.renderer.present(self.rays, self.elapsed, self.paused)

        pygame.quit()


def main():
    config = load_config()
    Simulation(config).run()


if __name__ == "__main__":
    main()