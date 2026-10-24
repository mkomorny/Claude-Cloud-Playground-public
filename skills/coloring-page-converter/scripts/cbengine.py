#!/usr/bin/env python3
"""
cbengine.py - DigiDreamWeaver coloring book engine (the ONE shared copy).

Used by the skills:
  coloring-page-converter      -> `convert`
  coloring-page-colorways      -> `colorize`
  coloring-book-pipeline       -> `pipeline` (convert + colorize + package)
  digidreamweaver-shop-pipeline-> `pipeline` + `listing` / `catalog` / `queue` /
                                  `mark` / `gumroad-checklist` / `gumroad-sync` /
                                  `pinterest-post`

Rules baked in (from the Grokbot / DigiDreamWeaver conversation):
  * pure black lines on pure white, no gray / shading / hatching / solid fills
  * every region closed (bucket-fill safe), no fingertip-impossible cells
  * original aspect ratio, never crop / stretch / squish
  * >= 4096 px long side, 300 DPI
  * previews watermarked with tiled diagonal "PREVIEW DigiDreamWeaver";
    buyer files never watermarked
  * preview order: 0 blank -> 1 realistic -> 2..5 creative

Requires: Python 3.10+, numpy, opencv-python, pillow, scipy.
Optional: realesrgan-ncnn-vulkan (AI upscale), potrace (SVG). Auto-detected.
"""
from __future__ import annotations

import argparse
import base64
import colorsys
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None

CANONICAL_PROMPT = """[TASK]
Convert the provided reference image into an original, high-precision digital coloring page. 

[AESTHETIC & ART STYLE]
- Style: Crisp digital pen-and-ink line art with a semi-realistic storybook finish.
- Line Rendering: 100% solid, fully opaque black lines (#000000) on a flat, pure white background (#FFFFFF).
- Contrast: Binary monochrome. Zero grayscale values, zero pencil grain, zero charcoal texture, zero faded/sketchy strokes, zero halftones, zero airbrushing, and zero drop shadows.
- Stroke Modulation: Maintain a clean hierarchy with medium-weight outer contour strokes for primary silhouettes and slightly thinner, uniform inner strokes for secondary surface details.

[BUCKET-FILL OPTIMIZATION (CRITICAL)]
- Closed Boundaries: Every single drawn shape, contour, seam, and detail must form a completely closed path. 
- Leak Prevention: There must be zero open vertices, micro-gaps, or broken outlines anywhere in the canvas. Every distinct area must be independently fillable with a single digital paint bucket tap without color leaking into adjacent regions.
- Tap Targets: Eliminate any enclosed area that is too microscopic to tap easily on a standard tablet screen. Group, simplify, or merge tiny details into coherent, colorable islands.

[COMPOSITION & SUBJECT FIDELITY]
- Framing & Aspect Ratio: Exactly preserve the composition, camera perspective, framing, horizon line, and spatial placement of all subjects from the reference image. Do not crop, squeeze, stretch, or rearrange elements.
- Translation of Realism: Translate complex organic elements (such as fur, clouds, foliage, water reflections, crater surfaces, and fabric folds) into stylized, graphic vector-like boundary lines rather than photorealistic shading or hatching.
- Feature Simplification: Omit atmospheric noise, photographic motion blur, diffuse lighting glares, lens flares, dust motes, and soft transparency gradients. Turn distinct silhouettes into clear line enclosures.

[TECHNICAL CONSTRAINTS & NEGATIVE DIRECTIVES]
- STRICT NEGATIVES: No color, no gray tones, no anti-aliasing blur, no feathered edges, no sketchy underdrawings, no cross-hatching, no stippling, no screentone dots, no solid black fills (except pupils where essential), no broken lines, no open loops, no artistic distress textures.
- OUTPUT SPECIFICATIONS: Razor-sharp edge definition, 4096 px minimum long edge, flat white background."""

SHOP = os.environ.get("CB_SHOP_NAME", "DigiDreamWeaver")
DEFAULT_ROOT = os.environ.get("CB_OUTPUT_ROOT", r"C:\Users\<you>\OneDrive\Pictures\Coloring Book")
DEFAULT_ORIGINALS_DIR = os.environ.get("CB_ORIGINALS_DIR", r"C:\Users\<you>\OneDrive\Pictures\coloring book originals - translate")
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
DPI = 300

# detail preset -> (kmeans colors, min-cell multiplier of a fingertip)
DETAIL = {"low": (6, 3.0), "medium": (8, 1.0), "high": (12, 0.6), "ultra": (16, 0.35)}

# Creative palettes, ordered dark -> light. "bg" = index used for the background region.
PALETTES = {
    "pastel":      {"c": ["7a8fb5", "a0c4ff", "bdb2ff", "ffc6ff", "caffbf", "fdffb6", "ffd6a5", "fff1e6"], "bg": -1},
    "jewel":       {"c": ["1b0f3b", "3a0ca3", "7209b7", "0f7173", "087e8b", "c9184a", "f2a541", "f7d08a"], "bg": -1},
    "neon":        {"c": ["0d0221", "541388", "ff006e", "fb5607", "3a86ff", "00f5d4", "ffbe0b", "f1fffa"], "bg": 0},
    "mono_accent": {"c": ["1f1f1f", "3d3d3d", "6b6b6b", "9a9a9a", "c8c8c8", "ececec"], "bg": -1, "accent": "e63946"},
    "ocean":       {"c": ["0b2545", "13315c", "134074", "1b6ca8", "3fa7d6", "8dd3e8", "cdeff6", "eaf8fb"], "bg": -1},
    "sunset":      {"c": ["3d0c11", "7a1c1c", "b23a48", "e4572e", "f28c38", "f6b26b", "fbd38d", "fdf1d6"], "bg": -1},
    "candy":       {"c": ["6a0572", "c9184a", "ff5d8f", "ff8fab", "9bf6ff", "ffb3c6", "caffbf", "fdffb6"], "bg": -1},
    "autumn":      {"c": ["3b1f0e", "6f2dbd", "9c2c13", "c4521b", "dd8a2e", "e9b44c", "f3d9a4", "fbf3e4"], "bg": -1},
    "forest":      {"c": ["0b2d1f", "1e4d2b", "386641", "6a994e", "a7c957", "d4a373", "e9edc9", "f7f5ea"], "bg": -1},
    "iridescent":  {"c": ["2b2d72", "5a4fcf", "7b9fff", "6ee7f9", "a7f3d0", "f9a8d4", "fde68a", "f5f3ff"], "bg": -1},
}
DEFAULT_CREATIVE = ["pastel", "jewel", "neon", "mono_accent"]


# ----------------------------------------------------------------------------- utils
def log(*a):
    print("[cbengine]", *a, flush=True)


def safe_name(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return (s[:60] or "Page")


def title_from_name(name: str) -> str:
    return " ".join(w.capitalize() if not w.isupper() else w for w in name.replace("_", " ").split())


def seed_of(name: str) -> int:
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16) & 0x7FFFFFFF


def load_rgb(path: str) -> np.ndarray:
    im = Image.open(path)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        im = bg
    return np.array(im.convert("RGB"))


def resize_long(img: np.ndarray, L: int, interp=cv2.INTER_CUBIC) -> np.ndarray:
    h, w = img.shape[:2]
    s = L / max(h, w)
    if abs(s - 1) < 1e-6:
        return img
    return cv2.resize(img, (max(1, round(w * s)), max(1, round(h * s))), interpolation=interp)


def ellipse(r: int):
    r = max(1, int(r))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))


def fingertip_area(h: int, w: int) -> float:
    """Pixel area of a fingertip-sized cell when the page is zoomed-to-fit on an iPad (~45px of 2732)."""
    return (max(h, w) * 0.0165) ** 2


def font(size: int, bold=True):
    names = ["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]
    for n in names + ["DejaVuSans-Bold.ttf", "DejaVuSans.ttf"]:
        for p in (os.path.join(r"C:\Windows\Fonts", n), n):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    return ImageFont.load_default(size)


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_json(path, default=None):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


# ----------------------------------------------------------------------------- optional tools
def find_tool(name, env):
    p = os.environ.get(env) or shutil.which(name)
    return p if p and os.path.exists(p) else None


def ai_upscale(rgb: np.ndarray, scale=4) -> np.ndarray | None:
    exe = find_tool("realesrgan-ncnn-vulkan", "REALESRGAN_EXE")
    if not exe:
        return None
    with tempfile.TemporaryDirectory() as td:
        i, o = os.path.join(td, "in.png"), os.path.join(td, "out.png")
        Image.fromarray(rgb).save(i)
        try:
            subprocess.run([exe, "-i", i, "-o", o, "-n", "realesrgan-x4plus-anime", "-s", str(scale)],
                           check=True, capture_output=True)
            log("Real-ESRGAN anime x4 upscale applied")
            return load_rgb(o)
        except Exception as e:  # noqa
            log("Real-ESRGAN failed, falling back to Lanczos:", e)
            return None


def upscale_to(rgb: np.ndarray, L: int, use_ai=True) -> np.ndarray:
    if max(rgb.shape[:2]) >= L:
        return resize_long(rgb, L, cv2.INTER_AREA)
    if use_ai:
        up = ai_upscale(rgb)
        if up is not None:
            return resize_long(up, L, cv2.INTER_AREA if max(up.shape[:2]) > L else cv2.INTER_CUBIC)
    return resize_long(rgb, L, cv2.INTER_LANCZOS4)


def vectorize(ink: np.ndarray, svg_path: str) -> bool:
    exe = find_tool("potrace", "POTRACE_EXE")
    if not exe:
        return False
    with tempfile.TemporaryDirectory() as td:
        bmp = os.path.join(td, "in.bmp")
        Image.fromarray(np.where(ink, 0, 255).astype(np.uint8)).convert("1").save(bmp)
        try:
            subprocess.run([exe, bmp, "-s", "-o", svg_path], check=True, capture_output=True)
            return True
        except Exception as e:  # noqa
            log("potrace failed:", e)
            return False


# ----------------------------------------------------------------------------- logo removal
def remove_logo(rgb: np.ndarray, corner: str, frac=0.10) -> np.ndarray:
    """Inpaint a light, low-saturation watermark/logo (e.g. Gemini sparkle) in a corner."""
    if corner in (None, "none"):
        return rgb
    h, w = rgb.shape[:2]
    bh, bw = int(h * frac), int(w * frac)
    ys = slice(h - bh, h) if corner[0] == "b" else slice(0, bh)
    xs = slice(w - bw, w) if corner[1] == "r" else slice(0, bw)
    box = rgb[ys, xs]
    hsv = cv2.cvtColor(box, cv2.COLOR_RGB2HSV)
    v, s = hsv[..., 2].astype(int), hsv[..., 1].astype(int)
    med = np.median(v)
    mask = ((v > med + 18) & (s < 60)) | ((v < med - 18) & (s < 40) & (med > 200))
    mask = cv2.morphologyEx(mask.astype(np.uint8) * 255, cv2.MORPH_OPEN, ellipse(1))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask)
    keep = np.zeros_like(mask)
    for i in range(1, n):  # logo = compact blob not touching the inner edges of the box
        x, y, ww, hh, a = stats[i]
        if a > 30 and ww < bw * 0.9 and hh < bh * 0.9:
            keep[lab == i] = 255
    if keep.any():
        keep = cv2.dilate(keep, ellipse(max(2, bw // 120)))
        out = rgb.copy()
        out[ys, xs] = cv2.inpaint(box, keep, 5, cv2.INPAINT_TELEA)
        log(f"logo removed in corner {corner}")
        return out
    return rgb


# ----------------------------------------------------------------------------- line-art helpers
def is_lineart(rgb: np.ndarray) -> bool:
    small = resize_long(rgb, 800, cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    g = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    white = (g > 200).mean()
    mid = ((g > 60) & (g < 200)).mean()
    return white > 0.5 and hsv[..., 1].mean() < 40 and mid < 0.25


def stroke_width(ink: np.ndarray) -> float:
    if not ink.any():
        return 0.0
    d = cv2.distanceTransform(ink.astype(np.uint8), cv2.DIST_L2, 5)
    ridge = (d >= cv2.dilate(d, np.ones((3, 3), np.uint8))) & (d > 0)
    return float(2 * np.median(d[ridge])) if ridge.any() else 0.0


def remove_small(mask: np.ndarray, min_area: float, conn=8) -> np.ndarray:
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=conn)
    keep = np.zeros(n, bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_area
    return keep[lab]


def fill_small_white(ink: np.ndarray, max_area: float) -> np.ndarray:
    """Pockets too small to color become ink (bucket fill would never reach them)."""
    white = (~ink).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(white, connectivity=4)
    small = np.zeros(n, bool)
    small[1:] = stats[1:, cv2.CC_STAT_AREA] < max_area
    return ink | small[lab]


def hollow_solids(ink: np.ndarray, line_px: float) -> np.ndarray:
    """Turn solid black fills into outlines (rule: no solid black fills)."""
    d = cv2.distanceTransform(ink.astype(np.uint8), cv2.DIST_L2, 5)
    core = d > line_px * 1.6
    if not core.any():
        return ink
    solid = cv2.dilate(core.astype(np.uint8), ellipse(line_px * 1.6)).astype(bool) & ink
    interior = cv2.erode(solid.astype(np.uint8), ellipse(max(1, line_px))).astype(bool)
    log(f"hollowed {int(interior.sum())} px of solid fill")
    return ink & ~interior


def smooth_ink(ink: np.ndarray, sigma: float) -> np.ndarray:
    f = cv2.GaussianBlur(ink.astype(np.float32), (0, 0), sigma)
    return f > 0.5


def default_line_px(L: int) -> int:
    return max(3, round(L / 650))


# ----------------------------------------------------------------------------- TRACE mode
def kmeans_classes(rgb: np.ndarray, k: int, seed=0) -> np.ndarray:
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    sm = cv2.bilateralFilter(bgr, 9, 60, 60)
    sm = cv2.bilateralFilter(sm, 9, 40, 40)
    sm = cv2.medianBlur(sm, 5)
    lab = cv2.cvtColor(sm, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    rng = np.random.default_rng(seed)
    sample = lab[rng.choice(len(lab), min(len(lab), 200_000), replace=False)]
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5)
    cv2.setRNGSeed(seed)
    _, _, centers = cv2.kmeans(sample, k, None, crit, 3, cv2.KMEANS_PP_CENTERS)
    out = np.empty(len(lab), np.uint8)
    c2 = (centers ** 2).sum(1)
    for i in range(0, len(lab), 400_000):
        x = lab[i:i + 400_000]
        out[i:i + 400_000] = (c2[None, :] - 2 * x @ centers.T).argmin(1)
    return out.reshape(rgb.shape[:2])


def majority_smooth(cl: np.ndarray, k: int, ksize: int) -> np.ndarray:
    best = np.zeros(cl.shape, np.float32)
    out = cl.copy()
    for c in range(k):
        m = cv2.blur((cl == c).astype(np.float32), (ksize, ksize))
        upd = m > best
        out[upd] = c
        best[upd] = m[upd]
    return out


def regions_from_classes(cl: np.ndarray, k: int) -> np.ndarray:
    reg = np.zeros(cl.shape, np.int32)
    nxt = 1
    for c in range(k):
        n, lab = cv2.connectedComponents((cl == c).astype(np.uint8), connectivity=4)
        m = lab > 0
        reg[m] = lab[m] + (nxt - 1)
        nxt += n - 1
    return reg


def merge_small_regions(reg: np.ndarray, min_area: float, iters=5) -> np.ndarray:
    for _ in range(iters):
        sizes = np.bincount(reg.ravel())
        small = sizes[reg] < min_area
        if not small.any() or small.all():
            break
        idx = ndi.distance_transform_edt(small, return_distances=False, return_indices=True)
        reg = reg[idx[0], idx[1]]
    return reg


def region_boundaries(reg: np.ndarray) -> np.ndarray:
    e = np.zeros(reg.shape, bool)
    e[:, 1:] |= reg[:, 1:] != reg[:, :-1]
    e[1:, :] |= reg[1:, :] != reg[:-1, :]
    return e


def trace_lineart(rgb: np.ndarray, L: int, detail: str, line_px: int, use_ai=True, seed=0) -> np.ndarray:
    k, mult = DETAIL[detail]
    work_L = 2048
    work = upscale_to(rgb, work_L, use_ai)
    h, w = work.shape[:2]
    min_area = fingertip_area(h, w) * mult
    log(f"trace: work {w}x{h}, k={k}, min_area={min_area:.0f}px")
    cl = kmeans_classes(work, k, seed)
    cl = majority_smooth(cl, k, 7)
    reg = regions_from_classes(cl, k)
    reg = merge_small_regions(reg, min_area)
    edges = region_boundaries(reg)
    # render boundaries at target resolution with uniform, smooth stroke
    s = L / max(h, w)
    H, W = round(h * s), round(w * s)
    up = cv2.resize(edges.astype(np.uint8) * 255, (W, H), interpolation=cv2.INTER_LINEAR) > 64
    d = cv2.distanceTransform((~up).astype(np.uint8), cv2.DIST_L2, 5)
    ink = d <= max(0.5, line_px / 2 - s / 2)
    ink = smooth_ink(ink, max(1.0, s * 0.6))
    return ink


# ----------------------------------------------------------------------------- CLEAN mode
def clean_lineart(rgb: np.ndarray, L: int, line_px: int, gap: int, use_ai=True, keep_solids=False) -> np.ndarray:
    up = upscale_to(rgb, L, use_ai)
    g = cv2.cvtColor(up, cv2.COLOR_RGB2GRAY)
    s = L / max(rgb.shape[:2])
    g = cv2.GaussianBlur(g, (0, 0), max(0.6, s * 0.45))
    t, _ = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    t = float(np.clip(t, 110, 200))
    ink = g < t
    ink = remove_small(ink, (line_px * 2.2) ** 2)          # dust / specks / sparkle
    if gap > 0:
        ink = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, ellipse(gap)).astype(bool)
    if not keep_solids:
        ink = hollow_solids(ink, line_px)
    sw = stroke_width(ink)
    if sw and sw < line_px * 0.75:
        ink = cv2.dilate(ink.astype(np.uint8), ellipse(max(1, round((line_px - sw) / 2)))).astype(bool)
        log(f"thickened strokes {sw:.1f}px -> ~{line_px}px")
    ink = smooth_ink(ink, max(1.0, line_px * 0.25))
    return ink


# ----------------------------------------------------------------------------- QC
def qc_report(ink: np.ndarray, page_dir: str | None = None) -> dict:
    h, w = ink.shape
    white = (~ink).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(white, connectivity=4)
    areas = stats[1:, cv2.CC_STAT_AREA]
    tip = fingertip_area(h, w)
    sw = stroke_width(ink)
    d = cv2.distanceTransform(ink.astype(np.uint8), cv2.DIST_L2, 5)
    largest = float(areas.max() / ink.size) if len(areas) else 0
    tiny = int((areas < tip * 0.5).sum())
    rep = {
        "size": [w, h],
        "long_side_px": max(w, h),
        "dpi": DPI,
        "pure_black_white": True,
        "fill_regions": int(n - 1),
        "smallest_region_px": int(areas.min()) if len(areas) else 0,
        "fingertip_cell_px": int(tip),
        "regions_below_half_fingertip": tiny,
        "largest_region_fraction": round(largest, 3),
        "stroke_width_px": round(sw, 2),
        "max_solid_black_px": round(float(d.max() * 2), 1),
        "ink_fraction": round(float(ink.mean()), 4),
    }
    warns = []
    if max(w, h) < 4096:
        warns.append("long side < 4096 px")
    if n - 1 and tiny / (n - 1) > 0.03:
        warns.append(f"{tiny} cells smaller than half a fingertip - lower detail or raise min area")
    if largest > 0.6:
        warns.append("one region covers >60% of the page - possible leak (open line) or very sparse art")
    if sw and d.max() * 2 > sw * 4:
        warns.append("solid black areas detected")
    if n - 1 < 25:
        warns.append("very few fill regions - page may be too simple")
    rep["warnings"] = warns
    rep["status"] = "PASS" if not warns else "WARN"
    if page_dir:
        cy, cx = h // 2, w // 2
        crop = ink[cy - h // 8: cy + h // 8, cx - w // 8: cx + w // 8]
        Image.fromarray(np.where(crop, 0, 255).astype(np.uint8)).save(os.path.join(page_dir, "qc_zoom_400.png"))
        write_json(os.path.join(page_dir, "qc_report.json"), rep)
    return rep


# ----------------------------------------------------------------------------- watermark & layout
def watermark(img: Image.Image, text: str | None = None, opacity=0.22, angle=30) -> Image.Image:
    text = text or f"PREVIEW  {SHOP}"
    W, H = img.size
    fs = max(14, int(min(W, H) / 16))
    diag = int(math.hypot(W, H)) + fs * 4
    layer = Image.new("RGBA", (diag, diag), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font(fs)
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
    tw, th = x1 - x0, y1 - y0
    sx, sy = int(tw + fs * 2.5), int(th + fs * 2.4)
    a = int(255 * opacity)
    for row, y in enumerate(range(0, diag, sy)):
        off = (row % 2) * sx // 2
        for x in range(-sx + off, diag, sx):
            d.text((x, y), text, font=f, fill=(55, 55, 55, a),
                   stroke_width=max(1, fs // 16), stroke_fill=(255, 255, 255, int(a * 0.85)))
    layer = layer.rotate(angle, resample=Image.BICUBIC)
    l, t = (diag - W) // 2, (diag - H) // 2
    out = img.convert("RGBA")
    out.alpha_composite(layer.crop((l, t, l + W, t + H)))
    return out.convert("RGB")


def fit(im: Image.Image, w: float, h: float) -> Image.Image:
    s = min(w / im.width, h / im.height)
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)


def save_preview(img: Image.Image, path: str, preview_long: int):
    if preview_long and max(img.size) > preview_long:
        img = fit(img, preview_long, preview_long) if img.width == img.height else \
            img.resize((round(img.width * preview_long / max(img.size)), round(img.height * preview_long / max(img.size))), Image.LANCZOS)
    watermark(img).save(path, quality=90)


def compose_pin(blank: Image.Image, colors: list[Image.Image], W=1000, H=1500, footer=72, pad=14) -> Image.Image:
    """Tall pin: blank page on top, colorways below. Nothing is ever cropped."""
    avail = H - footer
    n = len(colors)
    bw, bh = blank.size
    best = None
    for top in [0.38, 0.42, 0.46, 0.5, 0.55, 0.6, 0.65, 0.7]:
        th = avail * top
        for cols in range(1, max(1, n) + 1):
            rows = math.ceil(n / cols) if n else 0
            s_top = min((W - 2 * pad) / bw, (th - 2 * pad) / bh)
            if n:
                cw = (W - pad * (cols + 1)) / cols
                ch = (avail - th - pad * (rows + 1)) / rows
                if cw <= 0 or ch <= 0:
                    continue
                s_cell = min(cw / bw, ch / bh)
            else:
                s_cell = 0
            score = s_top ** 2 + 0.8 * n * s_cell ** 2
            if n and s_cell < 0.28 * s_top:
                score *= 0.5
            if best is None or score > best[0]:
                best = (score, th, cols)
    _, th, cols = best
    canvas = Image.new("RGB", (W, H), "white")
    t = fit(blank, W - 2 * pad, th - 2 * pad)
    canvas.paste(t, ((W - t.width) // 2, int((th - t.height) / 2)))
    if n:
        rows = math.ceil(n / cols)
        cw = (W - pad * (cols + 1)) / cols
        ch = (avail - th - pad * (rows + 1)) / rows
        for i, c in enumerate(colors):
            r, k = divmod(i, cols)
            in_row = min(cols, n - r * cols)
            x0 = (W - (in_row * cw + (in_row - 1) * pad)) / 2 + k * (cw + pad)
            y0 = th + pad + r * (ch + pad)
            ci = fit(c, cw, ch)
            canvas.paste(ci, (int(x0 + (cw - ci.width) / 2), int(y0 + (ch - ci.height) / 2)))
    canvas = watermark(canvas, opacity=0.16)
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, H - footer, W, H], fill=(24, 24, 32))
    label = f"{SHOP}  \u2022  Digital Coloring Page  \u2022  Procreate \u00b7 iPad \u00b7 Printable"
    f = font(26)
    tw = d.textlength(label, font=f)
    d.text(((W - tw) / 2, H - footer + (footer - 30) / 2), label, font=f, fill=(255, 255, 255))
    return canvas


def compose_cover(blank: Image.Image, colors: list[Image.Image], W=1280, H=720, pad=14) -> Image.Image:
    """Gumroad cover: blank left, 2x2 colorways right, original shape."""
    canvas = Image.new("RGB", (W, H), "white")
    lw = W * 0.5
    b = fit(blank, lw - 2 * pad, H - 2 * pad)
    canvas.paste(b, (int((lw - b.width) / 2), int((H - b.height) / 2)))
    cw, ch = (W - lw - 3 * pad) / 2, (H - 3 * pad) / 2
    for i, c in enumerate(colors[:4]):
        r, k = divmod(i, 2)
        ci = fit(c, cw, ch)
        x0, y0 = lw + pad + k * (cw + pad), pad + r * (ch + pad)
        canvas.paste(ci, (int(x0 + (cw - ci.width) / 2), int(y0 + (ch - ci.height) / 2)))
    return watermark(canvas, opacity=0.16)


def compose_split_thumb(blank: Image.Image, colored: Image.Image, S=1000) -> Image.Image:
    """Square thumbnail: same art, left half blank / right half colored (before-after)."""
    b, c = blank.convert("RGB"), colored.convert("RGB").resize(blank.size)
    w = b.width
    ba = b.copy()
    ba.paste(c.crop((w // 2, 0, w, b.height)), (w // 2, 0))
    d = ImageDraw.Draw(ba)
    d.line([(w // 2, 0), (w // 2, b.height)], fill=(255, 255, 255), width=max(3, w // 300))
    canvas = Image.new("RGB", (S, S), "white")
    t = fit(ba, S - 40, S - 40)
    canvas.paste(t, ((S - t.width) // 2, (S - t.height) // 2))
    return watermark(canvas, opacity=0.14)


# ----------------------------------------------------------------------------- page I/O
def page_paths(page_dir: str, name: str) -> dict:
    p = lambda f: os.path.join(page_dir, f)  # noqa
    return {
        "master_png": p(f"{name}_full_white.png"),
        "white_jpg": p(f"{name}_full_white.jpg"),
        "transparent_png": p(f"{name}_full_transparent.png"),
        "svg": p(f"{name}.svg"),
        "ipad_white": p(f"{name}_iPad_white.jpg"),
        "ipad_transparent": p(f"{name}_iPad_transparent.png"),
        "pdf_letter": p(f"{name}_print_Letter.pdf"),
        "pdf_a4": p(f"{name}_print_A4.pdf"),
        "pin": p(f"{name}_pin_1000x1500.jpg"),
        "cover": p(f"{name}_cover_1280x720.jpg"),
        "thumb": p(f"{name}_thumb_square.jpg"),
        "wm_dir": p("watermarked"),
        "pal_dir": p("palettes"),
        "page_json": p("page.json"),
        "prompt_txt": p("prompt.txt"),
    }


def load_ink(page_dir: str, name: str) -> np.ndarray:
    g = np.array(Image.open(page_paths(page_dir, name)["master_png"]).convert("L"))
    return g < 128


def resolve_page(arg: str) -> tuple[str, str]:
    """Accept a page folder or a *_full_white.png path; return (page_dir, name)."""
    if os.path.isdir(arg):
        meta = read_json(os.path.join(arg, "page.json"), {})
        name = meta.get("name") or os.path.basename(os.path.normpath(arg))
        return arg, name
    m = re.match(r"(.+)_full_white\.png$", os.path.basename(arg))
    if m:
        return os.path.dirname(arg), m.group(1)
    raise SystemExit(f"Not a page folder or *_full_white.png: {arg}")


# ----------------------------------------------------------------------------- CONVERT
def cmd_convert(a) -> tuple[str, str]:
    if not a.input:
        orig_dir = getattr(a, "originals_dir", None) or DEFAULT_ORIGINALS_DIR
        if os.path.isdir(orig_dir):
            cands = [os.path.join(orig_dir, f) for f in os.listdir(orig_dir)
                     if os.path.splitext(f)[1].lower() in IMG_EXT]
            if cands:
                cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                a.input = cands[0]
                log(f"no input path provided, auto-selected newest original: {a.input}")
            else:
                raise SystemExit(f"no input path provided and no images found in: {orig_dir}")
        else:
            raise SystemExit("no input path provided; specify an image path to convert")
    src = a.input
    name = safe_name(a.name or os.path.splitext(os.path.basename(src))[0])
    page_dir = os.path.join(a.root, name)
    os.makedirs(page_dir, exist_ok=True)
    P = page_paths(page_dir, name)
    rgb = load_rgb(src)
    if a.rotate_back:
        rgb = np.ascontiguousarray(np.rot90(rgb, k=-1 if a.rotate_back == "cw" else 1))
    corner = a.remove_logo
    if corner == "auto":
        corner = "br" if "gemini" in os.path.basename(src).lower() else "none"
    rgb = remove_logo(rgb, corner)
    mode = a.mode
    if mode == "auto":
        mode = "clean" if is_lineart(rgb) else "trace"
    line_px = a.line_px or default_line_px(a.long_side)
    log(f"convert {os.path.basename(src)} -> {name}  mode={mode} long={a.long_side} line={line_px}px")
    if mode == "trace":
        ink = trace_lineart(rgb, a.long_side, a.detail, line_px, not a.no_ai, seed_of(name))
    else:
        ink = clean_lineart(rgb, a.long_side, line_px, a.gap if a.gap is not None else max(1, line_px // 2),
                            not a.no_ai, a.keep_solids)
    h, w = ink.shape
    pocket = fingertip_area(h, w) * a.pocket
    ink = remove_small(ink, (line_px * 2) ** 2)
    if a.frame:
        m = max(2, line_px)
        ink[:m, :] = ink[-m:, :] = True
        ink[:, :m] = ink[:, -m:] = True
    gray = np.where(ink, 0, 255).astype(np.uint8)
    Image.fromarray(gray).save(P["master_png"], dpi=(DPI, DPI))
    Image.fromarray(gray).convert("RGB").save(P["white_jpg"], quality=95, dpi=(DPI, DPI))
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[..., 3] = ink.astype(np.uint8) * 255
    Image.fromarray(rgba, "RGBA").save(P["transparent_png"], dpi=(DPI, DPI))
    svg = vectorize(ink, P["svg"])
    os.makedirs(P["wm_dir"], exist_ok=True)
    save_preview(Image.fromarray(gray).convert("RGB"), os.path.join(P["wm_dir"], "0_blank_wm.jpg"), a.preview_long)
    rep = qc_report(ink, page_dir)
    meta = read_json(P["page_json"], {})
    meta.update({
        "name": name, "title": title_from_name(name), "source": os.path.abspath(src),
        "source_is_lineart": mode == "clean", "mode": mode, "detail": a.detail,
        "size": [w, h], "line_px": line_px, "svg": svg,
        "fill_regions": rep["fill_regions"], "qc": rep["status"],
        "converted": dt.datetime.now().isoformat(timespec="seconds"), "shop": SHOP,
    })
    write_json(P["page_json"], meta)
    with open(P["prompt_txt"], "w", encoding="utf-8") as pf:
        pf.write(CANONICAL_PROMPT + "\n")
    log(f"QC {rep['status']}: {rep['fill_regions']} fill regions, stroke {rep['stroke_width_px']}px",
        *(["| " + "; ".join(rep["warnings"])] if rep["warnings"] else []))
    log(f"done -> {page_dir}")
    return page_dir, name


# ----------------------------------------------------------------------------- COLORIZE
def hex2rgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def write_swatches(path: str, name: str, colors: list) -> None:
    sw = []
    for c in colors[:30]:
        r, g, b = [float(x) / 255 for x in c]
        hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
        sw.append({"hue": hh, "saturation": ss, "brightness": vv, "alpha": 1, "colorSpace": 0})
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Swatches.json", json.dumps([{"name": name, "swatches": sw}]))
    # hex sheet for non-Procreate apps
    cols = min(6, len(colors)) or 1
    rows = math.ceil(len(colors[:30]) / cols)
    S = 160
    im = Image.new("RGB", (cols * S, rows * (S + 40)), "white")
    d = ImageDraw.Draw(im)
    f = font(22, bold=False)
    for i, c in enumerate(colors[:30]):
        r, k = divmod(i, cols)
        x, y = k * S, r * (S + 40)
        d.rectangle([x + 8, y + 8, x + S - 8, y + S - 8], fill=tuple(int(v) for v in c))
        d.text((x + 12, y + S - 2), "#%02X%02X%02X" % tuple(int(v) for v in c), font=f, fill=(30, 30, 30))
    im.save(path.replace(".swatches", "_hex.png"))


def colorize_page(page_dir: str, name: str, original: str | None, palettes: list[str],
                  shade=0.35, preview_long=2048) -> list[tuple[str, str]]:
    P = page_paths(page_dir, name)
    ink = load_ink(page_dir, name)
    H, W = ink.shape
    white = (~ink).astype(np.uint8)
    n, lab = cv2.connectedComponents(white, connectivity=4)
    counts = np.bincount(lab.ravel(), minlength=n).astype(np.float64)
    counts[counts == 0] = 1
    rng = np.random.default_rng(seed_of(name))
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    border = border[border > 0]
    bg = int(border[np.argmax(counts[border])]) if len(border) else 0

    orig = None
    if original and os.path.exists(original):
        o = load_rgb(original)
        oh, ow = o.shape[:2]
        if abs(ow / oh - W / H) > 0.02:  # cover-fit, centered (composition alignment only)
            s = max(W / ow, H / oh)
            o = cv2.resize(o, (round(ow * s), round(oh * s)), interpolation=cv2.INTER_AREA)
            y0, x0 = (o.shape[0] - H) // 2, (o.shape[1] - W) // 2
            o = o[y0:y0 + H, x0:x0 + W]
            log("original aspect differs from line art; cover-fitted for color sampling")
        else:
            o = cv2.resize(o, (W, H), interpolation=cv2.INTER_AREA)
        orig = o

    flat = lab.ravel()
    lum = None
    if orig is not None:
        lum = cv2.GaussianBlur(cv2.cvtColor(orig, cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), max(W, H) / 500)
        reg_lum = np.bincount(flat, weights=lum.ravel(), minlength=n) / counts
        shade_map = 1 + shade * (lum - reg_lum[lab]) / 110
        key = np.argsort(np.argsort(reg_lum)) / max(1, n - 1)
    else:
        d = cv2.distanceTransform(white, cv2.DIST_L2, 5)
        mx = ndi.maximum(d, lab, index=np.arange(n)).astype(np.float32)
        mx[mx == 0] = 1
        shade_map = 0.84 + 0.16 * np.sqrt(np.clip(d / mx[lab], 0, 1))
        ys = np.bincount(flat, weights=np.repeat(np.arange(H, dtype=np.float64), W), minlength=n) / counts
        raw = 0.55 * ys / H + 0.45 * rng.random(n)
        key = np.argsort(np.argsort(raw)) / max(1, n - 1)
    shade_map = np.clip(shade_map, 0.62, 1.22).astype(np.float32)

    def render(table: np.ndarray) -> Image.Image:
        out = np.empty((H, W, 3), np.uint8)
        for c in range(3):
            ch = table[:, c][lab] * shade_map
            ch[ink] = 0
            out[..., c] = np.clip(ch, 0, 255)
        return Image.fromarray(out)

    jobs = []
    if orig is not None:
        table = np.stack([np.bincount(flat, weights=orig[..., c].ravel().astype(np.float64), minlength=n) / counts
                          for c in range(3)], 1).astype(np.float32)
        jobs.append(("1_realistic", table, None))
    else:
        log("no original image -> realistic colorway skipped (5 creative instead)")
        if len(palettes) < 5:
            palettes = palettes + [p for p in ["ocean", "sunset", "candy"] if p not in palettes][:5 - len(palettes)]
    start = 2 if orig is not None else 1
    for i, pname in enumerate(palettes[: (4 if orig is not None else 5)]):
        pal = PALETTES[pname]
        cols = np.stack([hex2rgb(h) for h in pal["c"]])
        m = len(cols)
        idx = np.clip(np.round(key * (m - 1) + rng.normal(0, 0.75, n)), 0, m - 1).astype(int)
        table = cols[idx].copy()
        if "accent" in pal:
            acc = rng.random(n) < 0.12
            table[acc] = hex2rgb(pal["accent"])
        if bg:
            table[bg] = cols[pal["bg"]]
        jobs.append((f"{start + i}_creative_{pname}", table, pname))

    os.makedirs(P["wm_dir"], exist_ok=True)
    os.makedirs(P["pal_dir"], exist_ok=True)
    made = []
    for tag, table, pname in jobs:
        img = render(table)
        full = os.path.join(page_dir, f"{name}_{tag}.jpg")
        img.save(full, quality=93, dpi=(DPI, DPI))
        save_preview(img, os.path.join(P["wm_dir"], f"{tag}_wm.jpg"), preview_long)
        if pname:
            used = [hex2rgb(h) for h in PALETTES[pname]["c"]] + ([hex2rgb(PALETTES[pname]["accent"])] if "accent" in PALETTES[pname] else [])
        else:  # realistic: most-used region colors, quantized
            q = (table[1:] // 24 * 24 + 12).astype(int)
            uniq, cnt = np.unique(q, axis=0, return_counts=True)
            used = [uniq[j] for j in np.argsort(-cnt)[:24]]
        write_swatches(os.path.join(P["pal_dir"], f"{name}_{tag}.swatches"), f"{title_from_name(name)} - {tag}", used)
        made.append((tag, full))
        log(f"colorway {tag} -> {os.path.basename(full)}")
    meta = read_json(P["page_json"], {})
    meta.update({"colorways": [t for t, _ in made], "original_for_realistic": original if orig is not None else None,
                 "colorized": dt.datetime.now().isoformat(timespec="seconds")})
    write_json(P["page_json"], meta)
    with open(P["prompt_txt"], "w", encoding="utf-8") as pf:
        pf.write(CANONICAL_PROMPT + "\n")
    return made


def cmd_colorize(a):
    page_dir, name = resolve_page(a.page)
    meta = read_json(os.path.join(page_dir, "page.json"), {})
    original = a.original
    if not original and meta.get("source") and not meta.get("source_is_lineart"):
        original = meta["source"]
    pals = [p.strip() for p in a.palettes.split(",")] if a.palettes else list(DEFAULT_CREATIVE)
    bad = [p for p in pals if p not in PALETTES]
    if bad:
        raise SystemExit(f"unknown palettes {bad}; choose from {list(PALETTES)}")
    colorize_page(page_dir, name, original, pals, a.shade, a.preview_long)


# ----------------------------------------------------------------------------- PACKAGE
def place(im: Image.Image, size, transparent=False, margin=0.04) -> Image.Image:
    W, H = size
    canvas = Image.new("RGBA" if transparent else "RGB", size, (0, 0, 0, 0) if transparent else "white")
    t = fit(im, W * (1 - 2 * margin), H * (1 - 2 * margin))
    canvas.paste(t, ((W - t.width) // 2, (H - t.height) // 2), t if transparent else None)
    return canvas


def colorway_files(page_dir: str, name: str) -> list[str]:
    fs = [f for f in os.listdir(page_dir) if re.match(rf"{re.escape(name)}_\d_(realistic|creative_.+)\.jpg$", f)]
    return [os.path.join(page_dir, f) for f in sorted(fs)]


def resolve_original_file(page_dir: str, name: str) -> str | None:
    """Find or stage the original reference image for customer delivery archive."""
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"):
        cand = os.path.join(page_dir, f"{name}_original{ext}")
        if os.path.exists(cand):
            return cand
    for f in os.listdir(page_dir):
        if "original" in f.lower() and os.path.splitext(f)[1].lower() in IMG_EXT:
            return os.path.join(page_dir, f)
    pj = os.path.join(page_dir, "page.json")
    if os.path.exists(pj):
        m = read_json(pj, {})
        for k in ("original_for_realistic", "original", "source"):
            ref = m.get(k)
            if ref and os.path.exists(ref) and not (k == "source" and m.get("source_is_lineart")):
                ext = os.path.splitext(ref)[1].lower()
                dest = os.path.join(page_dir, f"{name}_original{ext}")
                try:
                    if not os.path.exists(dest):
                        shutil.copy2(ref, dest)
                    return dest
                except Exception:
                    return ref
    return None


def cmd_package(a=None, page_dir=None, name=None, root=None):
    if a is not None:
        page_dir, name = resolve_page(a.page)
        root = a.root
    P = page_paths(page_dir, name)
    blank = Image.open(P["white_jpg"]).convert("RGB")
    trans = Image.open(P["transparent_png"]).convert("RGBA")
    portrait = blank.height >= blank.width
    ipad = (2048, 2732) if portrait else (2732, 2048)
    place(blank, ipad).save(P["ipad_white"], quality=95, dpi=(264, 264))
    place(trans, ipad, transparent=True).save(P["ipad_transparent"], dpi=(264, 264))
    for key, (pw, ph) in (("pdf_letter", (2550, 3300)), ("pdf_a4", (2480, 3508))):
        size = (pw, ph) if portrait else (ph, pw)
        place(blank, size, margin=0.03).save(P[key], "PDF", resolution=DPI)
    cws = colorway_files(page_dir, name)
    cimgs = [Image.open(f).convert("RGB") for f in cws]
    compose_pin(blank, cimgs).save(P["pin"], quality=92)
    if cimgs:
        compose_cover(blank, cimgs).save(P["cover"], quality=92)
        compose_split_thumb(blank, cimgs[0]).save(P["thumb"], quality=92)
    # buyer zip (NO watermarks, INCLUDES original reference image)
    zdir = os.path.join(root or os.path.dirname(page_dir), "_zips")
    os.makedirs(zdir, exist_ok=True)
    zpath = os.path.join(zdir, f"{name}.zip")
    orig_file = resolve_original_file(page_dir, name)
    orig_list = [orig_file] if (orig_file and os.path.exists(orig_file)) else []
    files = [P["white_jpg"], P["transparent_png"], P["ipad_white"], P["ipad_transparent"],
             P["pdf_letter"], P["pdf_a4"]] + ([P["svg"]] if os.path.exists(P["svg"]) else []) + orig_list + cws
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, os.path.basename(f))
        if os.path.isdir(P["pal_dir"]):
            for f in os.listdir(P["pal_dir"]):
                z.write(os.path.join(P["pal_dir"], f), "palettes/" + f)
        z.writestr("README.txt", (
            f"{title_from_name(name)} - {SHOP} digital coloring page\n\n"
            "Blank pages: full resolution (white JPG + transparent PNG for layer apps), iPad size, "
            "and print-ready PDFs (US Letter + A4).\n"
            "Original reference artwork: included for color matching and side-by-side painting.\n"
            "Colored versions: 5 inspiration variants + matching Procreate .swatches and hex-code sheets.\n"
            "palettes/: Procreate .swatches files (tap to import) + hex-code sheets for other apps.\n"
            "Works in Procreate, ibisPaint, Krita, Photoshop and any coloring app.\n"
            "Personal use only. Please do not resell or redistribute.\n"))
    meta = read_json(P["page_json"], {})
    meta.update({"zip": zpath, "packaged": dt.datetime.now().isoformat(timespec="seconds")})
    write_json(P["page_json"], meta)
    with open(P["prompt_txt"], "w", encoding="utf-8") as pf:
        pf.write(CANONICAL_PROMPT + "\n")
    log(f"packaged: iPad {ipad}, Letter/A4 PDF, pin, cover, thumb, zip -> {zpath}")


# ----------------------------------------------------------------------------- PIPELINE
def iter_inputs(path: str) -> list[str]:
    if os.path.isdir(path):
        return sorted(os.path.join(path, f) for f in os.listdir(path)
                      if os.path.splitext(f)[1].lower() in IMG_EXT)
    return [path]


def find_original(stem: str, originals_dir: str | None):
    if not originals_dir:
        return None
    for f in os.listdir(originals_dir):
        if os.path.splitext(f)[0].lower() == stem.lower() and os.path.splitext(f)[1].lower() in IMG_EXT:
            return os.path.join(originals_dir, f)
    return None


def cmd_pipeline(a):
    if not a.input:
        orig_dir = a.originals_dir or DEFAULT_ORIGINALS_DIR
        if os.path.isdir(orig_dir):
            cands = [os.path.join(orig_dir, f) for f in os.listdir(orig_dir)
                     if os.path.splitext(f)[1].lower() in IMG_EXT]
            if cands:
                cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                a.input = cands[0]
                log(f"no input path provided, auto-selected newest original: {a.input}")
            else:
                raise SystemExit(f"no input path provided and no images found in: {orig_dir}")
        else:
            raise SystemExit("no input path provided; specify an image path to translate")
    inputs = iter_inputs(a.input)
    if not inputs:
        raise SystemExit("no images found")
    pals = [p.strip() for p in a.palettes.split(",")] if a.palettes else list(DEFAULT_CREATIVE)
    results = []
    for src in inputs:
        stem = os.path.splitext(os.path.basename(src))[0]
        name = safe_name(a.name if (a.name and len(inputs) == 1) else stem)
        if os.path.exists(os.path.join(a.root, name, f"{name}_full_white.png")) and not a.force:
            log(f"skip {name} (exists; use --force)")
            continue
        a.input, a.name = src, name
        page_dir, name = cmd_convert(a)
        meta = read_json(os.path.join(page_dir, "page.json"), {})
        original = a.original if len(inputs) == 1 and a.original else find_original(stem, a.originals_dir or DEFAULT_ORIGINALS_DIR)
        if not original and not meta.get("source_is_lineart"):
            original = src
        colorize_page(page_dir, name, original, pals, a.shade, a.preview_long)
        cmd_package(page_dir=page_dir, name=name, root=a.root)
        results.append({"name": name, "dir": page_dir, "qc": meta.get("qc")})
    write_json(os.path.join(a.root, "_last_run.json"), results)
    log(f"pipeline finished: {len(results)} page(s)")
    for r in results:
        log(f"  {r['name']}: QC {r['qc']} -> {r['dir']}")


# ----------------------------------------------------------------------------- SHOP
CATALOG = "catalog.json"


def catalog_load(root):
    return read_json(os.path.join(root, CATALOG), {"shop": SHOP, "pages": {}})


def catalog_save(root, cat):
    write_json(os.path.join(root, CATALOG), cat)
    lines = [f"# {SHOP} catalog", "", f"Updated {dt.datetime.now():%Y-%m-%d %H:%M}", "",
             "| # | Title | Price | Gumroad | Pinterest | Link |", "|---|---|---|---|---|---|"]
    for i, (k, p) in enumerate(sorted(cat["pages"].items()), 1):
        lines.append(f"| {i:02d} | {p.get('title', k)} | {p.get('price_display', '')} | {p.get('status', 'ready')} | "
                     f"{'PINNED' if p.get('pinned') else '-'} | {p.get('gumroad_url', '')} |")
    with open(os.path.join(root, "catalog.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def build_listing(page_dir, name, title=None, story=None, price=1.0, lead_magnet=False):
    meta = read_json(os.path.join(page_dir, "page.json"), {})
    t = title or meta.get("title") or title_from_name(name)
    regions = meta.get("fill_regions") or 0
    rnd = int(regions // 100 * 100) if regions >= 200 else regions
    ncol = len(meta.get("colorways", []))
    full = f"{t} Digital Coloring Page for Procreate & ibisPaint | {rnd}+ Fill Areas | Adult Coloring | Transparent PNG + Printable PDF"
    desc = [
        (story.strip() + "\n") if story else "",
        f"A one-of-a-kind, highly detailed coloring page with {rnd}+ closed, fill-ready areas - "
        "clean single lines, no shading, so bucket fill and Procreate drag-to-fill never leak.",
        "",
        "WHAT YOU GET",
        "- Full-resolution blank page (300 DPI): white JPG + transparent PNG for layer-based apps",
        "- iPad size (2048x2732 / 2732x2048) white JPG + transparent PNG",
        "- Print-ready PDFs: US Letter + A4",
        "- Original reference artwork image for side-by-side color matching and inspiration",
        f"- {ncol} colored versions for inspiration + matching Procreate .swatches palettes and hex sheets",
        "",
        "Works in Procreate, ibisPaint, Krita, Photoshop and any coloring app on iPad, Android, Windows and Mac.",
        "Instant download for personal use. The preview images show a few ways to color it.",
    ]
    tags = ["procreate coloring page", "digital coloring page", "ipad coloring", "adult coloring pages",
            "intricate coloring", "transparent png line art", "ibispaint coloring", "printable coloring page",
            "fill ready coloring", "instant download", "unique coloring page",
            t.lower() + " coloring", "detailed coloring page"]
    price = 0.0 if lead_magnet else price
    listing = {
        "name": name, "title": full, "short_title": t, "description": "\n".join(desc).strip(),
        "tags": tags[:13], "price": price, "price_display": "$0+" if price == 0 else f"${price:.2f}",
        "pay_what_you_want": price == 0, "collect_emails": True,
        "main_image": os.path.join(page_dir, "watermarked", "0_blank_wm.jpg"),
        "preview_images_in_order": sorted(
            os.path.join(page_dir, "watermarked", f) for f in os.listdir(os.path.join(page_dir, "watermarked"))),
        "cover": os.path.join(page_dir, f"{name}_cover_1280x720.jpg"),
        "thumbnail": os.path.join(page_dir, f"{name}_thumb_square.jpg"),
        "pin": os.path.join(page_dir, f"{name}_pin_1000x1500.jpg"),
        "download_zip": meta.get("zip"),
        "notes": ["Etsy requires the AI-generated checkbox; Gumroad listings carry no AI line (Miranda's rule).",
                  "Only Miranda's own images; no real-person likenesses or IP characters."],
    }
    write_json(os.path.join(page_dir, "listing.json"), listing)
    return listing


def cmd_listing(a):
    page_dir, name = resolve_page(a.page)
    L = build_listing(page_dir, name, a.title, a.story, a.price, a.lead_magnet)
    root = a.root or os.path.dirname(page_dir)
    cat = catalog_load(root)
    p = cat["pages"].setdefault(name, {})
    p.update({"title": L["short_title"], "price": L["price"], "price_display": L["price_display"],
              "dir": page_dir, "status": p.get("status", "ready")})
    catalog_save(root, cat)
    log(f"listing.json written for {name} ({L['price_display']})")
    print(json.dumps({k: L[k] for k in ("title", "price_display", "tags")}, indent=2))


def cmd_catalog(a):
    cat = catalog_load(a.root)
    for d in sorted(os.listdir(a.root)):
        pj = os.path.join(a.root, d, "page.json")
        if os.path.exists(pj):
            m = read_json(pj, {})
            p = cat["pages"].setdefault(m.get("name", d), {"status": "ready"})
            p.setdefault("title", m.get("title", d))
            p["dir"] = os.path.join(a.root, d)
            p["complete"] = bool(m.get("zip")) and os.path.exists(os.path.join(a.root, d, "listing.json"))
    catalog_save(a.root, cat)
    log(f"catalog: {len(cat['pages'])} pages -> {os.path.join(a.root, 'catalog.md')}")


def cmd_mark(a):
    cat = catalog_load(a.root)
    p = cat["pages"].setdefault(a.name, {})
    if a.status:
        p["status"] = a.status
        if a.status == "live":
            p["published_on"] = dt.date.today().isoformat()
    if a.gumroad_url:
        p["gumroad_url"] = a.gumroad_url
    if a.pinned:
        p["pinned"] = True
        p["pinned_on"] = dt.date.today().isoformat()
    catalog_save(a.root, cat)
    log(f"{a.name}: {p}")


def cmd_queue(a):
    """Respect Gumroad's 10-new-products-per-day cap: plan what to publish today vs later."""
    cat = catalog_load(a.root)
    today = dt.date.today()
    used = sum(1 for p in cat["pages"].values() if p.get("published_on") == today.isoformat())
    pending = [k for k, p in sorted(cat["pages"].items()) if p.get("status") in ("ready", "draft", "queued")]
    plan, day, slots = {}, today, a.cap - used
    for k in pending:
        while slots <= 0:
            day += dt.timedelta(days=1)
            slots = a.cap
        plan.setdefault(day.isoformat(), []).append(k)
        slots -= 1
    write_json(os.path.join(a.root, "publish_queue.json"),
               {"cap_per_day": a.cap, "published_today": used, "plan": plan, "next_window": "~9:15 AM ET"})
    log(f"published today: {used}/{a.cap}")
    for d, ks in plan.items():
        log(f"  {d}: {', '.join(ks)}")


def cmd_gumroad_checklist(a):
    page_dir, name = resolve_page(a.page)
    L = read_json(os.path.join(page_dir, "listing.json")) or build_listing(page_dir, name)
    md = [f"# Gumroad listing checklist - {L['short_title']}", "",
          "Create as an **unpublished draft**. Publish only after Miranda says \"publish\".", "",
          "1. New product -> Digital product", f"2. **Name:** {L['title']}",
          f"3. **Price:** {L['price_display']}" + (" (pay-what-you-want, min $0)" if L["pay_what_you_want"] else ""),
          "4. **Description:**", "", "```", L["description"], "```", "",
          "5. **Cover images, in this order** (all watermarked):"]
    md += [f"   - `{p}`" for p in L["preview_images_in_order"]]
    md += [f"6. **Thumbnail (square):** `{L['thumbnail']}`", f"7. **Content / download:** `{L['download_zip']}`",
           f"8. **Tags:** {', '.join(L['tags'])}", "9. Save as draft. Post the URL back so Pinterest can link it:",
           f"   `python cbengine.py mark {name} --status draft --gumroad-url <URL>`", "",
           "> Limit: Gumroad allows 10 new products/day. Run `queue` to see what fits today."]
    out = os.path.join(page_dir, "gumroad_checklist.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    log(f"checklist -> {out}")


def http_json(url, token, method="GET", body=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")


def cmd_gumroad_sync(a):
    tok = os.environ.get("GUMROAD_ACCESS_TOKEN")
    if not tok:
        raise SystemExit("set GUMROAD_ACCESS_TOKEN (Gumroad -> Settings -> Advanced -> Applications)")
    data = http_json("https://api.gumroad.com/v2/products", tok)
    cat = catalog_load(a.root)
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())  # noqa
    n = 0
    for prod in data.get("products", []):
        for k, p in cat["pages"].items():
            if norm(p.get("title", k)) and norm(p.get("title", k)) in norm(prod.get("name", "")):
                p["gumroad_url"] = prod.get("short_url")
                p["status"] = "live" if prod.get("published") else "draft"
                n += 1
    catalog_save(a.root, cat)
    log(f"gumroad-sync matched {n} products")


def cmd_pinterest_post(a):
    page_dir, name = resolve_page(a.page)
    L = read_json(os.path.join(page_dir, "listing.json")) or build_listing(page_dir, name)
    link = a.link or (catalog_load(a.root or os.path.dirname(page_dir))["pages"].get(name, {}).get("gumroad_url"))
    if not link:
        raise SystemExit("no Gumroad link yet - Pinterest pins only after the listing is live (use --link)")
    title = L["short_title"] + " - Digital Coloring Page"
    desc = (f"{L['short_title']}: a detailed, fill-ready digital coloring page for Procreate & ibisPaint. "
            f"Blank page + colored versions. Instant download from {SHOP}.")[:500]
    imgs = [L["pin"]] if not a.carousel else L["preview_images_in_order"][:5]

    def b64(p):
        with open(p, "rb") as f:
            return base64.b64encode(f.read()).decode()
    if a.carousel:
        media = {"source_type": "multiple_image_base64",
                 "items": [{"content_type": "image/jpeg", "data": b64(p), "title": title[:100],
                            "description": desc, "link": link} for p in imgs]}
    else:
        media = {"source_type": "image_base64", "content_type": "image/jpeg", "data": b64(imgs[0])}
    if not a.live:
        log("DRY RUN (add --live to post). Would create pin:")
        print(json.dumps({"board": a.board_id or a.board_name, "title": title, "link": link,
                          "images": imgs, "alt_text": desc[:500]}, indent=2))
        return
    tok = os.environ.get("PINTEREST_ACCESS_TOKEN")
    if not tok:
        raise SystemExit("set PINTEREST_ACCESS_TOKEN (Pinterest developer app, scopes boards:read pins:write)")
    board = a.board_id
    if not board:
        boards = http_json("https://api.pinterest.com/v5/boards?page_size=100", tok).get("items", [])
        board = next((b["id"] for b in boards if b["name"].lower() == a.board_name.lower()), None)
        if not board:
            raise SystemExit(f"board '{a.board_name}' not found")
    res = http_json("https://api.pinterest.com/v5/pins", tok, "POST",
                    {"board_id": board, "title": title[:100], "description": desc, "link": link,
                     "alt_text": desc[:500], "media_source": media})
    root = a.root or os.path.dirname(page_dir)
    cat = catalog_load(root)
    p = cat["pages"].setdefault(name, {})
    p.update({"pinned": True, "pinned_on": dt.date.today().isoformat(),
              "pins": p.get("pins", []) + [res.get("id")]})
    catalog_save(root, cat)
    log(f"pinned {name}: pin id {res.get('id')}")


# ----------------------------------------------------------------------------- CLI
def add_convert_args(p):
    p.add_argument("--name", help="page name (folder + file prefix); default = file name")
    p.add_argument("--root", default=DEFAULT_ROOT, help=f"output root (default {DEFAULT_ROOT})")
    p.add_argument("--mode", choices=["auto", "trace", "clean"], default="auto",
                   help="trace = color photo/AI art -> region outlines; clean = existing line art -> solid leak-proof lines")
    p.add_argument("--detail", choices=list(DETAIL), default="medium")
    p.add_argument("--long-side", type=int, default=4096)
    p.add_argument("--line-px", type=int, default=0, help="outline stroke width at output (default long/650)")
    p.add_argument("--gap", type=int, default=None, help="clean mode gap-closing radius px")
    p.add_argument("--pocket", type=float, default=0.25, help="fill white pockets smaller than this x fingertip")
    p.add_argument("--remove-logo", default="auto", choices=["auto", "none", "br", "bl", "tr", "tl"])
    p.add_argument("--rotate-back", choices=["cw", "ccw"], help="undo the rotate-90 landscape trick")
    p.add_argument("--keep-solids", action="store_true")
    p.add_argument("--frame", action="store_true", help="draw a closed border around the page")
    p.add_argument("--no-ai", action="store_true", help="never use Real-ESRGAN even if installed")
    p.add_argument("--preview-long", type=int, default=2048, help="watermarked preview long side (0 = full res)")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cbengine", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("convert", help="image -> blank coloring page (+ watermarked preview)")
    p.add_argument("input", nargs="?", default=None, help="input image, folder, or omit to auto-select newest from originals folder")
    add_convert_args(p)
    p.set_defaults(fn=cmd_convert)

    p = sp.add_parser("colorize", help="blank page -> realistic + creative colorways (clean + watermarked)")
    p.add_argument("page", help="page folder or *_full_white.png")
    p.add_argument("--original", help="original color image for the realistic colorway")
    p.add_argument("--palettes", help=f"comma list from {','.join(PALETTES)} (default {','.join(DEFAULT_CREATIVE)})")
    p.add_argument("--shade", type=float, default=0.35)
    p.add_argument("--preview-long", type=int, default=2048)
    p.set_defaults(fn=cmd_colorize)

    p = sp.add_parser("package", help="iPad files, PDFs, pin, cover, thumbnail, buyer zip")
    p.add_argument("page")
    p.add_argument("--root", default=None)
    p.set_defaults(fn=cmd_package)

    p = sp.add_parser("pipeline", help="convert + colorize + package (file or folder)")
    p.add_argument("input", nargs="?", default=None, help="input image, folder, or omit to auto-select newest from originals folder")
    add_convert_args(p)
    p.add_argument("--original")
    p.add_argument("--originals-dir", help="folder with originals matched by file stem (batch)")
    p.add_argument("--palettes")
    p.add_argument("--shade", type=float, default=0.35)
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_pipeline)

    p = sp.add_parser("prompt", help="print canonical translation prompt")
    p.set_defaults(fn=lambda a: print(CANONICAL_PROMPT))

    p = sp.add_parser("qc", help="re-run quality check on a page")
    p.add_argument("page")
    p.set_defaults(fn=lambda a: print(json.dumps(qc_report(load_ink(*resolve_page(a.page)), resolve_page(a.page)[0]), indent=2)))

    p = sp.add_parser("watermark", help="watermark any image")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--text")
    p.set_defaults(fn=lambda a: watermark(Image.open(a.input).convert("RGB"), a.text).save(a.output, quality=92))

    p = sp.add_parser("listing", help="write listing.json (title/description/tags/price)")
    p.add_argument("page")
    p.add_argument("--title")
    p.add_argument("--story", help="one-line story hook shown first in the description")
    p.add_argument("--price", type=float, default=1.0)
    p.add_argument("--lead-magnet", action="store_true", help="$0+ pay-what-you-want")
    p.add_argument("--root")
    p.set_defaults(fn=cmd_listing)

    p = sp.add_parser("catalog", help="rebuild catalog.json / catalog.md")
    p.add_argument("--root", default=DEFAULT_ROOT)
    p.set_defaults(fn=cmd_catalog)

    p = sp.add_parser("mark", help="record status / Gumroad URL / pinned")
    p.add_argument("name")
    p.add_argument("--root", default=DEFAULT_ROOT)
    p.add_argument("--status", choices=["ready", "draft", "queued", "live"])
    p.add_argument("--gumroad-url")
    p.add_argument("--pinned", action="store_true")
    p.set_defaults(fn=cmd_mark)

    p = sp.add_parser("queue", help="plan publishing under Gumroad's daily cap")
    p.add_argument("--root", default=DEFAULT_ROOT)
    p.add_argument("--cap", type=int, default=10)
    p.set_defaults(fn=cmd_queue)

    p = sp.add_parser("gumroad-checklist", help="exact field-by-field Gumroad draft checklist")
    p.add_argument("page")
    p.set_defaults(fn=cmd_gumroad_checklist)

    p = sp.add_parser("gumroad-sync", help="pull product URLs/status via GUMROAD_ACCESS_TOKEN")
    p.add_argument("--root", default=DEFAULT_ROOT)
    p.set_defaults(fn=cmd_gumroad_sync)

    p = sp.add_parser("pinterest-post", help="pin a page (dry run unless --live; needs PINTEREST_ACCESS_TOKEN)")
    p.add_argument("page")
    p.add_argument("--link")
    p.add_argument("--board-name", default="Digital Coloring Pages")
    p.add_argument("--board-id")
    p.add_argument("--carousel", action="store_true", help="carousel of blank + colorways instead of the tall pin")
    p.add_argument("--live", action="store_true")
    p.add_argument("--root")
    p.set_defaults(fn=cmd_pinterest_post)

    a = ap.parse_args(argv)
    if getattr(a, "root", None):
        os.makedirs(a.root, exist_ok=True)
    a.fn(a)


if __name__ == "__main__":
    main()
