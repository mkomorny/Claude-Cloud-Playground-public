#!/usr/bin/env python3
"""
Coloring Book Product Bundle Builder
Orchestrates line art extraction, colorway creation, marketing pin generation,
ZIP archiving, and SEO listing copy formatting.
"""

import sys
import os
import zipfile
import argparse
from PIL import Image
from convert_lineart import extract_line_art
from generate_colorways import create_colorways
from watermark import add_tiled_watermark

def make_split_cover(blank_path: str, colorway_paths: list, output_path: str):
    """Creates split storefront cover: Blank line art left, 4 colorways 2x2 grid right."""
    blank = Image.open(blank_path).convert("RGB")
    target_h = 1600
    target_w = 2400
    
    cover = Image.new("RGB", (target_w, target_h), (255, 255, 255))
    
    # Left side: Blank line art (half width)
    left_w = target_w // 2
    blank_resized = blank.resize((left_w, target_h), Image.LANCZOS)
    cover.paste(blank_resized, (0, 0))
    
    # Right side: 2x2 grid of the 4 creative colorways
    cell_w = (target_w - left_w) // 2
    cell_h = target_h // 2
    
    for i, c_path in enumerate(colorway_paths[:4]):
        row = i // 2
        col = i % 2
        img = Image.open(c_path).convert("RGB").resize((cell_w, cell_h), Image.LANCZOS)
        cover.paste(img, (left_w + (col * cell_w), row * cell_h))
        
    cover.save(output_path, "JPEG", quality=92)
    print(f"[COVER] Built split storefront cover: {output_path}")

def make_pinterest_pin(blank_path: str, colorways: list, output_path: str):
    """Creates a tall 1000x1500 high-converting Pinterest pin."""
    pin_w = 1000
    pin_h = 1500
    pin = Image.new("RGB", (pin_w, pin_h), (255, 255, 255))
    
    # Blank line art top half (1000 x 750)
    blank = Image.open(blank_path).convert("RGB").resize((pin_w, 750), Image.LANCZOS)
    pin.paste(blank, (0, 0))
    
    # Two colored versions bottom half (500 x 750 each)
    if len(colorways) >= 2:
        c1 = Image.open(colorways[0]).convert("RGB").resize((500, 750), Image.LANCZOS)
        c2 = Image.open(colorways[1]).convert("RGB").resize((500, 750), Image.LANCZOS)
        pin.paste(c1, (0, 750))
        pin.paste(c2, (500, 750))
        
    pin.save(output_path, "JPEG", quality=92)
    print(f"[PINTEREST] Built tall 1000x1500 pin: {output_path}")

def package_customer_zip(lineart_files: dict, output_zip_path: str, original_path: str = None):
    """Packages customer-usable coloring files into the delivery archive, including the original reference artwork."""
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for key in ["full_white", "full_transparent", "ipad_white", "ipad_transparent"]:
            file_path = lineart_files.get(key)
            if file_path and os.path.exists(file_path):
                zf.write(file_path, arcname=os.path.basename(file_path))
        if original_path and os.path.exists(original_path):
            zf.write(original_path, arcname=os.path.basename(original_path))
    print(f"[ZIP] Packaged customer download (with original artwork): {output_zip_path}")

def generate_listing_copy(name: str, output_copy_path: str, price: str = "1.00", shop_name: str = "DigiDreamWeaver"):
    human_name = name.replace("_", " ").title()
    copy_content = f"""# Listing Sheet: {human_name} Digital Coloring Page

## Storefront Details
* **Shop**: {shop_name}
* **Price**: ${price} (or $0+ Pay-What-You-Want if used as audience lead magnet)
* **Instant Download**: Yes (.ZIP containing JPG and PNG files)

---

## Listing Title
{human_name} Digital Coloring Page for Procreate & ibisPaint | Intricate Adult Coloring Line Art | Transparent PNG & iPad Ready

---

## Product Description
Bring **{human_name}** to life with your favorite digital brushes or pencils! 

Expertly designed for digital colorists, this page features clean, closed, pure-black line art with **zero gray shading or muddy gradients**, guaranteeing seamless bucket-fill and drag-to-fill coloring in Procreate, ibisPaint, Krita, and Photoshop.

### What’s Included in Your Download:
* **Original Reference Artwork** (Full-color master file for inspiration & color matching)
* **Full-Resolution White JPG** (4K+ high-definition print & digital canvas)
* **Full-Resolution Transparent PNG** (Drop directly onto a layer above your colors)
* **iPad Native Formats** (2048×2732 resolution formatted with zero black bars)
* **Print-Ready PDFs** (US Letter & A4 for physical markers and colored pencils)

*Personal use only. Digital instant download.*

---

## Search Tags (Copy-Paste)
procreate coloring pages, digital coloring page, adult coloring, intricate coloring, ipad coloring, ibispaint coloring, transparent png line art, {name.lower().replace('_', ' ')}, coloring book page, instant download, relaxing coloring, printable coloring
"""
    with open(output_copy_path, "w", encoding="utf-8") as f:
        f.write(copy_content)
    print(f"[COPY] Generated SEO listing sheet: {output_copy_path}")

def build_full_bundle(
    input_path: str,
    output_parent_dir: str,
    name: str = "Coloring_Page",
    price: str = "1.00",
    shop_name: str = "DigiDreamWeaver"
):
    listing_dir = os.path.join(output_parent_dir, f"{name}_listing")
    os.makedirs(listing_dir, exist_ok=True)
    
    # 1. Line Art Extraction
    lineart_res = extract_line_art(input_path, listing_dir, name=name, watermark_text=f"PREVIEW {shop_name}")
    
    # 2. Colorways
    colorway_res = create_colorways(lineart_res["full_white"], listing_dir, source_image=input_path, name=name, watermark_text=f"PREVIEW {shop_name}")
    
    # 3. Split Cover
    cover_path = os.path.join(listing_dir, f"{name}_Cover_Split.jpg")
    make_split_cover(lineart_res["full_white"], colorway_res["creative"], cover_path)
    
    # 4. Pinterest Pin
    pin_path = os.path.join(listing_dir, f"{name}_Pin_1000x1500.jpg")
    make_pinterest_pin(lineart_res["full_white"], colorway_res["creative"], pin_path)
    
    # 5. Customer ZIP
    zip_path = os.path.join(listing_dir, f"{name}.zip")
    package_customer_zip(lineart_res, zip_path, original_path=input_path)
    
    # 6. SEO Copy
    copy_path = os.path.join(listing_dir, f"{name}_listing_copy.md")
    generate_listing_copy(name, copy_path, price=price, shop_name=shop_name)
    
    print(f"\n[DONE] Successfully assembled complete product bundle in: {listing_dir}")

def main():
    parser = argparse.ArgumentParser(description="Build complete coloring product bundle.")
    parser.add_argument("--input", "-i", required=True, help="Path to input image")
    parser.add_argument("--output-dir", "-o", default="./bundles", help="Parent output folder")
    parser.add_argument("--name", "-n", default="Coloring_Page", help="Product name slug")
    parser.add_argument("--price", "-p", default="1.00", help="Listing price")
    parser.add_argument("--shop", "-s", default="DigiDreamWeaver", help="Shop brand name")
    args = parser.parse_args()

    build_full_bundle(args.input, args.output_dir, name=args.name, price=args.price, shop_name=args.shop)

if __name__ == "__main__":
    main()
