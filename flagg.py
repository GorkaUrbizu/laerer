#!/usr/bin/env python3
"""Flagg - a Norwegian flag waving in the terminal (Lærer's easter egg).

Pure ANSI escape codes, no dependencies. Each text line holds two pixel rows
using the half-block character, so pixels come out roughly square.

Run on its own to debug it:
    python3 flagg.py                  # play the animation
    python3 flagg.py --beside         # next to some sample text
    python3 flagg.py --frame 5        # print a single frame and exit
    python3 flagg.py --seconds 10 --fps 30
"""

import argparse
import math
import os
import re
import sys
import time

FLAG_RED = (186, 12, 47)
FLAG_WHITE = (255, 255, 255)
FLAG_BLUE = (0, 32, 91)
POLE = (170, 170, 170)

FLAG_SCALE = 2                       # pixels per flag unit (flag is 22 x 16)
FLAG_W, FLAG_H = 22 * FLAG_SCALE, 16 * FLAG_SCALE
WAVE_AMP = 3                         # max vertical displacement in pixels
POLE_W = 2
POLE_EXTRA = 8                       # pole length below the flag
CANVAS_H = FLAG_H + 2 * WAVE_AMP + POLE_EXTRA   # must be even
HEIGHT = CANVAS_H // 2               # text lines per frame
WIDTH = POLE_W + FLAG_W              # columns per frame, without indent

ANSI = re.compile(r"\033\[[0-9;?]*[A-Za-z]")


def visible_len(text):
    """Length of text as shown on screen, ignoring color codes."""
    return len(ANSI.sub("", text))


def flag_color(x, y):
    """Color of the Norwegian flag at pixel (x, y), or None outside it."""
    if not (0 <= x < FLAG_W and 0 <= y < FLAG_H):
        return None
    u, v = x / FLAG_SCALE, y / FLAG_SCALE
    if 7 <= u < 9 or 7 <= v < 9:
        return FLAG_BLUE
    if 6 <= u < 10 or 6 <= v < 10:
        return FLAG_WHITE
    return FLAG_RED


def color_code(rgb, background=False):
    """ANSI escape for an RGB color; truecolor if supported, else 256-color."""
    r, g, b = rgb
    if os.environ.get("COLORTERM", "") in ("truecolor", "24bit"):
        return f"\033[{48 if background else 38};2;{r};{g};{b}m"
    idx = 16 + 36 * round(r / 51) + 6 * round(g / 51) + round(b / 51)
    return f"\033[{48 if background else 38};5;{idx}m"


def frame(t, indent=4):
    """Render frame number t of the waving flag as a list of text lines."""
    pixels = [[None] * (POLE_W + FLAG_W) for _ in range(CANVAS_H)]
    for y in range(CANVAS_H):
        for x in range(POLE_W):
            pixels[y][x] = POLE
    for x in range(FLAG_W):
        # The wave grows away from the pole; its slope gives the shading.
        grip = x / FLAG_W
        phase = x * 0.28 - t * 0.9
        offset = round(WAVE_AMP * grip * math.sin(phase))
        light = 1 + 0.35 * grip * math.cos(phase)
        for y in range(FLAG_H):
            col = flag_color(x, y)
            shaded = tuple(max(0, min(255, int(ch * light))) for ch in col)
            pixels[y + WAVE_AMP + offset][POLE_W + x] = shaded

    lines = []
    for row in range(0, CANVAS_H, 2):
        out = []
        for top, bottom in zip(pixels[row], pixels[row + 1]):
            if top and bottom:
                out.append(color_code(top) + color_code(bottom, True) + "▀")
            elif top:
                out.append("\033[0m" + color_code(top) + "▀")
            elif bottom:
                out.append("\033[0m" + color_code(bottom) + "▄")
            else:
                out.append("\033[0m ")
        lines.append(" " * indent + "".join(out) + "\033[0m")
    return lines


def beside(left, flag_lines, gap=4):
    """Put flag_lines to the right of the text lines in left, tops aligned."""
    left_w = max((visible_len(s) for s in left), default=0)
    rows = max(len(left), len(flag_lines))
    out = []
    for i in range(rows):
        text = left[i] if i < len(left) else ""
        flag = flag_lines[i] if i < len(flag_lines) else ""
        pad = " " * (left_w - visible_len(text) + gap)
        out.append(text + "\033[0m" + pad + flag)
    return out


def wave(seconds=4.0, fps=15, left=None, gap=4):
    """Play the animation in place; Ctrl+C stops it early.

    With left (a list of text lines), the flag waves to the right of that
    text, which is printed as part of every frame.
    """
    sys.stdout.write("\033[?25l")                       # hide cursor
    height = HEIGHT if left is None else max(HEIGHT, len(left))
    try:
        for i in range(int(seconds * fps)):
            if i:
                sys.stdout.write(f"\033[{height}A")     # back to the top
            lines = frame(i) if left is None else beside(left, frame(i, 0), gap)
            sys.stdout.write("\n".join(lines) + "\n")
            sys.stdout.flush()
            time.sleep(1 / fps)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[0m\033[?25h")            # reset, show cursor
        sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(
        description="A Norwegian flag waving in the terminal.")
    parser.add_argument("--seconds", type=float, default=4.0,
                        help="animation length (default: 4)")
    parser.add_argument("--fps", type=int, default=15,
                        help="frames per second (default: 15)")
    parser.add_argument("--frame", type=int, metavar="N",
                        help="print only frame N and exit")
    parser.add_argument("--beside", action="store_true",
                        help="show the flag to the right of some sample text")
    args = parser.parse_args()

    left = None
    if args.beside:
        left = ["  RESULTS", "", "  Score: 10/10  (100%)", ""] + [
            f"  {i:>2}. + sample word {i}" for i in range(1, 11)]

    if args.frame is not None:
        lines = frame(args.frame) if left is None else beside(
            left, frame(args.frame, 0))
        print("\n".join(lines))
    else:
        wave(args.seconds, args.fps, left)


if __name__ == "__main__":
    main()
