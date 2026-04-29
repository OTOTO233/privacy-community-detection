"""Generate ultra-clear PNG diagrams with short node text."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "diagrams"
FONT_PATH = Path(r"C:\Windows\Fonts\simsun.ttc")

BG = "#f7f9fc"
INK = "#18324a"
MUTED = "#56697c"
LINE = "#335c81"
BLUE = "#eaf3ff"
GREEN = "#eef8ef"
ORANGE = "#fff4e5"
WHITE = "#ffffff"
SHADOW = "#dbe6f2"


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size=size)


TITLE_FONT = font(110)
SUBTITLE_FONT = font(44)
BOX_TITLE_FONT = font(100)
BODY_FONT = font(44)
TAG_FONT = font(42)


def draw_box(
    draw: ImageDraw.ImageDraw,
    rect: tuple[int, int, int, int],
    title: str,
    lines: Iterable[str],
    fill: str,
    outline: str,
) -> None:
    x1, y1, x2, y2 = rect
    draw.rounded_rectangle((x1 + 10, y1 + 12, x2 + 10, y2 + 12), radius=34, fill=SHADOW)
    draw.rounded_rectangle(rect, radius=34, fill=fill, outline=outline, width=5)
    title_bbox = draw.textbbox((0, 0), title, font=BOX_TITLE_FONT)
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    text_x = x1 + ((x2 - x1) - title_w) / 2
    text_y = y1 + ((y2 - y1) - title_h) / 2 - 8
    draw.text((text_x, text_y), title, font=BOX_TITLE_FONT, fill=INK)


def draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=LINE, width=8)
    if x1 == x2 and y2 > y1:
        draw.polygon([(x2, y2), (x2 - 18, y2 - 30), (x2 + 18, y2 - 30)], fill=LINE)
    elif y1 == y2 and x2 > x1:
        draw.polygon([(x2, y2), (x2 - 30, y2 - 18), (x2 - 30, y2 + 18)], fill=LINE)


def draw_tag(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, fill: str, outline: str) -> None:
    bbox = draw.textbbox((0, 0), text, font=TAG_FONT)
    w = bbox[2] - bbox[0] + 60
    h = 64
    draw.rounded_rectangle((x, y, x + w, y + h), radius=20, fill=fill, outline=outline, width=4)
    draw.text((x + 30, y + 12), text, font=TAG_FONT, fill=outline)


def save_png(image: Image.Image, path: Path) -> None:
    image.save(path, format="PNG", dpi=(300, 300), compress_level=1)


def algorithm_flowchart() -> None:
    image = Image.new("RGB", (3600, 4800), BG)
    draw = ImageDraw.Draw(image)

    draw.text((1320, 90), "算法流程图", font=TITLE_FONT, fill=INK)

    boxes = [
        ((900, 360, 2700, 620), "1 数据输入", [], BLUE, LINE),
        ((900, 740, 2700, 1000), "2 加密上传", [], BLUE, LINE),
        ((900, 1120, 2700, 1430), "3 隐私处理", [], ORANGE, "#b86b00"),
        ((900, 1550, 2700, 1810), "4 初始划分", [], GREEN, "#4e8a36"),
        ((900, 1930, 2700, 2290), "5 节点移动", [], GREEN, "#4e8a36"),
        ((900, 2410, 2700, 2720), "6 社区合并", [], GREEN, "#4e8a36"),
        ((900, 2840, 2700, 3150), "7 结束判断", [], GREEN, "#4e8a36"),
        ((900, 3270, 2700, 3580), "8 结果输出", [], BLUE, LINE),
        ((900, 3700, 2700, 3960), "9 可视化", [], BLUE, LINE),
    ]

    for rect, title, lines, fill, outline in boxes:
        draw_box(draw, rect, title, lines, fill, outline)

    for idx in range(len(boxes) - 1):
        curr = boxes[idx][0]
        nxt = boxes[idx + 1][0]
        draw_arrow(draw, ((curr[0] + curr[2]) // 2, curr[3]), ((nxt[0] + nxt[2]) // 2, nxt[1]))

    draw_tag(draw, 180, 1170, "隐私模块", "#fff9ef", "#b86b00")
    draw_box(draw, (160, 1260, 700, 1640), "核心作用", [], WHITE, "#b86b00")

    draw_tag(draw, 2820, 1930, "优化核心", "#f4fbf4", "#4e8a36")
    draw_box(draw, (2800, 2020, 3440, 2540), "DH-Louvain", [], WHITE, "#4e8a36")

    save_png(image, OUTPUT_DIR / "algorithm_flowchart.png")


def system_architecture() -> None:
    image = Image.new("RGB", (4800, 3200), BG)
    draw = ImageDraw.Draw(image)

    draw.text((1780, 90), "系统架构图", font=TITLE_FONT, fill=INK)

    draw_tag(draw, 200, 320, "前端层", BLUE, LINE)
    draw_box(draw, (180, 420, 1320, 860), "浏览器与Vue", [], WHITE, LINE)
    draw_box(draw, (180, 980, 1320, 1320), "Nginx", [], WHITE, LINE)
    draw_box(draw, (180, 1440, 1320, 1920), "用户输出", [], BLUE, LINE)

    draw_tag(draw, 1710, 320, "后端层", "#f4fbf4", "#4e8a36")
    draw_box(draw, (1640, 420, 3140, 820), "FastAPI服务", [], WHITE, "#4e8a36")
    draw_box(draw, (1640, 940, 2280, 1400), "本地多层系统", [], BLUE, "#4e8a36")
    draw_box(draw, (2380, 940, 3140, 1400), "云服务器1", [], ORANGE, "#b86b00")
    draw_box(draw, (1950, 1520, 2780, 2000), "云服务器2", [], GREEN, "#4e8a36")

    draw_tag(draw, 3490, 320, "资源层", "#fff9ef", "#b86b00")
    draw_box(draw, (3420, 420, 4580, 860), "数据集", [], WHITE, "#b86b00")
    draw_box(draw, (3420, 980, 4580, 1400), "算法模块", [], WHITE, "#b86b00")
    draw_box(draw, (3420, 1520, 4580, 2000), "输出部署", [], WHITE, "#b86b00")

    draw_arrow(draw, (1320, 640), (1640, 640))
    draw_arrow(draw, (3140, 640), (3420, 640))
    draw_arrow(draw, (1960, 820), (1960, 940))
    draw_arrow(draw, (2760, 820), (2760, 940))
    draw_arrow(draw, (2360, 1400), (2360, 1520))
    draw_arrow(draw, (1320, 1680), (1640, 1680))

    save_png(image, OUTPUT_DIR / "system_architecture.png")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    algorithm_flowchart()
    system_architecture()
    print(f"Generated diagrams in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
