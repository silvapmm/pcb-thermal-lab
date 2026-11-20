#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_icon.py
@brief Draws the application icon (a thermometer on a green board) and writes every file of `ico/`.

The artwork is original and fully procedural (rounded rectangles, circles and lines drawn with Pillow): a thermometer
stands on a green board tile, its top ends in a copper via, and faint traces run beside it. Sizes of 48 px and more
keep the traces and the via; 32 px has heavier strokes and 24 and 16 px keep a minimal circuit (two trace strokes and
the via dot) so the thermometer stays readable in a title bar or a tray.
The output is deterministic: running the script twice gives the same pixels.

Usage: python examples/make_icon.py [output_folder]   (default: ico)

Writes `pcb-board.png` (1024 px master), `png/pcb-board_<size>.png` (16 to 1024 px), `pcb-board.ico` (16 to 256 px,
Windows) and, on macOS where `iconutil` exists, `pcb-board.icns`.
"""

import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

## Sizes of the PNG set, in px.
PNG_SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)
## Sizes stored in the Windows .ico, in px.
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
## Largest size that uses the minimal circuit (two trace strokes and the via dot), in px.
MINI_MAX = 24
## Largest size that uses the heavier-trace drawing, in px.
MID_MAX = 32

# Colours (RGBA)
BOARD = (30, 120, 70, 255)
BOARD_DARK = (22, 95, 55, 255)
TRACE_FAINT = (60, 160, 100, 255)
TRACE_MINI = (95, 190, 130, 255)
GLASS = (245, 245, 240, 255)
MERCURY = (225, 60, 40, 255)
COPPER = (236, 190, 70, 255)
TICK = (120, 120, 120, 255)
HIGHLIGHT = (255, 160, 140, 255)


def _box(n, *v):
    """!
    @brief Scale a normalised box or point list to pixels.
    @param n Image side in px.
    @param v Normalised coordinates (0 to 1).
    @return list Coordinates in px.
    """
    return [c * n for c in v]


def _trace(d, n, pts, width, fill, pad=0.028):
    """!
    @brief Draw a polyline with round caps and a round pad at its end, like a PCB trace ending in a pad.
    @param d ImageDraw object.
    @param n Image side in px.
    @param pts Normalised vertices (x, y).
    @param width Normalised line width.
    @param fill RGBA colour.
    @param pad Normalised radius of the pad at the last vertex.
    @return None
    """
    xy = [(x * n, y * n) for x, y in pts]
    d.line(xy, fill=fill, width=max(1, int(round(width * n))), joint="curve")
    r = width * n / 2
    # Round caps at both ends so the strokes look like copper, not like cut lines
    for px, py in (xy[0], xy[-1]):
        d.ellipse((px - r, py - r, px + r, py + r), fill=fill)
    # Pad at the free end (a bit larger than the trace)
    px, py = xy[-1]
    r = pad * n
    d.ellipse((px - r, py - r, px + r, py + r), fill=fill)


def draw_icon(n, size):
    """!
    @brief Draw the icon on an n x n transparent canvas.
    @param n Canvas side in px (draw at a multiple of the final size and reduce, for anti-aliasing).
    @param size Final size in px: 24 and below use the minimal circuit (two trace strokes and the via dot),
                32 uses heavier traces, larger sizes the full drawing.
    @return PIL.Image.Image RGBA image.
    """
    mini = size <= MINI_MAX
    mid = size <= MID_MAX
    margin = 0.06
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(_box(n, margin, margin, 1 - margin, 1 - margin), radius=0.18 * n, fill=BOARD)
    # Traces on both sides of the thermometer (the board); thicker as the icon gets smaller
    tw = 0.07 if mini else (0.04 if mid else 0.022)
    pr = 0.06 if mini else (0.045 if mid else 0.028)
    if mini:
        routes = [[(0.14, 0.34), (0.30, 0.34)], [(0.86, 0.52), (0.70, 0.52)]]
    else:
        routes = [[(0.16, 0.30), (0.30, 0.30), (0.36, 0.36)], [(0.16, 0.44), (0.34, 0.44)],
                  [(0.84, 0.36), (0.70, 0.36), (0.64, 0.42)], [(0.84, 0.52), (0.66, 0.52)]]
    for route in routes:
        _trace(d, n, route, tw, TRACE_FAINT if not mini else TRACE_MINI, pad=pr)
    # Glass tube and bulb: wider in the small drawings so that they survive the reduction
    tube = 0.22 if mini else (0.19 if mid else 0.17)
    bulb = 0.19 if mini else 0.17
    d.rounded_rectangle(_box(n, 0.5 - tube / 2, 0.13, 0.5 + tube / 2, 0.66), radius=tube / 2 * n, fill=GLASS)
    d.ellipse(_box(n, 0.5 - bulb, 0.72 - bulb, 0.5 + bulb, 0.72 + bulb), fill=GLASS)
    # Red column and bulb
    col = 0.11 if mini else (0.09 if mid else 0.07)
    d.rounded_rectangle(_box(n, 0.5 - col / 2, 0.30, 0.5 + col / 2, 0.70), radius=col / 2 * n, fill=MERCURY)
    inner = bulb - (0.055 if mini else 0.045)
    d.ellipse(_box(n, 0.5 - inner, 0.72 - inner, 0.5 + inner, 0.72 + inner), fill=MERCURY)
    # The via at the top of the thermometer: a copper ring with a hole (a plain copper dot in the minimal drawing)
    vr = 0.075 if mini else (0.055 if mid else 0.04)
    if not mini:
        # A copper trace leaves the column and ends in the via: the link to the board
        _trace(d, n, [(0.5, 0.30), (0.5, 0.24)], 0.03 if not mid else 0.045, COPPER, pad=0.0)
    d.ellipse(_box(n, 0.5 - vr, 0.22 - vr, 0.5 + vr, 0.22 + vr), fill=COPPER)
    if not mini:
        hr = vr * 0.43
        d.ellipse(_box(n, 0.5 - hr, 0.22 - hr, 0.5 + hr, 0.22 + hr), fill=BOARD_DARK)
    if not mini and not mid:
        # Scale ticks on the right of the tube
        for k in range(5):
            y = 0.32 + k * 0.07
            d.line(_box(n, 0.5 + tube / 2 - 0.045, y, 0.5 + tube / 2 - 0.015, y), fill=TICK, width=int(0.01 * n))
    if not mini:
        # Highlight on the bulb
        d.ellipse(_box(n, 0.5 - 0.09, 0.64, 0.5 - 0.04, 0.69), fill=HIGHLIGHT)
    return im


def render(size):
    """!
    @brief Render the icon at its final size with supersampling.
    @param size Final side in px.
    @return PIL.Image.Image RGBA image of size x size.
    """
    # More supersampling for the tiny sizes, where every pixel counts
    ss = 8 if size <= 64 else 4
    big = draw_icon(size * ss, size)
    # BOX keeps the hard colour fields of the small drawings; LANCZOS is sharper for the detailed one
    return big.resize((size, size), Image.Resampling.BOX if size <= MID_MAX else Image.Resampling.LANCZOS)


def make_icns(images, path):
    """!
    @brief Build a macOS .icns with `iconutil` from a temporary .iconset (not kept).
    @param images Dict size (px) -> PIL image, holding 16, 32, 64, 128, 256, 512 and 1024.
    @param path Output .icns path.
    @return bool True if the file was written, False if `iconutil` is not available (not macOS).
    """
    if shutil.which("iconutil") is None:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        iconset = os.path.join(tmp, "pcb-board.iconset")
        os.makedirs(iconset)
        # Apple's names: icon_<s>x<s>.png and icon_<s>x<s>@2x.png (the pixel size is 2 s)
        for s in (16, 32, 128, 256, 512):
            images[s].save(os.path.join(iconset, f"icon_{s}x{s}.png"))
            images[2 * s].save(os.path.join(iconset, f"icon_{s}x{s}@2x.png"))
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", path], check=True)
    return True


def main(argv):
    """!
    @brief Write the icon files.
    @param argv Command line arguments (optional output folder, default `ico/` of the repository).
    @return int Exit status, 0 on success.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = argv[1] if len(argv) > 1 else os.path.join(root, "ico")
    os.makedirs(os.path.join(out, "png"), exist_ok=True)
    images = {s: render(s) for s in sorted(set(PNG_SIZES) | set(ICO_SIZES))}
    for s in PNG_SIZES:
        images[s].save(os.path.join(out, "png", f"pcb-board_{s}.png"))
    # The master keeps the name the code uses
    images[1024].save(os.path.join(out, "pcb-board.png"))
    # One multi-size .ico; Pillow resamples the base image unless each size is given as an append, so the
    # hand-tuned small versions are passed explicitly
    largest = images[max(ICO_SIZES)]
    largest.save(os.path.join(out, "pcb-board.ico"), format="ICO", sizes=[(s, s) for s in ICO_SIZES],
                 append_images=[images[s] for s in ICO_SIZES if s != max(ICO_SIZES)])
    if not make_icns(images, os.path.join(out, "pcb-board.icns")):
        sys.stderr.write("iconutil not found: pcb-board.icns not written (run on macOS)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
