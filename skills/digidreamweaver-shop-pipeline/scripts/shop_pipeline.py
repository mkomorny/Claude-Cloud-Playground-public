#!/usr/bin/env python3
"""
shop_pipeline.py - Master runner for digidreamweaver-shop-pipeline.
Executes the full commercial workflow:
- Complete asset generation and packaging (cbengine pipeline)
- SEO listing copy generation (title, narrative hook, tags, $1 pricing)
- Gumroad draft generation and 10-products/day publishing queue
- Pinterest pin / carousel queueing and posting
- Shop catalog indexer (catalog.json / catalog.md)
"""
import os
import sys

# Locate cbengine.py in coloring-page-converter/scripts
ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "coloring-page-converter", "scripts"))
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

import cbengine  # noqa: E402


def main():
    if len(sys.argv) > 1 and sys.argv[1] in (
        "convert", "colorize", "package", "pipeline", "qc", "watermark",
        "listing", "catalog", "mark", "queue", "gumroad-checklist",
        "gumroad-sync", "pinterest-post"
    ):
        cbengine.main(sys.argv[1:])
    else:
        # Default action: run pipeline or show help
        cbengine.main(sys.argv[1:] if len(sys.argv) > 1 else ["--help"])


if __name__ == "__main__":
    main()
