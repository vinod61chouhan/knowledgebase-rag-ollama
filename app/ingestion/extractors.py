from pathlib import Path
import fitz
from docx import Document as WordDocument
from app.core.config import settings

def extract(path: str) -> list[dict]:
    suffix = Path(path).suffix.lower()
    if suffix in (".txt", ".md"):
        return [{"text": Path(path).read_text(encoding="utf-8", errors="replace"), "page": None}]
    if suffix == ".docx":
        doc = WordDocument(path)
        lines = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            lines.extend(" | ".join(cell.text for cell in row.cells) for row in table.rows)
        return [{"text": "\n".join(lines), "page": None}]
    if suffix == ".pdf":
        pages = []
        with fitz.open(path) as pdf:
            for i, page in enumerate(pdf, 1):
                text = page.get_text("text")
                if not text.strip() and settings.ocr_enabled:
                    import pytesseract
                    from PIL import Image
                    import io
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    text = pytesseract.image_to_string(
                        Image.open(io.BytesIO(pix.tobytes("png"))), lang=settings.ocr_language)
                try:
                    for table in page.find_tables().tables:
                        text += "\n" + "\n".join(" | ".join(str(c or "") for c in row)
                            for row in table.extract())
                except (AttributeError, ValueError):
                    pass
                pages.append({"text": text, "page": i})
        return pages
    raise ValueError(f"Unsupported extension: {suffix}")
