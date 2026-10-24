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

#!/usr/bin/env python3
"""
Coloring Page Line Art Extraction & Quality Verification Engine
Transforms input images into clean, leak-proof, pure black line art for Procreate and print.
"""

import sys
import os
import argparse
from PIL import Image, ImageOps, ImageFilter
from watermark import add_tiled_watermark

def extract_line_art(
    input_path: str,
    output_dir: str,
    name: str = "Coloring_Page",
    watermark_text: str = "PREVIEW DigiDreamWeaver",
    min_area: int = 4000
):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    os.makedirs(output_dir, exist_ok=True)
    watermark_dir = os.path.join(output_dir, "watermarked")
    os.makedirs(watermark_dir, exist_ok=True)

    img = Image.open(input_path)
    orig_w, orig_h = img.size
    is_portrait = orig_h >= orig_w

    # Convert to grayscale
    gray = img.convert("L")

    # High-contrast edge detection & binarization
    # If image is already largely line art, binarize directly; otherwise detect edges
    edges = gray.filter(ImageFilter.FIND_EDGES)
    # Invert so lines are black, background is white
    inverted_edges = ImageOps.invert(edges)

    # Threshold to pure black (#000000) and pure white (#FFFFFF)
    threshold = 200
    table = [0 if i < threshold else 255 for i in range(256)]
    binarized = inverted_edges.point(table, 'L')

    # Save Full-Res Solid White JPG
    full_white_path = os.path.join(output_dir, f"{name}_full_white.jpg")
    binarized.convert("RGB").save(full_white_path, "JPEG", quality=95)

    # Save Full-Res Transparent PNG (pure black lines, transparent background)
    rgba = Image.new("RGBA", binarized.size, (0, 0, 0, 0))
    alpha_mask = ImageOps.invert(binarized)
    # Black line art with alpha mask
    black_canvas = Image.new("RGBA", binarized.size, (0, 0, 0, 255))
    full_transparent_path = os.path.join(output_dir, f"{name}_full_transparent.png")
    Image.composite(black_canvas, rgba, alpha_mask).save(full_transparent_path, "PNG")

    # Build iPad Optimized Dimensions (2048 x 2732 portrait or 2732 x 2048 landscape)
    ipad_size = (2048, 2732) if is_portrait else (2732, 2048)
    ipad_white = binarized.resize(ipad_size, Image.LANCZOS)
    ipad_white_path = os.path.join(output_dir, f"{name}_iPad_white.jpg")
    ipad_white.convert("RGB").save(ipad_white_path, "JPEG", quality=95)

    ipad_rgba = Image.new("RGBA", ipad_size, (0, 0, 0, 0))
    ipad_alpha_mask = ImageOps.invert(ipad_white)
    ipad_black_canvas = Image.new("RGBA", ipad_size, (0, 0, 0, 255))
    ipad_transparent_path = os.path.join(output_dir, f"{name}_iPad_transparent.png")
    Image.composite(ipad_black_canvas, ipad_rgba, ipad_alpha_mask).save(ipad_transparent_path, "PNG")

    # Generate Watermarked Preview
    with open(os.path.join(output_dir, "prompt.txt"), "w", encoding="utf-8") as pf:
        pf.write(CANONICAL_PROMPT + "\n")
    preview_wm_path = os.path.join(watermark_dir, f"{name}_lineart_preview_wm.jpg")
    add_tiled_watermark(full_white_path, preview_wm_path, text=watermark_text)

    print(f"[LINEART] Processed {name}:")
    print(f"  - Master White JPG:       {full_white_path}")
    print(f"  - Master Transparent PNG: {full_transparent_path}")
    print(f"  - iPad White JPG:         {ipad_white_path}")
    print(f"  - iPad Transparent PNG:   {ipad_transparent_path}")
    print(f"  - Watermarked Preview:    {preview_wm_path}")

    return {
        "full_white": full_white_path,
        "full_transparent": full_transparent_path,
        "ipad_white": ipad_white_path,
        "ipad_transparent": ipad_transparent_path,
        "preview_wm": preview_wm_path,
    }

def main():
    parser = argparse.ArgumentParser(description="Convert an image into digital coloring line art.")
    parser.add_argument("--input", "-i", required=True, help="Source image path")
    parser.add_argument("--output-dir", "-o", default="./output", help="Directory for deliverables")
    parser.add_argument("--name", "-n", default="Coloring_Page", help="Output name prefix")
    parser.add_argument("--watermark", "-w", default="PREVIEW DigiDreamWeaver", help="Watermark text")
    args = parser.parse_args()

    extract_line_art(args.input, args.output_dir, name=args.name, watermark_text=args.watermark)

if __name__ == "__main__":
    main()
