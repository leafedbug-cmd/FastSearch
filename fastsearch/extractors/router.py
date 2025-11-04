from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastsearch.config.settings import Settings


TEXT_EXTS = {".txt", ".md", ".py", ".json", ".log", ".csv", ".yaml", ".yml", ".xml", ".ini", ".cfg", ".toml", ".html", ".htm", ".css", ".js", ".ts"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
PDF_EXTS = {".pdf"}


def extract_text_for_index(path: Path, settings: Optional[Settings] = None, max_bytes: int = 2_000_000) -> Optional[str]:
    ext = path.suffix.lower()
    try:
        if ext in TEXT_EXTS:
            if path.stat().st_size > max_bytes:
                return None
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
                return text
        if ext in PDF_EXTS:
            try:
                from pypdf import PdfReader  # type: ignore
            except Exception:
                return None
            try:
                reader = PdfReader(str(path), strict=False)
                parts = []
                for page in reader.pages:
                    try:
                        t = page.extract_text() or ""
                    except Exception:
                        t = ""
                    if t:
                        parts.append(t)
                text = "\n".join(parts).strip()
                return text or None
            except Exception:
                return None
        if ext in IMAGE_EXTS:
            st = settings or Settings()
            if not st.enable_ocr:
                return None
            try:
                import pytesseract  # type: ignore
                from PIL import Image  # type: ignore
            except Exception:
                return None
            try:
                img = Image.open(path)
                text = pytesseract.image_to_string(img)
                return (text or "").strip() or None
            except Exception:
                return None
    except Exception:
        return None
    return None
