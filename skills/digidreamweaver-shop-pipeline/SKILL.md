---
name: digidreamweaver-shop-pipeline
description: Full commercial publishing orchestrator for the DigiDreamWeaver coloring book venture. Executes production pipeline using the canonical translation prompt, high-converting listing copywriting (Procreate SEO, 13 tags, narrative hooks, $1 catalog price or $0+ lead magnet), Gumroad draft setup and 10-product daily cap queue management, watermarked Pinterest pins/carousels linked to live listings, and live catalog matrix updates. Trigger with /digidreamweaver-shop-pipeline, 'publish coloring page shop', 'run full coloring book shop pipeline', or 'publish to gumroad and pinterest'.
---

# DigiDreamWeaver Shop Pipeline: Autonomous Publishing & Social Orchestrator

Complete end-to-end commercial orchestrator replicating the exact multi-agent workflow developed by the DigiDreamWeaver bots.

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

## Canonical Translation Prompt Integration

All reference image conversions strictly use the **Canonical Translation Prompt** to guarantee pristine, fill-ready line art:

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

## The 5 Operational Phases

```
[Phase 1: Asset Production]
   ├── Canonical Line Art Translation (Pure B&W, bucket-fill leak proof, SVG)
   ├── 1 Realistic Colorway + 4 Creative Colorways
   ├── iPad Fitted Formats (2048x2732 / 2732x2048) + Print PDFs (Letter & A4)
   └── Compiled Customer Delivery Zip in _zips/<Name>.zip (includes original reference art) (includes original reference art) (includes original reference art) (includes original reference art)
           │
[Phase 2: Marketing Asset Generation]
   ├── Tiled Watermarked Previews (0_blank -> 1_realistic -> 2..5_creative)
   ├── Tall 1000x1500 Pinterest Pin (Blank top, colorways below, no cropping)
   ├── Gumroad 1280x720 Cover (Split 50% blank left, 2x2 colorways right)
   └── Square 1000x1000 Split Comparison Thumbnail
           │
[Phase 3: High-Converting Copywriting]
   ├── Procreate / iPad Optimized Keyword Title with fill area counts
   ├── Short Storytelling Narrative Hook
   ├── 13 High-Intent Tags
   └── Pricing: $1.00 standard catalog | $0+ for lead magnets (collect emails)
           │
[Phase 4: Gumroad Publishing & Daily Cap Queue]
   ├── Stage as unpublished draft first (never publish without Miranda's go-ahead)
   ├── Enforce Gumroad's 10 new products/day cap with daily batch queueing (~9:15 AM ET)
   └── Generate field-by-field checklist (gumroad_checklist.md) & API sync
           │
[Phase 5: Pinterest Social Traffic Engine]
   ├── Target Board: "Digital Coloring Pages" on DigiDreamWeaver
   ├── Lead with 1000x1500 tall before-and-after pin, followed by carousel
   ├── Pin strictly AFTER Gumroad listing URL is active (links directly to buy page)
   └── Update catalog.md & catalog.json status matrix
```

---

## Operational Rules & Guardrails

1. **Explicit Approval Gate for Publishing**: New listings are prepared as **unpublished drafts**. They are only marked live when Miranda explicitly authorizes publishing (*"publish the coloring pages"*).
2. **Safe Source File Retention**: Never delete source artwork until the completed product folder has been verified and backed up.
3. **No AI Mention in Gumroad Copy**: Keep AI disclosures off public Gumroad descriptions per Miranda's branding rule (disclose only on platforms that require checkboxes, e.g. Etsy).
4. **Order of Previews**: Always maintain strict preview sequence:
   - `0_blank_wm.jpg` (main cover/lead image)
   - `1_realistic_wm.jpg` (realistic matched to original)
   - `2..5_creative_*_wm.jpg` (creative palettes)
5. **Daily Limit Rollover**: If a batch exceeds 10 items, the excess is scheduled into `publish_queue.json` for the next day's window.

---

## Trigger Commands

Activate this skill when the user:
- Types `/digidreamweaver-shop-pipeline <input_path>`
- Asks: *"run the full shop pipeline on these images"*
- Asks: *"prep these coloring pages for Gumroad and Pinterest"*
- Asks: *"generate listing copy, covers, pins, and queue for publishing"*
