#!/usr/bin/env python3
"""Add macOS-style window chrome to an animated GIF."""

import sys
from pathlib import Path
from PIL import Image, ImageDraw

TITLE_BAR_H = 36
BORDER = 1
CROP = 4  # pixels to trim from raw GIF edges (removes agg rounded corners)
TITLE_BG = (88, 96, 105)   # #586069 — GitHub fg.muted, clearly visible on #0d1117
BORDER_BG = (88, 96, 105)  # same as title bar for clean look
DOTS = [
    (255, 95, 87),   # red    #FF5F57
    (254, 188, 46),  # yellow #FEBC2E
    (40, 200, 64),   # green  #28C840
]
DOT_RADIUS = 6
DOT_Y = TITLE_BAR_H // 2
DOT_START_X = 20
DOT_SPACING = 20


def add_chrome(src: Path, dst: Path):
    img = Image.open(src)
    frames: list[Image.Image] = []
    durations: list[int] = []

    w, h = img.size
    # Cropped content dimensions
    cw = w - 2 * CROP
    ch = h - 2 * CROP
    # Final dimensions
    new_w = cw + 2 * BORDER
    new_h = ch + TITLE_BAR_H + BORDER

    # Build the chrome template once
    chrome = Image.new("RGB", (new_w, new_h), BORDER_BG)
    # Draw title bar
    draw = ImageDraw.Draw(chrome)
    draw.rectangle([0, 0, new_w, TITLE_BAR_H - 1], fill=TITLE_BG)
    # Traffic light dots
    for i, color in enumerate(DOTS):
        cx = BORDER + DOT_START_X + i * DOT_SPACING
        cy = DOT_Y
        draw.ellipse(
            [cx - DOT_RADIUS, cy - DOT_RADIUS, cx + DOT_RADIUS, cy + DOT_RADIUS],
            fill=color,
        )

    # Process each frame
    try:
        while True:
            frame = img.convert("RGB")
            # Crop rounded corners
            frame = frame.crop((CROP, CROP, w - CROP, h - CROP))
            canvas = chrome.copy()
            canvas.paste(frame, (BORDER, TITLE_BAR_H))
            frames.append(canvas)
            durations.append(img.info.get("duration", 100))
            img.seek(img.tell() + 1)
    except EOFError:
        pass

    frames[0].save(
        dst,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
    )
    print(f"✓ {dst} ({new_w}x{new_h}, {len(frames)} frames)")


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/raw.gif")
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("assets/demo.gif")
    add_chrome(src, dst)
