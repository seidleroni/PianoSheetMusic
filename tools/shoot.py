"""Headless screenshot / inspection tool for the PianoSheetMusic web app.

Renders the static app in a headless browser and writes a PNG (or evaluates a JS
expression and prints the result) -- without the Chrome extension and without a
manually-started server. This is the documented way to "look at the site" during
development: deterministic, scriptable, in-repo, and independent of any live
browser session.

No install step: `uv` resolves the dependency from the inline metadata below, and
Playwright drives your already-installed Chrome via `channel="chrome"`, so there is
no ~130 MB browser download.

Run from the repo root (or tools/):

    uv run tools/shoot.py                          # homepage -> tools/preview.png
    uv run tools/shoot.py --lefthand triads        # set left hand, then shoot
    uv run tools/shoot.py --route /index.html --out shot.png
    uv run tools/shoot.py --url https://seidleroni.github.io/PianoSheetMusic/
    uv run tools/shoot.py --eval "document.querySelectorAll('#note-labels span').length"

Unless you pass --url, it serves docs/ on an ephemeral localhost port for the
duration of the shot (the app must be served over http:// for its ES modules and
piece files to load).
"""
# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright"]
# ///
from __future__ import annotations

import argparse
import functools
import http.server
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

DOCS = Path(__file__).resolve().parent.parent / "docs"
DEFAULT_OUT = Path(__file__).resolve().parent / "preview.png"


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # silence per-request logging
        pass


def _serve(directory: Path):
    """Start a background static server on a free port; return (server, port)."""
    handler = functools.partial(_QuietHandler, directory=str(directory))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def _launch(p):
    """Prefer the installed Chrome (no download); fall back to bundled Chromium."""
    try:
        return p.chromium.launch(channel="chrome", headless=True)
    except Exception:
        # Needs `uv run --with playwright playwright install chromium` once.
        return p.chromium.launch(headless=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Headless screenshot of the app.")
    ap.add_argument("--url", help="Shoot this URL directly instead of serving docs/.")
    ap.add_argument("--route", default="/", help="Path under docs/ to open (default: /).")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="Output PNG (default: tools/preview.png).")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--piece", help="Select this piece id in the <select> before shooting.")
    ap.add_argument("--lefthand", choices=["off", "notes", "triads"],
                    help="Set the left-hand accompaniment <select> before shooting.")
    ap.add_argument("--settle", type=int, default=700,
                    help="Extra ms to wait after load for OSMD render + label layout.")
    ap.add_argument("--full-page", action=argparse.BooleanOptionalAction, default=True,
                    help="Capture the whole page vs. just the viewport.")
    ap.add_argument("--eval", dest="js",
                    help="Evaluate a JS expression in the page and print the result (skips the screenshot).")
    args = ap.parse_args()

    httpd = None
    try:
        if args.url:
            url = args.url
        else:
            httpd, port = _serve(DOCS)
            url = f"http://127.0.0.1:{port}{args.route}"

        with sync_playwright() as p:
            browser = _launch(p)
            page = browser.new_page(viewport={"width": args.width, "height": args.height})
            page.goto(url, wait_until="networkidle")
            if args.piece:
                page.select_option("#piece", args.piece)
                page.wait_for_timeout(args.settle)
            if args.lefthand:
                page.select_option("#lefthand", args.lefthand)
            page.wait_for_timeout(args.settle)
            if args.js:
                print(page.evaluate(args.js))
            else:
                page.screenshot(path=args.out, full_page=args.full_page)
                print(args.out)
            browser.close()
    finally:
        if httpd:
            httpd.shutdown()


if __name__ == "__main__":
    main()
