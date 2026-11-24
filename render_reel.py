import os
import sys
import math
import time
import json
import random
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops
import imageio_ffmpeg

# ----------------- CONSTANTS & PATHS -----------------
BASE_DIR = "~/Documents/Google anti-gravity projects/mindset_upgrade_reel"
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
OUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
MASTER_AUDIO = os.path.join(AUDIO_DIR, "master_soundtrack.wav")
OUT_VIDEO = os.path.join(OUT_DIR, "mindset_upgrade_cinematic_reel.mp4")

WIDTH = 1080
HEIGHT = 1920
FPS = 60
DURATION = 30.0
TOTAL_FRAMES = int(DURATION * FPS)  # 1800 frames

# ----------------- FONTS -----------------
FONT_SF_BOLD = "/System/Library/Fonts/SFNS.ttf"
FONT_SF_MONO = "/System/Library/Fonts/SFNSMono.ttf"
FONT_HELV_NEUE = "/System/Library/Fonts/HelveticaNeue.ttc"
FONT_FUTURA = "/System/Library/Fonts/Supplemental/Futura.ttc"
FONT_ARIAL_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_ARIAL_BLACK = "/System/Library/Fonts/Supplemental/Arial Black.ttf"

def get_font(size, style="bold"):
    try:
        if style == "black":
            return ImageFont.truetype(FONT_ARIAL_BLACK, size)
        elif style == "bold":
            return ImageFont.truetype(FONT_SF_BOLD, size)
        elif style == "mono":
            return ImageFont.truetype(FONT_SF_MONO, size)
        elif style == "futura":
            return ImageFont.truetype(FONT_FUTURA, size)
        else:
            return ImageFont.truetype(FONT_HELV_NEUE, size)
    except Exception:
        try:
            return ImageFont.truetype(FONT_ARIAL_BOLD, size)
        except Exception:
            return ImageFont.load_default()

# ----------------- EASING FUNCTIONS -----------------
def ease_out_cubic(x):
    return 1 - (1 - x) ** 3

def ease_in_out_cubic(x):
    return 4 * x * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2

def ease_out_expo(x):
    return 1 if x == 1 else 1 - (2 ** (-10 * x))

def ease_out_back(x, c1=1.70158):
    c3 = c1 + 1
    return 1 + c3 * ((x - 1) ** 3) + c1 * ((x - 1) ** 2)

def clamp(val, min_v=0.0, max_v=1.0):
    return max(min_v, min(max_v, val))

# ----------------- GRAPHIC PRIMITIVES -----------------

def create_radial_gradient(w, h, center_x, center_y, inner_color, outer_color, radius):
    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)
    norm_dist = np.clip(dist_from_center / radius, 0.0, 1.0)
    
    r = (inner_color[0] * (1 - norm_dist) + outer_color[0] * norm_dist).astype(np.uint8)
    g = (inner_color[1] * (1 - norm_dist) + outer_color[1] * norm_dist).astype(np.uint8)
    b = (inner_color[2] * (1 - norm_dist) + outer_color[2] * norm_dist).astype(np.uint8)
    
    rgb = np.dstack((r, g, b))
    return Image.fromarray(rgb, "RGB")

# Pre-generate subtle background particles
random.seed(1337)
NUM_BG_PARTICLES = 60
bg_particles = []
for _ in range(NUM_BG_PARTICLES):
    bg_particles.append({
        "x": random.uniform(0, WIDTH),
        "y": random.uniform(0, HEIGHT),
        "vx": random.uniform(-0.3, 0.3),
        "vy": random.uniform(-0.8, -0.2),
        "size": random.uniform(1.5, 4.5),
        "alpha": random.uniform(40, 160),
        "color": random.choice([(140, 210, 255), (100, 180, 255), (180, 230, 255), (255, 255, 255)])
    })

def overlay_bg_particles(draw, frame_idx):
    for p in bg_particles:
        px = (p["x"] + p["vx"] * frame_idx) % WIDTH
        py = (p["y"] + p["vy"] * frame_idx) % HEIGHT
        sz = p["size"]
        col = (*p["color"], int(p["alpha"] * (0.8 + 0.2 * math.sin(frame_idx * 0.08 + p["x"]))))
        draw.ellipse([px - sz, py - sz, px + sz, py + sz], fill=col)

def draw_hud_decorations(draw, t, section_label="01 // CAPABILITY MATRIX"):
    font_mono = get_font(18, "mono")
    
    # Top Status Bar
    draw.text((60, 70), "APPLE-STYLE KINETIC SYSTEM", fill=(255, 255, 255, 140), font=font_mono)
    draw.text((WIDTH - 300, 70), f"TC: 00:{t:04.1f}s // 60FPS", fill=(120, 200, 255, 180), font=font_mono)
    
    # Subtle corner targeting reticles
    bracket_len = 24
    bracket_col = (255, 255, 255, 80)
    # Top Left
    draw.line([(45, 55), (45 + bracket_len, 55)], fill=bracket_col, width=2)
    draw.line([(45, 55), (45, 55 + bracket_len)], fill=bracket_col, width=2)
    # Top Right
    draw.line([(WIDTH - 45, 55), (WIDTH - 45 - bracket_len, 55)], fill=bracket_col, width=2)
    draw.line([(WIDTH - 45, 55), (WIDTH - 45, 55 + bracket_len)], fill=bracket_col, width=2)
    # Bottom Left
    draw.line([(45, HEIGHT - 65), (45 + bracket_len, HEIGHT - 65)], fill=bracket_col, width=2)
    draw.line([(45, HEIGHT - 65), (45, HEIGHT - 65 - bracket_len)], fill=bracket_col, width=2)
    # Bottom Right
    draw.line([(WIDTH - 45, HEIGHT - 65), (WIDTH - 45 - bracket_len, HEIGHT - 65)], fill=bracket_col, width=2)
    draw.line([(WIDTH - 45, HEIGHT - 65), (WIDTH - 45, HEIGHT - 65 - bracket_len)], fill=bracket_col, width=2)
    
    # Bottom Center Chapter Bar
    draw.text((WIDTH // 2 - 130, HEIGHT - 85), section_label, fill=(180, 200, 230, 140), font=font_mono)

def draw_glass_pill(draw, x0, y0, x1, y1, radius=20, bg_col=(18, 24, 38, 200), border_col=(80, 160, 255, 160), border_w=2):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=bg_col, outline=border_col, width=border_w)

def draw_text_centered(draw, text, y, font, fill=(255, 255, 255, 255), x_center=WIDTH//2, tracking=0):
    lines = text.split("\n")
    total_h = 0
    line_bboxes = []
    for l in lines:
        bb = font.getbbox(l)
        line_bboxes.append(bb)
        total_h += (bb[3] - bb[1]) + 12
    total_h -= 12
    
    curr_y = y - total_h // 2
    for idx, l in enumerate(lines):
        bb = line_bboxes[idx]
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        if tracking == 0:
            draw.text((x_center - tw // 2, curr_y), l, font=font, fill=fill)
        else:
            tot_w = tw + len(l) * tracking
            cx = x_center - tot_w // 2
            for char in l:
                draw.text((cx, curr_y), char, font=font, fill=fill)
                c_bb = font.getbbox(char)
                cx += (c_bb[2] - c_bb[0]) + tracking
        curr_y += th + 12

def apply_glitch_rgb(img, intensity=10, slice_prob=0.3):
    arr = np.array(img)
    h, w, c = arr.shape
    out = arr.copy()
    
    shift_r = int(intensity * (random.random() * 2 - 1))
    if shift_r != 0:
        out[:, :, 0] = np.roll(arr[:, :, 0], shift_r, axis=1)
        
    shift_b = int(intensity * (random.random() * 2 - 1))
    if shift_b != 0:
        out[:, :, 2] = np.roll(arr[:, :, 2], shift_b, axis=1)
        
    if random.random() < slice_prob:
        num_slices = random.randint(2, 6)
        for _ in range(num_slices):
            y_start = random.randint(0, h - 50)
            y_len = random.randint(10, 45)
            x_disp = random.randint(-intensity * 2, intensity * 2)
            out[y_start:y_start+y_len, :, :] = np.roll(out[y_start:y_start+y_len, :, :], x_disp, axis=1)
            
    return Image.fromarray(out)

# ----------------- SCENE RENDERERS -----------------

# 1. SCENE 1: 0.0s – 3.0s (Frames 0 – 180) — STOP-SCROLL HOOK
def render_scene_1(t, frame_idx):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (6, 8, 14, 255))
    
    ambient = create_radial_gradient(WIDTH, HEIGHT, WIDTH//2, HEIGHT//2, (20, 30, 50), (6, 8, 14), 700).convert("RGBA")
    img = Image.alpha_composite(img, ambient)
    draw = ImageDraw.Draw(img)
    overlay_bg_particles(draw, frame_idx)
    
    if t < 0.5:
        # Phase 1: Minimal quiet opening
        f_small = get_font(34, "bold")
        alpha = int(clamp(t / 0.15) * 255)
        draw_text_centered(draw, "AI IS MAKING PEOPLE LAZY.", HEIGHT // 2, f_small, fill=(240, 240, 245, alpha), tracking=3)
        
        # Subtle blinking cursor
        if int(t * 4) % 2 == 0:
            bbox = f_small.getbbox("AI IS MAKING PEOPLE LAZY.")
            tw = bbox[2] - bbox[0]
            draw.rectangle([WIDTH//2 + tw//2 + 10, HEIGHT//2 - 16, WIDTH//2 + tw//2 + 14, HEIGHT//2 + 16], fill=(120, 200, 255, alpha))
            
    elif 0.5 <= t < 0.8:
        # Phase 2: Violent glitch distortion
        f_small = get_font(36, "bold")
        draw_text_centered(draw, "AI IS MAKING PEOPLE L̶A̶Z̶Y̶", HEIGHT // 2 + random.randint(-15, 15), f_small, fill=(255, 80, 80, 240))
        for _ in range(8):
            sy = random.randint(HEIGHT//2 - 100, HEIGHT//2 + 100)
            draw.line([(0, sy), (WIDTH, sy)], fill=(200, 230, 255, 120), width=random.randint(2, 5))
        img = apply_glitch_rgb(img, intensity=25, slice_prob=0.8)
        draw = ImageDraw.Draw(img)
        
    elif 0.8 <= t < 1.8:
        # Phase 3: Monumental "WRONG." impact
        prog = (t - 0.8) / 1.0
        scale = 1.0 + 0.35 * (1.0 - ease_out_cubic(clamp(prog * 2.5))) + (prog * 0.08)
        font_size = int(160 * scale)
        f_wrong = get_font(font_size, "black")
        
        glow_size = int(400 * (1.0 - prog*0.4))
        glow = create_radial_gradient(WIDTH, HEIGHT, WIDTH//2, HEIGHT//2, (255, 60, 80), (6, 8, 14), glow_size).convert("RGBA")
        img = Image.alpha_composite(img, glow)
        draw = ImageDraw.Draw(img)
        
        # Chromatic drop shadow
        draw_text_centered(draw, "WRONG.", HEIGHT // 2 + 8, f_wrong, fill=(255, 40, 70, 160))
        draw_text_centered(draw, "WRONG.", HEIGHT // 2 - 4, f_wrong, fill=(40, 200, 255, 160))
        draw_text_centered(draw, "WRONG.", HEIGHT // 2, f_wrong, fill=(255, 255, 255, 255))
        
        f_sub = get_font(24, "mono")
        draw_text_centered(draw, "[ STOP-SCROLL HOOK // MINDSET SHIFT ]", HEIGHT // 2 + 140, f_sub, fill=(255, 180, 180, int(clamp(prog * 2) * 200)))
        
    else:
        # Phase 4: 1.8s - 3.0s — "AI ISN'T MAKING YOU LESS CAPABLE."
        f_top = get_font(44, "bold")
        draw_text_centered(draw, "AI ISN'T MAKING YOU", HEIGHT // 2 - 90, f_top, fill=(200, 220, 245, 230), tracking=2)
        
        shrink_prog = clamp((t - 2.1) / 0.6)
        less_scale = max(0.001, 1.0 - ease_out_cubic(shrink_prog))
        cap_scale = 1.0 + ease_out_back(shrink_prog) * 0.45
        
        if less_scale > 0.05:
            f_less = get_font(int(52 * less_scale), "bold")
            draw_text_centered(draw, "LESS", HEIGHT // 2 - 15, f_less, fill=(255, 100, 100, int(less_scale * 220)))
            
        f_cap = get_font(int(82 * cap_scale), "black")
        glow_alpha = int(clamp(shrink_prog) * 255)
        draw_text_centered(draw, "CAPABLE.", HEIGHT // 2 + 80, f_cap, fill=(0, 220, 255, glow_alpha))
        draw_text_centered(draw, "CAPABLE.", HEIGHT // 2 + 76, f_cap, fill=(255, 255, 255, 255))

    draw_hud_decorations(draw, t, "01 // THE PARADOX")
    return img.convert("RGB")

# 2. SCENE 2: 3.0s – 7.0s (Frames 180 – 420) — THE PROBLEM (Overload -> Freeze -> Leverage)
CHAOTIC_TASKS = [
    ("I don't know how to start", "BLOCKED"),
    ("Too much manual work", "OVERLOAD"),
    ("Need more time in the day", "TIME TRAP"),
    ("I'm not skilled enough", "DOUBT"),
    ("Where do I even begin?", "FATIGUE"),
    ("Backlog overflowing (34 items)", "CRITICAL"),
    ("Complex codebase architecture", "SCALE"),
    ("Context switching fatigue", "DRAIN"),
    ("Missing technical leverage", "BOTTLENECK")
]

def render_scene_2(t, frame_idx):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (8, 10, 18, 255))
    
    is_frozen = (6.2 <= t < 6.7)
    freeze_t = 6.2 if t >= 6.2 else t
    
    ambient = create_radial_gradient(WIDTH, HEIGHT, WIDTH//2, HEIGHT//2, (18, 28, 48), (8, 10, 18), 850).convert("RGBA")
    img = Image.alpha_composite(img, ambient)
    draw = ImageDraw.Draw(img)
    overlay_bg_particles(draw, frame_idx)
    
    f_task = get_font(24, "bold")
    f_badge_mono = get_font(15, "mono")
    
    # Floating chaotic cards
    num_cards = len(CHAOTIC_TASKS)
    for i, (task_text, tag) in enumerate(CHAOTIC_TASKS):
        angle = (i / num_cards) * 2 * math.pi + (freeze_t * 0.22)
        radius = 240 + (i % 3) * 110
        
        drift_y = math.sin(freeze_t * 1.5 + i) * 55 + (i - num_cards//2) * 95
        card_x = WIDTH // 2 + math.cos(angle) * (radius * 0.85)
        card_y = HEIGHT // 2 + drift_y
        
        entry_t = 3.0 + i * 0.16
        if t < entry_t:
            continue
        card_alpha = int(clamp((t - entry_t) / 0.35) * 210)
        if is_frozen:
            card_alpha = int(card_alpha * 0.45)
            
        bbox = f_task.getbbox(task_text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x, pad_y = 24, 16
        
        bx0 = int(card_x - tw//2 - pad_x - 30)
        by0 = int(card_y - th//2 - pad_y)
        bx1 = int(card_x + tw//2 + pad_x)
        by1 = int(card_y + th//2 + pad_y)
        
        card_col = (14, 18, 30, card_alpha)
        border_col = (255, 90, 90, card_alpha) if i % 2 == 0 else (80, 160, 240, card_alpha)
        draw_glass_pill(draw, bx0, by0, bx1, by1, radius=16, bg_col=card_col, border_col=border_col, border_w=1)
        
        # Tag badge
        draw.rounded_rectangle([bx0 + 12, by0 + 12, bx0 + 85, by1 - 12], radius=6, fill=(255, 60, 60, int(card_alpha*0.8)) if i%2==0 else (40, 120, 220, int(card_alpha*0.8)))
        draw.text((bx0 + 18, by0 + pad_y - 2), tag, font=f_badge_mono, fill=(255, 255, 255, card_alpha))
        draw.text((bx0 + 95, by0 + pad_y - 2), task_text, font=f_task, fill=(240, 245, 255, card_alpha))

    # Center freeze / reveal
    if t >= 5.0:
        focus_alpha = int(clamp((t - 5.0) / 0.7) * 235)
        focus_mask = Image.new("RGBA", (WIDTH, HEIGHT), (6, 8, 14, focus_alpha))
        img = Image.alpha_composite(img, focus_mask)
        draw = ImageDraw.Draw(img)
        
        f_prob = get_font(38, "bold")
        draw_text_centered(draw, "THE PROBLEM WAS NEVER JUST", HEIGHT // 2 - 70, f_prob, fill=(180, 200, 230, 230), tracking=2)
        
        if t < 6.7:
            f_time = get_font(90, "black")
            time_alpha = int(clamp((t - 5.2) / 0.5) * 255)
            if is_frozen:
                draw_text_centered(draw, "TIME.", HEIGHT // 2 + 40, f_time, fill=(255, 80, 80, time_alpha))
            else:
                draw_text_centered(draw, "TIME.", HEIGHT // 2 + 40, f_time, fill=(255, 255, 255, time_alpha))
        else:
            prog_lev = clamp((t - 6.7) / 0.3)
            scale = 1.0 + ease_out_back(prog_lev) * 0.25
            f_lev = get_font(int(105 * scale), "black")
            
            glow = create_radial_gradient(WIDTH, HEIGHT, WIDTH//2, HEIGHT//2 + 40, (0, 220, 255), (8, 10, 18), 350).convert("RGBA")
            img = Image.alpha_composite(img, glow)
            draw = ImageDraw.Draw(img)
            
            draw_text_centered(draw, "LEVERAGE.", HEIGHT // 2 + 40, f_lev, fill=(0, 230, 255, 255))
            draw_text_centered(draw, "LEVERAGE.", HEIGHT // 2 + 36, f_lev, fill=(255, 255, 255, 255))

    draw_hud_decorations(draw, t, "02 // ROOT CAUSE ANALYSIS")
    return img.convert("RGB")

# 3. SCENE 3: 7.0s – 12.0s (Frames 420 – 720) — THE SHIFT (Ecosystem of Capabilities)
CAPABILITIES = [
    ("WRITING", (100, 220, 255)),
    ("RESEARCH", (120, 255, 200)),
    ("DESIGN", (255, 140, 220)),
    ("ANALYSIS", (255, 200, 90)),
    ("CODING", (90, 180, 255)),
    ("LEARNING", (180, 130, 255)),
    ("PLANNING", (255, 110, 140)),
    ("AUTOMATION", (70, 255, 170))
]

def render_scene_3(t, frame_idx):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (6, 9, 16, 255))
    draw = ImageDraw.Draw(img)
    
    # 3D Matrix grid ground
    for gy in range(820, HEIGHT, 50):
        draw.line([(0, gy), (WIDTH, gy)], fill=(30, 50, 80, 70), width=1)
    for gx in range(0, WIDTH, 80):
        draw.line([(gx, 820), (gx, HEIGHT)], fill=(30, 50, 80, 70), width=1)
        
    center_x = WIDTH // 2
    center_y = HEIGHT // 2 + 130
    
    core_glow = create_radial_gradient(WIDTH, HEIGHT, center_x, center_y, (0, 180, 255), (6, 9, 16), 320).convert("RGBA")
    img = Image.alpha_composite(img, core_glow)
    draw = ImageDraw.Draw(img)
    overlay_bg_particles(draw, frame_idx)
    
    # Human Silhouette
    head_y = center_y - 80
    draw.ellipse([center_x - 24, head_y - 24, center_x + 24, head_y + 24], fill=(245, 250, 255, 245))
    body_pts = [(center_x - 38, center_y + 55), (center_x + 38, center_y + 55), (center_x + 26, head_y + 32), (center_x - 26, head_y + 32)]
    draw.polygon(body_pts, fill=(225, 240, 255, 235))
    
    f_step = get_font(34, "bold")
    f_huge = get_font(46, "black")
    
    if t >= 7.1:
        a1 = int(clamp((t - 7.1) / 0.3) * 255)
        draw_text_centered(draw, "ONE PERSON", HEIGHT // 2 - 380, f_step, fill=(180, 200, 230, a1), tracking=2)
    if t >= 7.6:
        a2 = int(clamp((t - 7.6) / 0.3) * 255)
        draw_text_centered(draw, "ONE TOOL", HEIGHT // 2 - 320, f_step, fill=(100, 220, 255, a2), tracking=2)
    if t >= 8.1:
        a3 = int(clamp((t - 8.1) / 0.3) * 255)
        draw_text_centered(draw, "MULTIPLE CAPABILITIES.", HEIGHT // 2 - 250, f_huge, fill=(255, 255, 255, a3), tracking=1)

    # Orbiting modules in 3D
    rot_speed = (t - 8.0) * 0.65
    num_caps = len(CAPABILITIES)
    orbit_rx, orbit_ry = 380, 180
    
    cap_renders = []
    for idx, (cap_name, cap_color) in enumerate(CAPABILITIES):
        entry_time = 8.2 + idx * 0.22
        if t < entry_time:
            continue
        phi = (idx / num_caps) * 2 * math.pi + rot_speed
        cx = center_x + math.cos(phi) * orbit_rx
        cy = center_y + math.sin(phi) * orbit_ry
        depth_z = math.sin(phi)
        scale = 0.8 + 0.3 * (depth_z + 1.0) * 0.5
        alpha = int(clamp((t - entry_time) / 0.3) * (140 + 115 * (depth_z + 1.0) * 0.5))
        cap_renders.append({"name": cap_name, "color": cap_color, "x": cx, "y": cy, "z": depth_z, "scale": scale, "alpha": alpha})
        
    cap_renders.sort(key=lambda item: item["z"])
    draw.ellipse([center_x - orbit_rx, center_y - orbit_ry, center_x + orbit_rx, center_y + orbit_ry], outline=(60, 120, 200, 75), width=2)
    
    for c in cap_renders:
        draw.line([(center_x, center_y - 20), (c["x"], c["y"])], fill=(*c["color"], int(c["alpha"] * 0.6)), width=2)
        f_dyn = get_font(int(22 * c["scale"]), "bold")
        bbox = f_dyn.getbbox(c["name"])
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad_x, pad_y = int(24 * c["scale"]), int(12 * c["scale"])
        bx0 = int(c["x"] - tw//2 - pad_x)
        by0 = int(c["y"] - th//2 - pad_y)
        bx1 = int(c["x"] + tw//2 + pad_x)
        by1 = int(c["y"] + th//2 + pad_y)
        draw_glass_pill(draw, bx0, by0, bx1, by1, radius=int(14 * c["scale"]), bg_col=(14, 20, 34, c["alpha"]), border_col=(*c["color"], c["alpha"]), border_w=2)
        draw.text((bx0 + pad_x, by0 + pad_y - 1), c["name"], font=f_dyn, fill=(245, 250, 255, c["alpha"]))

    if t >= 9.0:
        f_mono = get_font(20, "mono")
        badge_alpha = int(clamp((t - 9.0) / 0.5) * 220)
        draw_text_centered(draw, "TEAM-SCALE AMPLIFICATION // 10X LEVERAGE", HEIGHT - 180, f_mono, fill=(140, 220, 255, badge_alpha))

    draw_hud_decorations(draw, t, "03 // EXPANDED HUMAN CAPABILITY")
    return img.convert("RGB")

# 4. SCENE 4: 12.0s – 17.0s (Frames 720 – 1020) — THE MINDSET RESET (Passive vs Amplified)
MINDSET_COMMANDS = [
    ("AI, HELP ME\nDO MORE.", 12.0, 13.0),
    ("AI, HELP ME\nTHINK BIGGER.", 13.0, 14.0),
    ("AI, HELP ME\nBUILD FASTER.", 14.0, 15.0),
    ("AI, HELP ME\nLEARN FASTER.", 15.0, 16.2),
]

def render_scene_4(t, frame_idx):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (6, 8, 14, 255))
    draw = ImageDraw.Draw(img)
    
    wipe_prog = clamp((t - 16.0) / 0.8)
    split_x = int(WIDTH * (0.5 + wipe_prog * 0.6))
    
    # 1. Left Side (Passive)
    if split_x > 0:
        draw.rectangle([0, 0, split_x, HEIGHT], fill=(16, 18, 24, 255))
        f_pass_lbl = get_font(22, "mono")
        draw.text((70, 320), "OLD MINDSET // PASSIVE", fill=(140, 140, 150, 160), font=f_pass_lbl)
        
        f_passive = get_font(38, "bold")
        pass_alpha = int(clamp(1.0 - (t - 12.0) * 0.25, 0.15, 1.0) * 180)
        draw.text((70, HEIGHT // 2 - 80), "“AI, DO THIS\nFOR ME.”", fill=(160, 165, 175, pass_alpha), font=f_passive)
        
        # Vector bullet points
        bullets_left = ["Replaces human effort", "Creates dependency", "Caps skill ceiling"]
        f_sub_p = get_font(20, "regular")
        for b_idx, b_txt in enumerate(bullets_left):
            by = HEIGHT // 2 + 80 + b_idx * 34
            draw.ellipse([70, by + 6, 78, by + 14], fill=(255, 90, 90, pass_alpha))
            draw.text((90, by), b_txt, fill=(130, 135, 145, pass_alpha), font=f_sub_p)

    # 2. Right Side (Active)
    if split_x < WIDTH:
        draw.rectangle([split_x, 0, WIDTH, HEIGHT], fill=(8, 14, 28, 255))
    
    if wipe_prog < 0.95:
        draw.line([(split_x, 0), (split_x, HEIGHT)], fill=(0, 220, 255, 220), width=3)
        
    if t < 16.0:
        f_act_lbl = get_font(22, "mono")
        draw.text((split_x + 60, 320), "NEW MINDSET // AMPLIFIED", fill=(0, 220, 255, 230), font=f_act_lbl)
        
        for p_text, p_start, p_end in MINDSET_COMMANDS:
            if p_start <= t < p_end:
                beat_prog = (t - p_start) / (p_end - p_start)
                scale = 1.0 + ease_out_back(clamp(beat_prog * 3.0)) * 0.12
                f_active = get_font(int(42 * scale), "black")
                
                ty = HEIGHT // 2 - 80
                draw.text((split_x + 60, ty), p_text, fill=(0, 230, 255, 255), font=f_active)
                draw.text((split_x + 58, ty - 2), p_text, fill=(255, 255, 255, 255), font=f_active)
                
                bullets_right = ["Multiplies potential", "Accelerates build cycle", "Expands capability"]
                f_sub_a = get_font(20, "bold")
                for b_idx, b_txt in enumerate(bullets_right):
                    by = HEIGHT // 2 + 80 + b_idx * 34
                    draw.ellipse([split_x + 60, by + 6, split_x + 68, by + 14], fill=(0, 240, 255, 240))
                    draw.text((split_x + 80, by), b_txt, fill=(180, 235, 255, 220), font=f_sub_a)
                break
    else:
        # 16.0s - 17.0s: ABILITY explodes beyond frame
        prog_ab = (t - 16.0) / 1.0
        scale_ab = 1.0 + ease_out_expo(prog_ab) * 2.2
        
        glow = create_radial_gradient(WIDTH, HEIGHT, WIDTH//2, HEIGHT//2, (0, 180, 255), (6, 8, 14), 600).convert("RGBA")
        img = Image.alpha_composite(img, glow)
        draw = ImageDraw.Draw(img)
        overlay_bg_particles(draw, frame_idx)
        
        f_top = get_font(38, "bold")
        draw_text_centered(draw, "EXPAND YOUR", HEIGHT // 2 - 140, f_top, fill=(200, 230, 255, 240), tracking=3)
        
        f_huge_ab = get_font(int(120 * scale_ab), "black")
        draw_text_centered(draw, "ABILITY", HEIGHT // 2 + 30, f_huge_ab, fill=(0, 240, 255, 220))
        draw_text_centered(draw, "ABILITY", HEIGHT // 2 + 25, f_huge_ab, fill=(255, 255, 255, 255))

    draw_hud_decorations(draw, t, "04 // THE MINDSET RESET")
    return img.convert("RGB")

# 5. SCENE 5: 17.0s – 23.0s (Frames 1020 – 1380) — THE PRODUCTIVITY TRANSFORMATION
WORKFLOW_STEPS = [
    ("AN IDEA.", 17.0, 18.2, (100, 220, 255), "SYNAPSE GENERATION"),
    ("A PLAN.", 18.2, 19.4, (120, 255, 200), "DYNAMIC ROADMAP"),
    ("ACTION.", 19.4, 20.6, (255, 180, 80), "HIGH-VELOCITY EXECUTION"),
    ("OUTPUT.", 20.6, 21.8, (255, 90, 180), "MULTI-MODAL ARTIFACTS"),
]

def render_scene_5(t, frame_idx):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (6, 9, 16, 255))
    draw = ImageDraw.Draw(img)
    
    conduit_y = HEIGHT // 2 + 230
    draw.line([(80, conduit_y), (WIDTH - 80, conduit_y)], fill=(40, 70, 110, 120), width=4)
    pulse_x = 80 + ((t * 450) % (WIDTH - 160))
    draw.line([(max(80, pulse_x - 60), conduit_y), (min(WIDTH - 80, pulse_x + 60), conduit_y)], fill=(0, 240, 255, 255), width=6)
    
    if t < 21.8:
        for s_title, s_start, s_end, s_color, s_sub in WORKFLOW_STEPS:
            if s_start <= t < s_end:
                p = (t - s_start) / (s_end - s_start)
                scale = 1.0 + ease_out_back(clamp(p * 3.0)) * 0.16
                
                glow = create_radial_gradient(WIDTH, HEIGHT, WIDTH//2, HEIGHT//2 - 80, s_color, (6, 9, 16), 420).convert("RGBA")
                img = Image.alpha_composite(img, glow)
                draw = ImageDraw.Draw(img)
                overlay_bg_particles(draw, frame_idx)
                
                f_badge = get_font(22, "mono")
                draw_text_centered(draw, f"[ PIPELINE: {s_sub} ]", HEIGHT // 2 - 220, f_badge, fill=(*s_color, 220), tracking=2)
                
                f_title = get_font(int(96 * scale), "black")
                draw_text_centered(draw, s_title, HEIGHT // 2 - 90, f_title, fill=(*s_color, 240))
                draw_text_centered(draw, s_title, HEIGHT // 2 - 94, f_title, fill=(255, 255, 255, 255))
                
                if s_title == "AN IDEA.":
                    for k in range(6):
                        nx = WIDTH//2 + int(math.cos(k * 1.05 + p*2) * 160)
                        ny = HEIGHT//2 + 80 + int(math.sin(k * 1.05 + p*2) * 70)
                        draw.line([(WIDTH//2, HEIGHT//2 + 80), (nx, ny)], fill=(100, 220, 255, 140), width=2)
                        draw.ellipse([nx-12, ny-12, nx+12, ny+12], fill=(180, 240, 255, 220))
                elif s_title == "A PLAN.":
                    for m in range(4):
                        mx = 180 + m * 240
                        my = HEIGHT//2 + 80
                        draw_glass_pill(draw, mx - 95, my - 28, mx + 95, my + 28, radius=12, bg_col=(18, 28, 45, 200), border_col=(120, 255, 200, 200))
                        draw.text((mx - 55, my - 10), f"PHASE 0{m+1}", fill=(200, 255, 230, 230), font=get_font(16, "mono"))
                elif s_title == "ACTION.":
                    for v in range(5):
                        vy = HEIGHT//2 + 40 + v * 25
                        vx_start = int(140 + p * 220 + v * 30) % WIDTH
                        draw.line([(vx_start, vy), (vx_start + 180, vy)], fill=(255, 180, 80, 220), width=3)
                elif s_title == "OUTPUT.":
                    cards = [("DOCUMENT", "Strategic Architecture"), ("DASHBOARD", "10x Growth Model"), ("UI ENGINE", "Production Deploy"), ("TIMELINE", "Final 4K Master")]
                    for c_i, (c_hdr, c_val) in enumerate(cards):
                        cx = 150 + (c_i % 2) * 400
                        cy = HEIGHT//2 + 10 + (c_i // 2) * 90
                        draw_glass_pill(draw, cx, cy, cx + 370, cy + 72, radius=14, bg_col=(20, 24, 40, 220), border_col=(255, 100, 200, 200))
                        draw.text((cx + 20, cy + 12), c_hdr, fill=(255, 140, 220, 240), font=get_font(15, "mono"))
                        draw.text((cx + 20, cy + 36), c_val, fill=(255, 255, 255, 230), font=get_font(18, "bold"))
                break
    else:
        # 21.8s - 23.0s: THINK → BUILD → LEARN → IMPROVE
        f_hdr = get_font(26, "mono")
        draw_text_centered(draw, "THE EXPONENTIAL FEEDBACK LOOP", HEIGHT // 2 - 260, f_hdr, fill=(140, 220, 255, 220), tracking=2)
        
        loop_words = ["THINK", "BUILD", "LEARN", "IMPROVE"]
        f_loop = get_font(40, "black")
        
        for lw_i, lw in enumerate(loop_words):
            ly = HEIGHT // 2 - 140 + lw_i * 105
            prog_lw = clamp((t - (21.8 + lw_i * 0.25)) / 0.3)
            alpha_lw = int(prog_lw * 255)
            
            draw_glass_pill(draw, WIDTH//2 - 240, ly - 35, WIDTH//2 + 240, ly + 35, radius=18, bg_col=(16, 24, 42, alpha_lw), border_col=(0, 220, 255, alpha_lw), border_w=2)
            draw_text_centered(draw, f"0{lw_i+1}   {lw}", ly, f_loop, fill=(255, 255, 255, alpha_lw), tracking=3)
            
            if lw_i < 3:
                draw.line([(WIDTH//2, ly + 35), (WIDTH//2, ly + 70)], fill=(0, 220, 255, int(alpha_lw * 0.7)), width=2)

    draw_hud_decorations(draw, t, "05 // HIGH-VELOCITY OUTPUT")
    return img.convert("RGB")

# 6. SCENE 6: 23.0s – 27.0s (Frames 1380 – 1620) — THE BIG IDEA (Think With It)
def render_scene_6(t, frame_idx):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (6, 8, 14, 255))
    draw = ImageDraw.Draw(img)
    
    np.random.seed(42)
    node_pts = []
    for _ in range(18):
        node_pts.append((np.random.randint(100, WIDTH - 100), np.random.randint(HEIGHT//2 - 350, HEIGHT//2 + 350)))
    for p1 in node_pts:
        for p2 in node_pts:
            dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
            if dist < 220:
                alpha_net = int((1.0 - dist / 220) * 45)
                draw.line([p1, p2], fill=(80, 160, 255, alpha_net), width=1)
        draw.ellipse([p1[0]-4, p1[1]-4, p1[0]+4, p1[1]+4], fill=(120, 200, 255, 60))

    f_main = get_font(40, "bold")
    f_huge = get_font(68, "black")
    
    if t < 24.6:
        full_text = "THE FUTURE DOESN'T BELONG\nTO PEOPLE WHO USE AI."
        chars_to_show = int(clamp((t - 23.0) / 1.4) * len(full_text))
        typed = full_text[:chars_to_show]
        
        lines = typed.split("\n")
        for l_idx, line in enumerate(lines):
            draw_text_centered(draw, line, HEIGHT // 2 - 40 + l_idx * 65, f_main, fill=(220, 230, 245, 240), tracking=2)
            
        if int(t * 5) % 2 == 0:
            draw.rectangle([WIDTH//2 + 220, HEIGHT//2 + 20, WIDTH//2 + 225, HEIGHT//2 + 65], fill=(0, 220, 255, 240))
            
    elif 24.6 <= t < 25.2:
        draw_text_centered(draw, "THE FUTURE BELONGS TO PEOPLE WHO", HEIGHT // 2 - 80, f_main, fill=(200, 220, 245, 200), tracking=2)
        draw_text_centered(draw, "T̶H̶I̶N̶K̶ ̶W̶I̶T̶H̶ ̶I̶T̶", HEIGHT // 2 + 20, f_huge, fill=(255, 60, 80, 240))
        img = apply_glitch_rgb(img, intensity=20, slice_prob=0.7)
        draw = ImageDraw.Draw(img)
        
    else:
        prog_lock = (t - 25.2) / 1.8
        cam_push = 1.0 + prog_lock * 0.08
        
        aura = create_radial_gradient(WIDTH, HEIGHT, WIDTH//2, HEIGHT//2, (0, 200, 255), (6, 8, 14), 520).convert("RGBA")
        img = Image.alpha_composite(img, aura)
        draw = ImageDraw.Draw(img)
        overlay_bg_particles(draw, frame_idx)
        
        f_top = get_font(int(36 * cam_push), "bold")
        draw_text_centered(draw, "THE FUTURE BELONGS TO PEOPLE WHO", HEIGHT // 2 - 90, f_top, fill=(200, 230, 255, 240), tracking=2)
        
        f_bot = get_font(int(72 * cam_push), "black")
        draw_text_centered(draw, "THINK WITH AI.", HEIGHT // 2 + 30, f_bot, fill=(0, 240, 255, 240), tracking=2)
        draw_text_centered(draw, "THINK WITH AI.", HEIGHT // 2 + 26, f_bot, fill=(255, 255, 255, 255), tracking=2)
        
        f_sub = get_font(20, "mono")
        draw_text_centered(draw, "[ THE COGNITIVE AMPLIFIER // HUMAN + MACHINE ]", HEIGHT // 2 + 150, f_sub, fill=(140, 210, 255, 180))

    draw_hud_decorations(draw, t, "06 // THE STRATEGIC PARADIGM")
    return img.convert("RGB")

# 7. SCENE 7: 27.0s – 30.0s (Frames 1620 – 1800) — FINAL PAYOFF
def render_scene_7(t, frame_idx):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (4, 6, 10, 255))
    draw = ImageDraw.Draw(img)
    
    f_flash = get_font(100, "black")
    
    if 27.0 <= t < 27.4:
        glow = create_radial_gradient(WIDTH, HEIGHT, WIDTH//2, HEIGHT//2, (0, 200, 255), (4, 6, 10), 500).convert("RGBA")
        img = Image.alpha_composite(img, glow)
        draw = ImageDraw.Draw(img)
        draw_text_centered(draw, "MORE TIME.", HEIGHT // 2, f_flash, fill=(0, 240, 255, 255), tracking=2)
        draw_text_centered(draw, "MORE TIME.", HEIGHT // 2 - 4, f_flash, fill=(255, 255, 255, 255), tracking=2)
        
    elif 27.4 <= t < 27.8:
        glow = create_radial_gradient(WIDTH, HEIGHT, WIDTH//2, HEIGHT//2, (180, 100, 255), (4, 6, 10), 500).convert("RGBA")
        img = Image.alpha_composite(img, glow)
        draw = ImageDraw.Draw(img)
        draw_text_centered(draw, "MORE OUTPUT.", HEIGHT // 2, f_flash, fill=(200, 140, 255, 255), tracking=2)
        draw_text_centered(draw, "MORE OUTPUT.", HEIGHT // 2 - 4, f_flash, fill=(255, 255, 255, 255), tracking=2)
        
    elif 27.8 <= t < 28.2:
        glow = create_radial_gradient(WIDTH, HEIGHT, WIDTH//2, HEIGHT//2, (255, 180, 60), (4, 6, 10), 550).convert("RGBA")
        img = Image.alpha_composite(img, glow)
        draw = ImageDraw.Draw(img)
        draw_text_centered(draw, "MORE CAPABILITY.", HEIGHT // 2, get_font(80, "black"), fill=(255, 200, 80, 255), tracking=1)
        draw_text_centered(draw, "MORE CAPABILITY.", HEIGHT // 2 - 4, get_font(80, "black"), fill=(255, 255, 255, 255), tracking=1)
        
    elif 28.2 <= t < 28.4:
        pass
        
    else:
        p_final = (t - 28.4) / 1.6
        cam_zoom = 1.0 + p_final * 0.05
        
        glow = create_radial_gradient(WIDTH, HEIGHT, WIDTH//2, HEIGHT//2, (30, 60, 100), (4, 6, 10), 650).convert("RGBA")
        img = Image.alpha_composite(img, glow)
        draw = ImageDraw.Draw(img)
        overlay_bg_particles(draw, frame_idx)
        
        f_main = get_font(int(54 * cam_zoom), "black")
        draw_text_centered(draw, "“YOUR MINDSET IS", HEIGHT // 2 - 120, f_main, fill=(255, 255, 255, 255), tracking=2)
        draw_text_centered(draw, "THE REAL UPGRADE.”", HEIGHT // 2 - 40, f_main, fill=(0, 230, 255, 255), tracking=2)
        
        div_w = int(180 * clamp(p_final * 2.0))
        draw.line([(WIDTH//2 - div_w, HEIGHT//2 + 40), (WIDTH//2 + div_w, HEIGHT//2 + 40)], fill=(0, 200, 255, 180), width=2)
        
        f_sub = get_font(24, "bold")
        sub_alpha = int(clamp((p_final - 0.2) / 0.5) * 230)
        draw_text_centered(draw, "AI DOESN'T DEFINE YOUR POTENTIAL.", HEIGHT // 2 + 100, f_sub, fill=(200, 220, 245, sub_alpha), tracking=2)
        draw_text_centered(draw, "HOW YOU USE IT DOES.", HEIGHT // 2 + 145, f_sub, fill=(255, 255, 255, sub_alpha), tracking=2)
        
        if t >= 29.7:
            fade_alpha = int(((t - 29.7) / 0.3) * 255)
            fade_mask = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, fade_alpha))
            img = Image.alpha_composite(img, fade_mask)

    draw_hud_decorations(draw, t, "07 // THE REAL UPGRADE")
    return img.convert("RGB")

# ----------------- MASTER FRAME DISPATCHER -----------------

def render_frame(frame_idx):
    t = frame_idx / FPS
    
    if t < 3.0:
        return render_scene_1(t, frame_idx)
    elif t < 7.0:
        return render_scene_2(t, frame_idx)
    elif t < 12.0:
        return render_scene_3(t, frame_idx)
    elif t < 17.0:
        return render_scene_4(t, frame_idx)
    elif t < 23.0:
        return render_scene_5(t, frame_idx)
    elif t < 27.0:
        return render_scene_6(t, frame_idx)
    else:
        return render_scene_7(t, frame_idx)

# ----------------- MAIN VIDEO PIPELINE -----------------

def main():
    print(f"==================================================")
    print(f"🎬 RENDERING 30-SECOND TYPOGRAPHIC REEL (1080x1920 @ 60FPS)")
    print(f"Total frames to generate: {TOTAL_FRAMES}")
    print(f"Master Audio Track: {MASTER_AUDIO}")
    print(f"Output Video Target: {OUT_VIDEO}")
    print(f"==================================================")
    
    start_time = time.time()
    
    cmd = [
        FFMPEG_EXE,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-i", MASTER_AUDIO,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "320k",
        "-shortest",
        OUT_VIDEO
    ]
    
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    
    for idx in range(TOTAL_FRAMES):
        frame_img = render_frame(idx)
        proc.stdin.write(frame_img.tobytes())
        
        if idx % 120 == 0 or idx == TOTAL_FRAMES - 1:
            elapsed = time.time() - start_time
            fps_speed = (idx + 1) / max(0.001, elapsed)
            percent = ((idx + 1) / TOTAL_FRAMES) * 100
            eta = (TOTAL_FRAMES - (idx + 1)) / max(0.001, fps_speed)
            print(f"Frame [{idx+1:4d}/{TOTAL_FRAMES}] ({percent:5.1f}%) | Time: {idx/FPS:4.1f}s | Speed: {fps_speed:4.1f} fps | ETA: {eta:4.1f}s")
            
    proc.stdin.close()
    proc.wait()
    
    total_time = time.time() - start_time
    print(f"\n✨ Video Render Complete in {total_time:.1f}s!")
    print(f"Saved to: {OUT_VIDEO}")

if __name__ == "__main__":
    main()
