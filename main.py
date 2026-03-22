"""
main.py
-------
Entry point for the Web Crawler & Link Graph Analyzer.

Run from the project root:
    python main.py

Requirements: Python 3.10+, standard library only (tkinter is built-in).
"""

import os
import sys

# ── Ensure the project root is on the path ────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.gui import App

PAGES_DIR = os.path.join(PROJECT_ROOT, "pages")


def main():
    if not os.path.isdir(PAGES_DIR):
        print(f"[ERROR] Pages directory not found: {PAGES_DIR}")
        sys.exit(1)

    app = App(pages_dir=PAGES_DIR)
    app.mainloop()


if __name__ == "__main__":
    main()
