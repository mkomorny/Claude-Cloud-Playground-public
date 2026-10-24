---
name: coloring-page-colorways
description: Generates professional colored-in previews from blank coloring book line art. Produces 1 realistic colorway (matching the original source artwork's colors and lighting) plus 4 distinct creative colorways (pastel, jewel tones, neon, monochrome with color accent, etc.). Outputs unwatermarked full-resolution files, matching Procreate .swatches palettes, and watermarked preview images (PREVIEW DigiDreamWeaver). Trigger with /coloring-page-colorways, 'create colored in previews', 'colorize coloring book page', or 'generate colorways for coloring page'.
---

# Coloring Page Colorways: Digital Coloring Simulation & Palette Engine

Generates colored-in preview variants and palette assets from blank coloring book line art, strictly adhering to the DigiDreamWeaver shop standards.

---

## Canonical Line Art Grounding

Colorways are generated exclusively from clean, closed line art adhering to the **Canonical Translation Prompt**:
* Lines remain 100% solid, fully opaque black (`#000000`).
* Colors are deposited into closed regions beneath the line art layer, simulating a master digital colorist working in Procreate.
* Zero color bleeding across closed boundary contours.

---

## Core Specification & Output Structure

For every blank coloring page, this skill produces:
1. **1 Realistic Colorway**: Samples colors directly from the original reference image and maps them into the line art regions with clean fills and soft lighting, recreating how a skilled digital colorer would paint it.
2. **4 Creative Colorways**: Curated high-end color themes selected from:
   - **`pastel`**: Soft, dreamy storybook tones (lavender, soft cyan, blush, butter).
   - **`jewel`**: Deep rich saturated jewel tones (amethyst, emerald, ruby, gold).
   - **`neon`**: High-contrast cyberpunk / vaporwave vibrancy on dark backdrop.
   - **`mono_accent`**: Sophisticated grayscale gradients punctuated by a single vibrant pop of color (e.g., crimson or teal).
   - **`ocean`**, **`sunset`**, **`candy`**, **`autumn`**, **`forest`**, **`iridescent`**.
3. **Layered Digital Simulation**: Colors are deposited within closed line contours with subtle volumetric gradients, while preserving the master pure black line art sharply on top.
4. **Dual Output (Unwatermarked Full-Res + Watermarked Previews)**:
   - **Unwatermarked Masters**: Full-resolution JPGs for buyer inspiration packages.
   - **Watermarked Previews**: Semi-transparent tiled `"PREVIEW DigiDreamWeaver"` diagonal watermark saved in `watermarked/` for public listing display.
5. **Bonus Palette Files**: Procreate `.swatches` files (importable directly into Procreate on iPad) plus hex-code color reference sheets.

---

## File Layout

Inside the page directory (`<OutputRoot>/<Page_Name>/`):

```text
<OutputRoot>/<Page_Name>/
├── <Page_Name>_1_realistic.jpg             # Unwatermarked full-res realistic colorway
├── <Page_Name>_2_creative_pastel.jpg       # Unwatermarked full-res pastel colorway
├── <Page_Name>_3_creative_jewel.jpg        # Unwatermarked full-res jewel colorway
├── <Page_Name>_4_creative_neon.jpg         # Unwatermarked full-res neon colorway
├── <Page_Name>_5_creative_mono_accent.jpg  # Unwatermarked full-res mono+accent colorway
├── watermarked/
│   ├── 1_realistic_wm.jpg                  # Watermarked realistic preview
│   ├── 2_creative_pastel_wm.jpg            # Watermarked pastel preview
│   ├── 3_creative_jewel_wm.jpg             # Watermarked jewel preview
│   ├── 4_creative_neon_wm.jpg              # Watermarked neon preview
│   └── 5_creative_mono_accent_wm.jpg       # Watermarked mono preview
└── palettes/
    ├── <Page_Name>_1_realistic.swatches    # Procreate .swatches file
    ├── <Page_Name>_1_realistic_hex.png     # Hex code visual palette sheet
    └── ... (palettes for each creative variant)
```

---

## Trigger Commands

Activate this skill when the user:
- Types `/coloring-page-colorways <page_folder>`
- Asks: *"create colored in previews of this coloring book blank"*
- Asks: *"generate colorways for this coloring page"*
- Asks: *"make watermarked previews and full-res colored versions"*
