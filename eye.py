import math
import os
import sys
import pygame

# THE POETRY

ring_lines = [
    "i was taught that a window is a wall that learned to listen ",
    "look long enough and the dark begins to read you back ",
    "every language i carry is a lantern and my mother's voice is the oil ",
    "to see is to remember in the light ",
    "open and the world is a poem still deciding what it means ",
    "close and the poem keeps writing itself behind my eyelids ",
    "wonder is the oldest kind of courage ",
]

lid_upper = "what the eye gathers the heart translates into home and into names "
lid_lower = "we are made of everything we have ever looked at with love "

background_lines = [
    "stay curious and the silence will start to speak ",
    "shadows only prove the presence of a light somewhere near ",
    "you are the observer and the observed and the quiet between ",
    "every surface hides a sentence waiting to be read aloud ",
    "breathe in the question and let the answer arrive on its own ",
    "light remembers everything that darkness carries ",
]


# SETTINGS

w, h = 1000, 640
fps = 60
bg = (22, 6, 40)

pygame.init()
screen = pygame.display.set_mode((w, h))
pygame.display.set_caption("Poetry Eye")
clock = pygame.time.Clock()


def make_font(size, bold=False):
    for name in ("georgia", "timesnewroman", "cambria", "serif"):
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size + 6)


font_ring = make_font(17, bold=True)
font_lid = make_font(19, bold=True)
font_bg = make_font(13)


# GLYPH CACHE

_glyphs = {}


def glyph(font, ch, color, angle_deg):
    q = int(round(angle_deg / 3.0)) * 3
    key = (id(font), ch, color, q)
    g = _glyphs.get(key)
    if g is None:
        base = font.render(ch, True, color)
        g = pygame.transform.rotate(base, q)
        _glyphs[key] = g
    return g


def adv(font, ch):
    return font.size(ch)[0] + 1



# IRIS RINGS

def build_ring(text, radius, font):
    """Return list of (char, fraction around the circle) that wraps exactly."""
    circ = 2 * math.pi * radius
    chars, total = [], 0.0
    k = 0
    while total < circ:
        ch = text[k % len(text)]
        chars.append((ch, total))
        total += adv(font, ch)
        k += 1
    return [(ch, pos / total) for ch, pos in chars]


iris_r = 150
pupil_r = 48
ring_radii = [iris_r - 10 - i * 20 for i in range(len(ring_lines))]
ring_radii = [r for r in ring_radii if r > pupil_r + 6]
ring_colors = [
    (255, 120, 180), (200, 110, 240), (255, 160, 200),
    (255, 205, 110), (170, 120, 255), (255, 100, 150),
    (240, 150, 230),
]
rings = []
for i, r in enumerate(ring_radii):
    rings.append({
        "r": r,
        "layout": build_ring(ring_lines[i % len(ring_lines)], r, font_ring),
        "color": ring_colors[i % len(ring_colors)],
        "speed": (0.25 + 0.07 * i) * (1 if i % 2 == 0 else -1),
    })


# BACKGROUND ROWS

row_h = 15
rows = []
for n in range(h // row_h + 1):
    unit = background_lines[n % len(background_lines)]
    unit_w = font_bg.size(unit)[0]
    text = unit
    while font_bg.size(text)[0] < w + unit_w:
        text += unit
    surf = font_bg.render(text, True, (70, 30, 90))
    rows.append({
        "surf": surf,
        "unit_w": unit_w,
        "speed": (12 + (n * 7) % 25) * (1 if n % 2 == 0 else -1),
        "y": n * row_h,
    })


# EYE SHAPE

cx, cy = w // 2, h // 2
half_w = int(w * 0.42)
eye_h = 130


def lid_points(openness, upper, steps=140):
    pts = []
    for i in range(steps + 1):
        u = -1 + 2 * i / steps
        shape = 1 - u * u
        x = cx + u * half_w
        if upper:
            y = cy - eye_h * openness * shape
        else:
            y = cy + eye_h * 0.85 * openness * shape
        pts.append((x, y))
    return pts


def text_on_curve(pts, text, font, color, target):
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + math.dist(pts[i], pts[i - 1]))
    total = cum[-1]
    d, k, j = 0.0, 0, 0
    while True:
        ch = text[k % len(text)]
        w = adv(font, ch)
        mid = d + w / 2
        if mid >= total:
            break
        while j < len(pts) - 2 and cum[j + 1] < mid:
            j += 1
        seg = cum[j + 1] - cum[j]
        t = 0 if seg == 0 else (mid - cum[j]) / seg
        x = pts[j][0] + (pts[j + 1][0] - pts[j][0]) * t
        y = pts[j][1] + (pts[j + 1][1] - pts[j][1]) * t
        ang = math.degrees(math.atan2(pts[j + 1][1] - pts[j][1],
                                      pts[j + 1][0] - pts[j][0]))
        g = glyph(font, ch, color, -ang)
        target.blit(g, g.get_rect(center=(x, y)))
        d += w
        k += 1


def blink_amount(t):
    """1 = fully open, 0 = closed. Blinks every few seconds."""
    period = 4.2
    dur = 0.32
    p = t % period
    if period - dur <= p:
        x = (p - (period - dur)) / dur
        return max(0.0, abs(math.cos(x * math.pi)))
    return 1.0


crease_text = "open the eyes of the dark and ask it to stay "


def draw_lashes(pts, target):
    for i in range(6, len(pts) - 6, 4):
        x, y = pts[i]
        dx = pts[i + 1][0] - pts[i - 1][0]
        dy = pts[i + 1][1] - pts[i - 1][1]
        ln = math.hypot(dx, dy) or 1
        nx, ny = dy / ln, -dx / ln
        u = (x - cx) / half_w
        nx += u * 0.6
        nl = math.hypot(nx, ny)
        nx, ny = nx / nl, ny / nl
        rot = -math.degrees(math.atan2(nx, -ny))
        count = 3 + int(2 * (1 - abs(u)))
        for k in range(count):
            px = x + nx * (9 + k * 6)
            py = y + ny * (9 + k * 6)
            g = glyph(font_ring, "l", (255, 190, 220), rot)
            target.blit(g, g.get_rect(center=(px, py)))


# MAIN LOOP

eye_layer = pygame.Surface((w, h), pygame.SRCALPHA)
mask = pygame.Surface((w, h), pygame.SRCALPHA)
shade = pygame.Surface((w, h), pygame.SRCALPHA)

max_frames = int(os.environ.get("eye_frames", "0"))
frame = 0
running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            running = False

    t = frame / fps
    o = blink_amount(t)

    # background
    screen.fill(bg)
    for row in rows:
        off = (t * row["speed"]) % row["unit_w"]
        screen.blit(row["surf"], (-off, row["y"]))

    # eye contents on their own layer, then masked to the lid shape
    gaze_x = cx + 38 * math.sin(t * 0.45)
    gaze_y = cy + 10 * math.sin(t * 0.31)
    upper = lid_points(o, True)
    lower = lid_points(o, False)

    # the white of the eye, softly tinted
    eye_layer.fill((255, 228, 242, 85))

    # iris: dark at the edge, glowing toward the pupil
    steps = 36
    for i in range(steps):
        f = i / (steps - 1)
        rad = iris_r * (1 - f) + pupil_r * f
        col = (int(30 + 90 * f), int(8 + 30 * f), int(55 + 45 * f), 255)
        pygame.draw.circle(eye_layer, col, (gaze_x, gaze_y), rad)

    # fine fibers running out from the pupil
    for i in range(72):
        a = i * 2 * math.pi / 72 + 0.03 * math.sin(i)
        col = (95, 45, 105, 255) if i % 2 else (125, 80, 95, 255)
        p1 = (gaze_x + (pupil_r + 4) * math.cos(a),
              gaze_y + (pupil_r + 4) * math.sin(a))
        p2 = (gaze_x + (iris_r - 4) * math.cos(a),
              gaze_y + (iris_r - 4) * math.sin(a))
        pygame.draw.line(eye_layer, col, p1, p2, 1)

    # the poetry rings
    for ring in rings:
        base = t * ring["speed"]
        for ch, frac in ring["layout"]:
            a = base + frac * 2 * math.pi
            x = gaze_x + ring["r"] * math.cos(a)
            y = gaze_y + ring["r"] * math.sin(a)
            g = glyph(font_ring, ch, ring["color"], -math.degrees(a) - 90)
            eye_layer.blit(g, g.get_rect(center=(x, y)))

    # dark ring at the edge of the iris, pupil, and little reflections of light
    pygame.draw.circle(eye_layer, (15, 3, 30, 255), (gaze_x, gaze_y), iris_r, 5)
    pulse = pupil_r + 5 * math.sin(t * 1.6)
    pygame.draw.circle(eye_layer, (0, 0, 6, 255), (gaze_x, gaze_y), pulse)
    pygame.draw.circle(eye_layer, (255, 250, 255, 255),
                       (gaze_x - pupil_r * 0.45, gaze_y - pupil_r * 0.5), 9)
    pygame.draw.circle(eye_layer, (255, 235, 245, 255),
                       (gaze_x + pupil_r * 0.35, gaze_y + pupil_r * 0.4), 4)

    # soft shadow the upper lid casts, and a lighter one from the lower lid
    shade.fill((0, 0, 0, 0))
    for k in range(34, 0, -3):
        pts = [(x, y + k) for x, y in upper]
        pygame.draw.lines(shade, (25, 4, 45, int(150 * (1 - k / 36))), False, pts, 4)
    for k in range(18, 0, -3):
        pts = [(x, y - k) for x, y in lower]
        pygame.draw.lines(shade, (25, 4, 45, int(70 * (1 - k / 20))), False, pts, 4)
    eye_layer.blit(shade, (0, 0))

    mask.fill((0, 0, 0, 0))
    pygame.draw.polygon(mask, (255, 255, 255, 255), upper + lower[::-1])
    eye_layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    screen.blit(eye_layer, (0, 0))

    # tear duct in the inner corner
    if o > 0.25:
        pygame.draw.circle(screen, (255, 160, 190), (cx - half_w * 0.9, cy + 4), 6)
        pygame.draw.circle(screen, (255, 110, 150), (cx - half_w * 0.9, cy + 4), 3)

    # the crease above the eye, written in poetry
    crease = []
    for x, y in upper:
        u = (x - cx) / half_w
        crease.append((x, y - (8 + 26 * o) * (1 - u * u) ** 0.6))
    text_on_curve(crease, crease_text, font_bg, (150, 90, 175), screen)

    # eyelids written in poetry, then lashes
    text_on_curve(upper, lid_upper, font_lid, (255, 214, 130), screen)
    text_on_curve(lower, lid_lower, font_lid, (255, 175, 210), screen)
    if o > 0.2:
        draw_lashes(upper, screen)

    pygame.display.flip()
    clock.tick(fps)
    frame += 1
    if max_frames and frame >= max_frames:
        if len(sys.argv) > 1:
            pygame.image.save(screen, sys.argv[1])
        running = False

pygame.quit()