"""Render the README motion study and its static storyboard."""

import argparse
from functools import cache
from math import atan2, cos, hypot, pi, sin
from pathlib import Path
from subprocess import check_output

from PIL import Image, ImageColor, ImageDraw, ImageFont


WIDTH, HEIGHT, SCALE, FPS = 768, 432, 2, 12


def mix(start, end, amount):
    start, end = ImageColor.getrgb(start), ImageColor.getrgb(end)
    return tuple(round(a + (b - a) * amount) for a, b in zip(start, end))


def ease(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


@cache
def font(family, size):
    path = check_output(["fc-match", "--format=%{file}", family], text=True)
    return ImageFont.truetype(path, round(size * SCALE))


class Canvas:
    def __init__(self, background):
        self.image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), background)
        self.pen = ImageDraw.Draw(self.image)

    @staticmethod
    def coords(xy):
        return tuple(round(value * SCALE) for value in xy)

    def txt(self, value, x, y, size, color, family, anchor="lt"):
        self.pen.text(self.coords((x, y)), value, fill=color, font=font(family, size), anchor=anchor)

    def rule(self, points, color, width=1):
        self.pen.line([self.coords(point) for point in points], fill=color,
                      width=max(1, round(width * SCALE)), joint="curve")

    def rect(self, rect, fill=None, outline=None, width=1, radius=0):
        if radius:
            self.pen.rounded_rectangle(self.coords(rect), round(radius * SCALE), fill=fill,
                                       outline=outline, width=max(1, round(width * SCALE)))
        else:
            self.pen.rectangle(self.coords(rect), fill=fill, outline=outline,
                               width=max(1, round(width * SCALE)))

    def disk(self, x, y, radius, fill=None, outline=None, width=1):
        self.pen.ellipse(self.coords((x-radius, y-radius, x+radius, y+radius)),
                         fill=fill, outline=outline, width=max(1, round(width * SCALE)))

    def arc(self, x, y, radius, start, end, color, width=1):
        self.pen.arc(self.coords((x-radius, y-radius, x+radius, y+radius)), start, end,
                     fill=color, width=max(1, round(width * SCALE)))

    def polygon(self, points, fill):
        self.pen.polygon([self.coords(p) for p in points], fill=fill)

    def arrow(self, start, end, color, width=2, head=8):
        self.rule([start, end], color, width)
        x, y = end
        angle = atan2(y - start[1], x - start[0])
        arms = [(x - head*cos(angle + offset), y - head*sin(angle + offset))
                for offset in (-0.55, 0.55)]
        self.polygon([end, *arms], color)

    def dashed(self, start, end, color, width=1, dash=5, gap=6):
        dx, dy = end[0] - start[0], end[1] - start[1]
        distance = hypot(dx, dy)
        for offset in range(0, round(distance), dash + gap):
            stop = min(offset + dash, distance)
            self.rule([(start[0]+dx*offset/distance, start[1]+dy*offset/distance),
                       (start[0]+dx*stop/distance, start[1]+dy*stop/distance)], color, width)

    def finish(self):
        return self.image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def export(frame, length, stills):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    panels = [frame(t) for t in stills]
    storyboard = Image.new("RGB", (WIDTH, len(panels) * HEIGHT + (len(panels)-1)*6), "#24242d")
    for index, panel in enumerate(panels):
        storyboard.paste(panel, (0, index * (HEIGHT + 6)))
    storyboard.save(args.out / "overview.png", optimize=True)

    # Keep a stable palette across frames so text and stationary areas do not shimmer.
    palette = storyboard.quantize(colors=112, method=Image.Quantize.MEDIANCUT)
    frames = [frame(i / FPS).quantize(palette=palette, dither=Image.Dither.NONE)
              for i in range(round(length * FPS))]
    frames[0].save(args.out / "overview.gif", save_all=True, append_images=frames[1:],
                   duration=round(1000/FPS), loop=0, disposal=1, optimize=True)


PAPER = "#f7f2dc"
TINT = "#e9dec3"
INK = "#18362e"
QUIET = "#4e6351"
TEAL = "#237864"
OXIDE = "#a4462f"
RAIL = "#89a091"
TITLE = "Open Sans Condensed:style=Bold"
BODY = "Open Sans Condensed:style=Bold"
COUNTS = "Liberation Mono:style=Bold"


def track(c, lane, y, amount, color):
    c.txt(lane, 34, y-32, 36, INK, TITLE)
    committed = amount >= 1
    c.txt("REV 1" if committed else "REV 0", 34, y+15, 23, QUIET, COUNTS)
    c.rule([(211, y-7), (694, y-7)], TINT, 12)
    c.rule([(211, y+7), (694, y+7)], RAIL, 1.5)
    for x in range(216, 693, 18):
        c.rule([(x, y-3), (x, y+7)], RAIL)
    for x in (246, 657):
        c.disk(x, y, 11, PAPER, color, width=2)
    for offset in (-22, 0, 22):
        x = 246 + 411*amount + offset
        c.disk(x, y, 8, color, PAPER, width=1.2)
    c.txt("FREE", 245, y+27, 23, QUIET, BODY, "mt")
    c.txt("HELD", 657, y+27, 23, QUIET, BODY, "mt")
    if committed:
        c.txt("OK", 729, y-11, 25, color, COUNTS, "rt")


def fork_path(c, start, middle, end, color):
    c.rule([start, middle, end], color, 2.5)
    c.arrow(middle, end, color, width=2.5, head=10)


def frame(t):
    c = Canvas(PAPER)
    separate = t < 4.3
    c.rect((0, 0, 12, HEIGHT), INK)
    c.txt("RHO FORGE", 35, 24, 22, QUIET, COUNTS)
    c.txt("Two offices can commit" if separate else "Two calls, one lane", 32, 58, 49, INK, TITLE)
    c.rule([(34, 118), (735, 118)], INK, 1.4)

    if separate:
        track(c, "Office A", 175, ease((t-0.45)/1.72), TEAL)
        c.rule([(34, 244), (735, 244)], TINT, 2)
        track(c, "Office B", 292, ease((t-0.65)/1.72), OXIDE)
        c.txt("One reservation per lane", 34, 394, 27, INK, BODY)
        c.txt("Two of four lanes", 732, 395, 25, QUIET, BODY, "rt")
    else:
        settled = t >= 5.88
        gates = ((153, 177), (153, 293))
        joint = (352, 234)
        ends = [(578, 168), (578, 304)]
        c.txt("Call 1", 35, 156, 29, INK, TITLE)
        c.txt("REV 0", 35, 193, 24, QUIET, COUNTS)
        c.txt("Call 2", 35, 271, 29, INK, TITLE)
        c.txt("REV 0", 35, 308, 24, QUIET, COUNTS)
        for number, start in enumerate(gates):
            c.dashed(start, joint, color=RAIL, width=2)
            p = ease((t-4.55-number*0.12)/1.32)
            if not settled:
                x = start[0]+(joint[0]-start[0])*p
                y = start[1]+(joint[1]-start[1])*p
                c.disk(x, y, 9, TEAL if number == 0 else OXIDE)
        c.disk(*joint, 34, INK, PAPER, 3)
        c.txt("A", *joint, 34, PAPER, TITLE, "mm")
        c.txt("REV 1" if settled else "REV 0", 352, 281, 24, INK, COUNTS, "mt")
        for index, (end, label, color) in enumerate(zip(ends, ("OK", "STALE"), (TEAL, OXIDE))):
            mid = (459, 234)
            if settled:
                fork_path(c, joint, mid, end, color)
                p = ease((t-5.88-index*0.09)/0.68)
                if p < 1:
                    c.disk(mid[0]+(end[0]-mid[0])*p, mid[1]+(end[1]-mid[1])*p, 6, color)
                c.txt(label, 602, end[1]-13, 29, color, COUNTS)
            else:
                c.dashed(mid, end, TINT, width=2)
        c.txt("One commit on a fresh lane A", 34, 394, 27, INK, BODY)

    c.rule([(34, 370), (735, 370)], INK, 1.4)
    return c.finish()


if __name__ == "__main__":
    export(frame, 8.9, (3.4, 7.8))
