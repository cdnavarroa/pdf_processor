from pathlib import Path
import fitz

# Umbral mínimo de chars para considerar que la página tiene texto nativo
_TEXT_MIN_CHARS = 20


def _is_scanned(text: str) -> bool:
    return len(text.strip()) < _TEXT_MIN_CHARS


def _ocr_page(page) -> str:
    """OCR de una página usando Tesseract si está disponible."""
    try:
        import pytesseract
        from PIL import Image
        import io
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img, lang="spa")
    except ImportError:
        return ""
    except Exception:
        return ""


class PDFExtractor:

    def extract(self, path: Path, max_pages: int | None = None) -> str:
        doc = fitz.open(str(path))
        limit = len(doc) if max_pages is None else min(max_pages, len(doc))
        parts = []
        for i in range(limit):
            page = doc[i]
            text = page.get_text()
            if _is_scanned(text):
                text = _ocr_page(page)
            parts.append(text)
        doc.close()
        return "\n".join(parts)

    def first_page(self, path: Path) -> str:
        return self.extract(path, max_pages=1)

    def page_count(self, path: Path) -> int:
        doc = fitz.open(str(path))
        n = len(doc)
        doc.close()
        return n

    def is_scanned(self, path: Path) -> bool:
        doc = fitz.open(str(path))
        text = doc[0].get_text() if len(doc) > 0 else ""
        doc.close()
        return _is_scanned(text)
