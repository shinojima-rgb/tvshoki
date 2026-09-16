#!/usr/bin/env python3
"""Generate a 1200×630 original text/shape OG thumbnail (SVG + PNG).

WEB Designer lock (hamburg pilot visual, reuse forever):
  - Paper white background (#faf8f5)
  - Text + simple geometric shapes only
  - Small site name テレビでみた at the top
  - Center, large, short three lines: 番組名 / 短い日付 / 短い主題
    Example: サタデープラス / 8月29日 / ハンバーグ
  - Not お取り寄せ食品, not SKU names, not ranking, not 予告
  - No TV screenshots, program logos, manufacturer images, prices, or CTAs
  - Same PNG is og:image, twitter:image, and the date-index card

Usage (9/5 and later):
  python3 scripts/generate_og_thumb.py \\
    --slug 2026-09-05-example \\
    --program サタデープラス \\
    --date 9月5日 \\
    --topic ハンバーグ

Writes site/og/<slug>.svg and site/og/<slug>.png.

Rasterizer: rsvg-convert (librsvg). Japanese glyphs come from Noto Sans CJK JP
when installed (OFL, apt: fonts-noto-cjk), else Noto Sans JP / Hiragino Sans
via fontconfig. The SVG itself names Hiragino Sans / Noto Sans JP so browsers
match the live site stack. Do not invent English-only thumbs.
"""

from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "site" / "og"
WIDTH = 1200
HEIGHT = 630
FONT_STACK = "Hiragino Sans, Noto Sans JP, Noto Sans CJK JP, sans-serif"
BG = "#faf8f5"
INK = "#222"
MUTED = "#666"
HAIRLINE = "#e4dfd6"
RULE = "#1a1a1a"


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as fh:
        sig = fh.read(8)
        if sig != b"\x89PNG\r\n\x1a\n":
            raise SystemExit(f"{path} is not a PNG")
        length = struct.unpack(">I", fh.read(4))[0]
        chunk = fh.read(4)
        if chunk != b"IHDR" or length < 8:
            raise SystemExit(f"{path} missing IHDR")
        width, height = struct.unpack(">II", fh.read(8))
    return width, height


TOPIC_MAX_WIDTH = 1040        # 枠(1120)の内側に左右40pxずつ余白を残す
TOPIC_MAX_SIZE = 84
TOPIC_MIN_SIZE = 44


def _text_width(text: str, size: int) -> float:
    """全角はほぼ字送り1em、半角は約0.55em として見積もる。"""
    return sum(1.0 if ord(char) > 0x2E7F else 0.55 for char in text) * size


def _split_two_lines(topic: str, size: int, force: bool = False) -> list[str]:
    """意味の切れ目で2行に割る。`force` のときは幅に収まらなくても切れ目を優先する。

    幅で妥協して真ん中で割ると「feuquiage」が「feu / quiage」になり、読めない札になる。
    """
    for separator in ("（", "(", "・", "／", "/", " "):
        cut = topic.rfind(separator, 0, len(topic) * 2 // 3 + 1)
        if cut <= 0:
            continue
        head, tail = topic[:cut], topic[cut:].lstrip("（(")
        if force or max(_text_width(head, size), _text_width(tail, size)) <= TOPIC_MAX_WIDTH:
            return [head, tail]
    middle = len(topic) // 2
    return [topic[:middle], topic[middle:]]


def fit_topic(topic: str) -> tuple[list[str], int]:
    """収まる字の大きさと行を返す。1行で入らなければ2行、それでも入らなければ詰める。"""
    topic = " ".join(str(topic or "").split())
    for size in range(TOPIC_MAX_SIZE, TOPIC_MIN_SIZE - 1, -4):
        if _text_width(topic, size) <= TOPIC_MAX_WIDTH:
            return [topic], size
    for size in range(TOPIC_MAX_SIZE - 16, TOPIC_MIN_SIZE - 1, -4):
        lines = _split_two_lines(topic, size)
        if all(_text_width(line, size) <= TOPIC_MAX_WIDTH for line in lines):
            return lines, size
    size = TOPIC_MIN_SIZE
    trimmed = []
    for line in _split_two_lines(topic, size, force=True):
        original = line
        while line and _text_width(line + "…", size) > TOPIC_MAX_WIDTH:
            line = line[:-1]
        trimmed.append(line if line == original else line + "…")
    return trimmed, size


def svg_markup(program: str, date: str, topic: str) -> str:
    program_xml = escape(program)
    date_xml = escape(date)
    topic_lines, topic_size = fit_topic(topic)
    # 1行なら従来と同じ位置。2行は日付(baseline 372)の下から始めて枠(590)に収める。
    baselines = [478] if len(topic_lines) == 1 else [430, 430 + topic_size + 12]
    topic_xml = "\n  ".join(
        f'<text x="600" y="{y}" text-anchor="middle" font-family="{FONT_STACK}"'
        f' font-size="{topic_size}" font-weight="700" fill="{INK}">{escape(line)}</text>'
        for line, y in zip(topic_lines, baselines))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
  <rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>
  <rect x="40" y="40" width="1120" height="550" fill="none" stroke="{HAIRLINE}" stroke-width="2"/>
  <text x="600" y="108" text-anchor="middle" font-family="{FONT_STACK}" font-size="28" font-weight="500" fill="{MUTED}">テレビでみた</text>
  <rect x="552" y="128" width="96" height="3" fill="{RULE}"/>
  <text x="600" y="280" text-anchor="middle" font-family="{FONT_STACK}" font-size="96" font-weight="700" fill="{INK}">{program_xml}</text>
  <text x="600" y="372" text-anchor="middle" font-family="{FONT_STACK}" font-size="56" font-weight="500" fill="{MUTED}">{date_xml}</text>
  {topic_xml}
</svg>
"""


def rasterize_with_pillow(png_path: Path, program: str, date: str, topic: str) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise SystemExit("Pillow is required when no working SVG rasterizer is available") from exc
    font_path = Path("/System/Library/Fonts/Hiragino Sans GB.ttc")
    if not font_path.exists():
        raise SystemExit("Japanese font not found for Pillow fallback")
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, 1160, 590), outline=HAIRLINE, width=2)

    def centered(text: str, y: int, size: int, color: str) -> None:
        font = ImageFont.truetype(str(font_path), size=size, index=0)
        box = draw.textbbox((0, 0), text, font=font)
        x = (WIDTH - (box[2] - box[0])) / 2
        draw.text((x, y), text, font=font, fill=color)

    centered("テレビでみた", 74, 28, MUTED)
    draw.rectangle((552, 128, 648, 131), fill=RULE)
    centered(program, 178, 96, INK)
    centered(date, 318, 56, MUTED)
    topic_lines, topic_size = fit_topic(topic)
    top = 390 if len(topic_lines) == 1 else 386
    for index, line in enumerate(topic_lines):
        centered(line, top + index * (topic_size + 12), topic_size, INK)
    image.save(png_path, format="PNG")


def rasterize(svg_path: Path, png_path: Path, program: str, date: str, topic: str) -> None:
    rsvg = shutil.which("rsvg-convert")
    if rsvg:
        subprocess.run(
            [
                rsvg,
                "--width",
                str(WIDTH),
                "--height",
                str(HEIGHT),
                "--format",
                "png",
                "--output",
                str(png_path),
                str(svg_path),
            ],
            check=True,
        )
        return
    magick = shutil.which("magick")
    if magick:
        result = subprocess.run(
            [magick, "-background", "none", "-density", "96", str(svg_path), str(png_path)],
            capture_output=True,
        )
        if result.returncode == 0:
            return
    rasterize_with_pillow(png_path, program, date, topic)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", required=True, help="Output basename, e.g. 2026-08-29-hamburg")
    parser.add_argument("--program", required=True, help="番組名, e.g. サタデープラス")
    parser.add_argument("--date", required=True, help="短い放送日, e.g. 8月29日")
    parser.add_argument(
        "--topic",
        required=True,
        help="短い主題, e.g. ハンバーグ（カテゴリ名・SKU名・ランキング・予告は使わない）",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory for SVG and PNG (default: site/og)",
    )
    args = parser.parse_args()

    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_path = out_dir / f"{args.slug}.svg"
    png_path = out_dir / f"{args.slug}.png"

    svg_path.write_text(svg_markup(args.program, args.date, args.topic), encoding="utf-8")
    rasterize(svg_path, png_path, args.program, args.date, args.topic)

    width, height = png_dimensions(png_path)
    if (width, height) != (WIDTH, HEIGHT):
        raise SystemExit(f"{png_path} is {width}×{height}, expected {WIDTH}×{HEIGHT}")
    print(f"wrote {svg_path.relative_to(ROOT)}")
    print(f"wrote {png_path.relative_to(ROOT)} ({width}×{height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
