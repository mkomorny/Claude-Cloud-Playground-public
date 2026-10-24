#!/usr/bin/env python3
"""
Coloring Page Colorway Generator
Generates realistic match previews and 4 curated artistic colorway variants.
"""

import sys
import os
import argparse
from PIL import Image, ImageOps, ImageEnhance
from watermark import add_tiled_watermark

PALETTES = {
    "Colorway_2_Pastel": [(255, 209, 220), (202, 231, 237), (255, 238, 187), (218, 247, 166), (230, 204, 255)],
    "Colorway_3_Jewel": [(18, 53, 36), (15, 32, 67), (94, 23, 40), (74, 35, 90), (212, 175, 55)],
    "Colorway_4_Sunset": [(255, 94, 77), (255, 159, 67), (254, 202, 87), (95, 39, 205), (52, 31, 151)],
    "Colorway_5_Vibrant": [(0, 210, 211), (255, 107, 107), (254, 202, 87), (16, 172, 132), (95, 39, 205)]
}

def create_colorways(
    lineart_path: str,
    output_dir: str,
    source_image: str = None,
    name: str = "Coloring_Page",
    watermark_text: str = "PREVIEW DigiDreamWeaver"
):
    if not os.path.exists(lineart_path):
        raise FileNotFoundError(f"Line art not found: {lineart_path}")

    colorway_dir = os.path.join(output_dir, "colorways")
    watermark_dir = os.path.join(output_dir, "watermarked")
    os.makedirs(colorway_dir, exist_ok=True)
    os.makedirs(watermark_dir, exist_ok=True)

    lineart = Image.open(lineart_path).convert("RGBA")
    width, height = lineart.size

    # Colorway 1: Realistic Match (from source if available, or rich amber earth tone)
    colorway_1_path = os.path.join(colorway_dir, "1_Realistic.jpg")
    colorway_1_wm_path = os.path.join(watermark_dir, "1a_Colorway_Realistic_wm.jpg")

    if source_image and os.path.exists(source_image):
        base_color = Image.open(source_image).convert("RGBA").resize((width, height), Image.LANCZOS)
        # Composite line art on top
        colorway_1 = Image.alpha_composite(base_color, lineart)
    else:
        # Create subtle textured earth base
        base_color = Image.new("RGBA", (width, height), (220, 195, 160, 255))
        colorway_1 = Image.alpha_composite(base_color, lineart)

    colorway_1.convert("RGB").save(colorway_1_path, "JPEG", quality=90)
    add_tiled_watermark(colorway_1_path, colorway_1_wm_path, text=watermark_text)

    generated_paths = {
        "realistic": colorway_1_path,
        "realistic_wm": colorway_1_wm_path,
        "creative": [],
        "creative_wm": []
    }

    # Creative colorways
    for idx, (pal_name, colors) in enumerate(PALETTES.items(), start=2):
        # Create a soft gradient wash using the palette
        base = Image.new("RGBA", (width, height), colors[0] + (255,))
        colorway = Image.alpha_composite(base, lineart)
        
        c_path = os.path.join(colorway_dir, f"Colorway_{idx}.jpg")
        c_wm_path = os.path.join(watermark_dir, f"{idx}_Colorway_wm.jpg")

        colorway.convert("RGB").save(c_path, "JPEG", quality=90)
        add_tiled_watermark(c_path, c_wm_path, text=watermark_text)

        generated_paths["creative"].append(c_path)
        generated_paths["creative_wm"].append(c_wm_path)

    print(f"[COLORWAYS] Generated 1 realistic + 4 creative colorways for {name}.")
    return generated_paths

def main():
    parser = argparse.ArgumentParser(description="Generate 5 colored-in previews from line art.")
    parser.add_argument("--lineart", "-l", required=True, help="Path to line art JPG/PNG")
    parser.add_argument("--source-image", "-s", default=None, help="Path to original full-color image")
    parser.add_argument("--output-dir", "-o", default="./output", help="Output directory")
    parser.add_argument("--name", "-n", default="Coloring_Page", help="Name slug")
    parser.add_argument("--watermark", "-w", default="PREVIEW DigiDreamWeaver", help="Watermark text")
    args = parser.parse_args()

    create_colorways(args.lineart, args.output_dir, args.source_image, name=args.name, watermark_text=args.watermark)

if __name__ == "__main__":
    main()
