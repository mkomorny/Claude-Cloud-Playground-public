#!/usr/bin/env python3
"""
converter.py - Standalone runner for coloring-page-converter.
Converts any image or AI artwork into a clean, fill-ready coloring book page
with a watermarked preview and unwatermarked full-resolution master files.
"""
import os
import sys

# Locate cbengine.py relative to this script
ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

import cbengine  # noqa: E402


def main():
    # Pass arguments directly to cbengine convert
    cbengine.main(["convert"] + sys.argv[1:])


if __name__ == "__main__":
    main()
