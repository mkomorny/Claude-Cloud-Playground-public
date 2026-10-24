---
name: coloring-book-pipeline
description: Comprehensive asset bundling engine for digital coloring book products. Translates reference images into crisp digital pen-and-ink line art via the canonical prompt, generates 5 colorway variants, marketing covers, Pinterest pins, SEO copy, and customer delivery ZIP archives. Input rule: Uses provided file path directly as the original reference image without searching. Only searches for the latest original artwork in the originals staging folder when no path or image is provided. Never searches for Gemini images. Trigger with /coloring-book-pipeline, 'build coloring product bundle', 'package coloring book listing', or 'prepare coloring pack'.
---

# Digital Coloring Book Asset Pipeline (`coloring-book-pipeline`)

Production-grade composite orchestration skill that transforms reference images, concepts, and artwork into complete, commercial-ready digital coloring product bundles.

This skill automates **the entire creation and packaging lifecycle** up to the publishing boundary—generating all product files, marketing assets, and listing copy locally on your machine.

Compatible with **Google Antigravity**, **Claude (Desktop / Code)**, and **Grok CLI**.

---

## Input Resolution & Search Rules (MANDATORY)

1. **NEVER Search for a "Gemini Image" Every Time**:
   * Do **NOT** search directories, libraries, or chat history for files named `Gemini_Generated_Image_*` or assume that a Gemini-branded image is required.
   * Do **NOT** run exploratory directory listings (`Get-ChildItem`, `os.listdir`, glob patterns) browsing for images when a file path is provided.
   * The reference art may originate from any source (phone photo, digital drawing, Midjourney, Grok, 3D render, etc.). Never mandate or seek a Gemini image.

2. **File Path Provided (Standard / Default Execution Flow)**:
   * The original image to translate will **usually be provided directly via file path** (e.g., `/coloring-book-pipeline "C:\path\to\original_image.jpg"`).
   * When an image or path to an image is provided:
     * **Immediately and directly use that provided path** as the original reference image to translate.
     * **DO NOT search for the original image** elsewhere or browse other folders.
     * Pass the path straight to the conversion engine and run the pipeline without intermediate browsing steps.

3. **No File Path Provided (Fallback Search Flow Only)**:
   * **ONLY search for the original image when NO image and NO file path is provided** in the user's prompt (e.g., the user simply types `/coloring-book-pipeline` with no arguments).
   * In this fallback case only:
     * Check the designated originals staging folder:
       `C:\Users\<you>\OneDrive\Pictures\coloring book originals - translate\`
       and select the most recently modified image file.
     * If no files exist there, prompt the user for the image path.
     * Never wander into unrelated folders, photo libraries, or past product directories.

4. **Dual Input Mode (Line Art + Original Artwork)**:
   * If the user explicitly provides both a pre-existing line art file and an original reference file (e.g., `/coloring-book-pipeline "C:\path\to\lineart.png" and the original is "C:\path\to\original.jpg"`):
     * Use the line art as the input image and supply `--original "C:\path\to\original.jpg"`.
     * Do NOT search for any other files.

---

## Canonical Translation Prompt

When converting any reference image or artwork into an original digital coloring page, the following canonical prompt must be used:

```text
[TASK]
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
- OUTPUT SPECIFICATIONS: Razor-sharp edge definition, 4096 px minimum long edge, flat white background.
```

---

## The 5-Stage Assembly Pipeline

```text
[Reference Image] ──▶ 1. Canonical Line Art Translation ──▶ 2. Colorway Suite
                                                                    │
                                                                    ▼
[SEO Copy & ZIP] ◀── 5. Package & Archive ◀── 4. SEO Copy ◀── 3. Marketing Covers
```

### Stage 1: Canonical Line Art Translation & Verification
* Takes the provided reference image (or the newest staged original from `coloring book originals - translate` if no path was provided).
* Translates the reference image using the **Canonical Translation Prompt** into a crisp storybook pen-and-ink digital coloring page.
* Enforces post-processing standards:
  * Full-res pure black line art (`#000000`) on flat white JPG and transparent PNG (minimum 4096 px long edge, 300 DPI).
  * Native iPad formats (`2048×2732` portrait / `2732×2048` landscape) with zero cropping or distortion.
  * Print-ready PDFs (US Letter and A4).
  * Flood-fill closed contour testing (ensures zero bucket leaks).

### Stage 2: Realistic & Creative Colorway Suite
* Produces colored inspiration variants:
  * 1 Realistic Colorway matching source lighting and colors.
  * 4 Curated Creative Colorways (Pastel, Jewel Tones, Neon, Monochrome with accent).
  * Both master unwatermarked copies and light diagonally watermarked previews (`0_blank_wm.jpg` through `5_creative_*_wm.jpg`).
  * Matching Procreate `.swatches` palettes and hex code reference sheets.

### Stage 3: Marketing Cover & Social Pin Composition
* **Split Storefront Cover (`1280×720` / `2400×1600`)**: Clean side-by-side graphic featuring the blank line-art page on the left and four colored thumbnail versions on the right.
* **Tall Pinterest Graphic (`1000×1500`)**: High-converting vertical format optimized for feed clicks. Displays the blank line art on top and colored previews underneath.
* **Square Comparison Thumbnail (`1000×1000`)**: Split thumbnail showing half blank line art and half realistic color.

### Stage 4: Customer Delivery ZIP Packaging
* Compiles customer-facing files into a single clean archive: **`<Name>.zip`** in `_zips/`.
  * Contains the **original reference artwork** (`<Name>_original.*`), blank coloring files, iPad files, print PDFs, clean colorways, palettes, and a `README.txt`.
  * Excludes previews and watermarked files so buyers get a clean coloring experience with original art for reference and color matching.

### Stage 5: SEO Listing Copy & Catalog Update
Produces a formatted markdown listing sheet (`<Name>_listing_copy.md` or `listing.json`):
* **Optimized Title**: High search-volume keywords (`Procreate`, `ibisPaint`, `Adult Coloring`, `Instant Download`, fill area count).
* **Compelling Description**: Emphasizes closed lines ("Fill-ready, no leaks"), layer-ready transparent PNGs, and supported devices.
* **Keyword Tags**: 12–15 high-intent tags.
* **Pricing Strategy**: Identifies whether the item should be a **$0+ Pay-What-You-Want lead magnet** or a **$1.00–$3.00 single paid download**.
* **Catalog Sync**: Updates `catalog.json` and `catalog.md`.

---

## Output Directory Architecture

Every generated bundle is packaged into:

```text
C:\Users\<you>\OneDrive\Pictures\Coloring Book\<Name>/
├── <Name>_original.jpg                   # Original reference artwork (included in customer download)
├── <Name>_full_white.png                 # Master 1-bit line art (unwatermarked, 300 DPI)
├── <Name>_full_white.jpg                 # Full-res white background JPG (unwatermarked)
├── <Name>_full_transparent.png           # Full-res transparent PNG for layer apps (unwatermarked)
├── <Name>_iPad_white.jpg                 # iPad native white JPG (2048x2732 / 2732x2048)
├── <Name>_iPad_transparent.png           # iPad native transparent PNG
├── <Name>_print_Letter.pdf               # US Letter print-ready PDF
├── <Name>_print_A4.pdf                   # A4 print-ready PDF
├── <Name>_1_realistic.jpg                # Full-res realistic colorway
├── <Name>_2_creative_pastel.jpg          # Full-res pastel colorway
├── <Name>_3_creative_jewel.jpg           # Full-res jewel colorway
├── <Name>_4_creative_neon.jpg            # Full-res neon colorway
├── <Name>_5_creative_mono_accent.jpg     # Full-res mono accent colorway
├── <Name>_cover_1280x720.jpg             # Split storefront cover
├── <Name>_pin_1000x1500.jpg              # Tall Pinterest before-and-after graphic
├── <Name>_thumb_square.jpg               # Square split comparison thumbnail
├── <Name>_listing_copy.md                # Copy-paste SEO title, description, tags & pricing
├── page.json                             # Technical metadata, dimensions, cell counts, QC status
├── qc_report.json                        # Automated quality check audit
├── qc_zoom_400.png                       # 400% zoom crop proof verifying line crispness
├── palettes/                             # Procreate .swatches files + hex sheets
└── watermarked/                          # Public listing preview gallery
    ├── 0_blank_wm.jpg                    # Watermarked line art preview
    ├── 1_realistic_wm.jpg                # Watermarked realistic preview
    ├── 2_creative_pastel_wm.jpg          # Watermarked pastel preview
    ├── 3_creative_jewel_wm.jpg           # Watermarked jewel preview
    ├── 4_creative_neon_wm.jpg            # Watermarked neon preview
    └── 5_creative_mono_accent_wm.jpg     # Watermarked mono preview

Customer Download ZIP:
C:\Users\<you>\OneDrive\Pictures\Coloring Book\_zips\<Name>.zip
  (Includes original reference artwork, master blank line art JPG/PNG, iPad files, Letter/A4 PDFs, 5 colorway inspiration jpgs, palettes/ swatches + hex sheets, and README.txt)
```

---

## Trigger Commands & Invocations

* `/coloring-book-pipeline "C:\path\to\original_image.jpg"` *(Standard: uses provided file path immediately, zero searching)*
* `/coloring-book-pipeline` *(Fallback: auto-detects newest image in `coloring book originals - translate` folder)*
* `/coloring-book-pipeline "C:\path\to\lineart.jpg" --original "C:\path\to\original.jpg"` *(Dual input mode)*
* *"build a coloring product bundle for [image]"*
* *"package [image] as a complete coloring listing"*
* CLI execution:
  ```bash
  python "C:\Users\<you>\.agents\skills\coloring-page-converter\scripts\cbengine.py" pipeline \
    "C:\path\to\original_image.jpg" \
    --name "Eldritch_Hound"
  ```
