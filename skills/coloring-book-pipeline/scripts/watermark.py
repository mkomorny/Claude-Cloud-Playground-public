#!/usr/bin/env python3
"""
Light Diagonal Tiled Watermark Generator
Applies a semi-transparent diagonal tiled watermark across preview images
(e.g., "PREVIEW DigiDreamWeaver") to prevent unauthorized scraping while
allowing customers to clearly evaluate the art.
"""

import sys
import os
import argparse
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

def add_tiled_watermark(
    input_path: str,
    output_path: str,
    text: str = "PREVIEW DigiDreamWeaver",
    angle: int = -35,
    opacity: float = 0.28,
    font_size: int = None
):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    base_image = Image.open(input_path).convert("RGBA")
    width, height = base_image.size

    # Dynamic font sizing based on image dimensions
    if font_size is None:
        font_size = max(24, int(min(width, height) / 16))

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    # Create a separate overlay for the watermarks
    overlay = Image.new("RGBA", (width * 2, height * 2), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Calculate step distances
    step_x = int(font_size * 7.5)
    step_y = int(font_size * 4.0)

    for y in range(-height, height * 2, step_y):
        for x in range(-width, width * 2, step_x):
            # Draw subtle drop shadow + crisp white text with dark outline
            draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0, int(180 * opacity)))
            draw.text((x, y), text, font=font, fill=(255, 255, 255, int(255 * opacity)))

    # Rotate overlay
    rotated_overlay = overlay.rotate(angle, resample=Image.BICUBIC)

    # Crop rotated overlay back to original image size
    left = (rotated_overlay.width - width) // 2
    top = (rotated_overlay.height - height) // 2
    cropped_overlay = rotated_overlay.crop((left, top, left + width, top + height))

    # Composite
    watermarked = Image.alpha_composite(base_image, cropped_overlay)
    
    # Save output
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    if output_path.lower().endswith(".jpg") or output_path.lower().endswith(".jpeg"):
        watermarked.convert("RGB").save(output_path, "JPEG", quality=92)
    else:
        watermarked.save(output_path, "PNG")

    print(f"[WATERMARK] Saved: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Add tiled diagonal watermark to an image.")
    parser.add_argument("--input", "-i", required=True, help="Path to input image")
    parser.add_argument("--output", "-o", required=True, help="Path to output watermarked image")
    parser.add_argument("--text", "-t", default="PREVIEW DigiDreamWeaver", help="Watermark text")
    parser.add_argument("--opacity", type=float, default=0.28, help="Watermark opacity (0.0 to 1.0)")
    args = parser.parse_args()

    add_tiled_watermark(args.input, args.output, text=args.text, opacity=args.opacity)

if __name__ == "__main__":
    main()
