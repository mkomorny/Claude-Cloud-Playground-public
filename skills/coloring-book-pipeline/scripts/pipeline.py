#!/usr/bin/env python3
"""
pipeline.py - Standalone runner for coloring-book-pipeline.
End-to-end bundled workflow: converts images, generates line art, realistic + creative
colorways, iPad & PDF print files, Pinterest pin graphic, covers, thumbnails, and buyer zip.
Does NOT perform live social or Gumroad publishing.
"""
import os
import sys

# Locate cbengine.py in coloring-page-converter/scripts
ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "coloring-page-converter", "scripts"))
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

import cbengine  # noqa: E402


def main():
    cbengine.main(["pipeline"] + sys.argv[1:])


if __name__ == "__main__":
    main()
