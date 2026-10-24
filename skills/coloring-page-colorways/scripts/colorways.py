#!/usr/bin/env python3
"""
colorways.py - Standalone runner for coloring-page-colorways.
Generates realistic and creative colored previews from a blank coloring page.
Outputs both unwatermarked full-resolution versions and watermarked preview images.
"""
import os
import sys

# Locate cbengine.py in coloring-page-converter/scripts
ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "coloring-page-converter", "scripts"))
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

import cbengine  # noqa: E402


def main():
    cbengine.main(["colorize"] + sys.argv[1:])


if __name__ == "__main__":
    main()
