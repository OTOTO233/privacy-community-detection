from __future__ import annotations

from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "output" / "thesis_cn_visual_final_centered.docx"
OUT = ROOT / "output" / "thesis_cn_visual_final_fitted.docx"

EMU_PER_CM = 360000


def main() -> None:
    doc = Document(SRC)

    for section in doc.sections:
        usable_width = section.page_width - section.left_margin - section.right_margin
        target_width = int(usable_width * 0.96)

        for shape in doc.inline_shapes:
            if shape.width and shape.width > target_width:
                ratio = shape.height / shape.width if shape.width else 1
                shape.width = target_width
                shape.height = int(target_width * ratio)

    doc.save(OUT)


if __name__ == "__main__":
    main()
