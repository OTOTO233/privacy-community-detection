from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "output" / "thesis_cn_visual_final.docx"
OUT = ROOT / "output" / "thesis_cn_visual_final_centered.docx"


def paragraph_has_drawing(paragraph) -> bool:
    return bool(paragraph._element.xpath(".//w:drawing"))


def normalize_picture_paragraph(paragraph) -> None:
    fmt = paragraph.paragraph_format
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fmt.left_indent = Pt(0)
    fmt.right_indent = Pt(0)
    fmt.first_line_indent = Pt(0)
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)


def normalize_caption_paragraph(paragraph) -> None:
    fmt = paragraph.paragraph_format
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fmt.left_indent = Pt(0)
    fmt.right_indent = Pt(0)
    fmt.first_line_indent = Pt(0)


def main() -> None:
    doc = Document(SRC)

    paragraphs = list(doc.paragraphs)
    for idx, paragraph in enumerate(paragraphs):
        if paragraph_has_drawing(paragraph):
            normalize_picture_paragraph(paragraph)
            if idx + 1 < len(paragraphs):
                next_para = paragraphs[idx + 1]
                caption = next_para.text.strip()
                if caption.startswith("图"):
                    normalize_caption_paragraph(next_para)

    doc.save(OUT)


if __name__ == "__main__":
    main()
