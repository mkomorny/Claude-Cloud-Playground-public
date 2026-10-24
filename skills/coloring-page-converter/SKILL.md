---
name: coloring-page-converter
description: Converts reference photos, AI artwork, or sketches into professional, high-precision (>=4096px, 300 DPI) digital coloring book pages using the canonical prompt. Enforces pure solid black lines on flat pure white background, leak-proof closed paths for instant bucket/drag-fill, fingertip tap targets, aspect ratio preservation, and produces unwatermarked master files (white JPG, transparent PNG, iPad, print PDFs, SVG) and watermarked previews (PREVIEW DigiDreamWeaver). Trigger with /coloring-page-converter, 'convert image to coloring page', 'create coloring book translation of image', or 'make coloring page from image'.
---

# Coloring Page Converter: High-Precision Line Art Engine

Converts photos, AI illustrations, or concept sketches into **production-grade digital coloring book pages** adhering strictly to the specifications established in the DigiDreamWeaver pipeline.

---

---

## Input Resolution & Search Rules (MANDATORY)

1. **NEVER Search for a "Gemini Image" Every Time**:
   * Do **NOT** search directories, libraries, or chat history for files named `Gemini_Generated_Image_*` or assume that a Gemini-branded image is required.
   * Do **NOT** run exploratory directory listings (`Get-ChildItem`, `os.listdir`, glob patterns) browsing for images when a file path is provided.
   * The reference art may originate from any source (phone photo, digital drawing, Midjourney, Grok, 3D render, etc.). Never mandate or seek a Gemini image.

2. **File Path Provided (Standard / Default Execution Flow)**:
   * The original image to translate will **usually be provided directly via file path** (e.g., `"<path_to_image>"`).
   * When an image or path to an image is provided:
     * **Immediately and directly use that provided path** as the original reference image to process.
     * **DO NOT search for the original image** elsewhere or browse other folders.
     * Pass the path straight to the conversion engine and execute without intermediate browsing steps.

3. **No File Path Provided (Fallback Search Flow Only)**:
   * **ONLY search for the original image when NO image and NO file path is provided** in the user's prompt (e.g., the command is invoked with no arguments).
   * In this fallback case only:
     * Check the designated originals staging folder:
       `C:\Users\<you>\OneDrive\Pictures\coloring book originals - translate\`
       and select the most recently modified image file.
     * If no files exist there, prompt the user for the image path.
     * Never wander into unrelated folders, photo libraries, or past product directories.

## Canonical Translation Prompt

When translating any reference image or artwork into a digital coloring page, the following canonical prompt must be used:

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

## Core Specification & Quality Rules

Every coloring page generated must adhere to these non-negotiable rules:
1. **Pure Black & White**: Solid black lines on flat pure white background (`#000000` on `#FFFFFF`). Absolutely zero grayscale values, zero pencil grain, zero charcoal texture, zero faded/sketchy strokes, zero halftones, zero airbrushing, and zero drop shadows.
2. **Bucket-Fill Ready (Leak-Proof)**: Every single drawn shape, contour, seam, and detail must form a completely closed path. Zero open vertices, micro-gaps, or broken outlines anywhere.
3. **Fingertip Tap Targets**: Eliminate any enclosed area that is too microscopic to tap easily on a standard tablet screen. Group, simplify, or merge tiny details into coherent, colorable islands.
4. **Composition & Framing Fidelity**: Exactly preserve the composition, camera perspective, framing, horizon line, and spatial placement of all subjects from the reference image. Do not crop, squeeze, stretch, or rearrange elements.
5. **Stylized Realism**: Translate complex organic elements (such as fur, clouds, foliage, water reflections, crater surfaces, and fabric folds) into stylized, graphic vector-like boundary lines rather than photorealistic shading or hatching.
6. **No Solid Black Blobs**: No solid black fills (except pupils where essential).
7. **Resolution Standards**: Minimum 4096 px on the long edge at 300 DPI.
8. **Watermarking Discipline**:
   - **Watermarked Preview**: `watermarked/0_blank_wm.jpg` with tiled diagonal semi-transparent `"PREVIEW DigiDreamWeaver"`.
   - **Unwatermarked Masters**: High-resolution white JPG, transparent PNG, and iPad formats are **never watermarked**.

---

## Output Architecture

Generated pages are stored under `<OutputRoot>/<Page_Name>/`:

```text
<OutputRoot>/<Page_Name>/
├── <Page_Name>_full_white.png        # Master 300 DPI 1-bit line art (unwatermarked)
├── <Page_Name>_full_white.jpg        # Full-res white background JPG (unwatermarked)
├── <Page_Name>_full_transparent.png  # Full-res transparent PNG for Procreate/layer apps (unwatermarked)
├── <Page_Name>_iPad_white.jpg        # iPad native white JPG (2048x2732 / 2732x2048)
├── <Page_Name>_iPad_transparent.png  # iPad native transparent PNG
├── <Page_Name>_print_Letter.pdf      # US Letter print PDF
├── <Page_Name>_print_A4.pdf          # A4 print PDF
├── <Page_Name>.svg                   # Resolution-independent vector line art (if potrace available)
├── watermarked/
│   └── 0_blank_wm.jpg                # Tiled diagonal watermarked preview
├── qc_report.json                    # Automated audit: cell counts, stroke width, leak warnings
├── qc_zoom_400.png                   # 400% zoom crop proof verifying line crispness
└── page.json                         # Technical metadata & conversion parameters
```

---

## Trigger Commands

Activate this skill when the user:
- Types `/coloring-page-converter <image_path>`
- Asks: *"create coloring book translation of this image"*
- Asks: *"turn this photo into a coloring page with watermarked preview"*
- Asks: *"extract clean line art from this image for Procreate"*
