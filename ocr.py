import os
import tempfile
from typing import Tuple

import pdfplumber
import pytesseract
from PIL import Image


def extract_text_from_image(file_path: str) -> str:
    try:
        image = Image.open(file_path)
        return pytesseract.image_to_string(image, lang="ita+eng")
    except Exception:
        return ""


def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
                # Attempt OCR on images if text is empty
                if not text.strip():
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_image:
                        page_image = page.to_image(resolution=300)
                        page_image.save(tmp_image.name, format="PNG")
                        text += extract_text_from_image(tmp_image.name)
                        os.unlink(tmp_image.name)
    except Exception:
        return text
    return text


def extract_text(file_path: str) -> Tuple[str, str]:
    lower = file_path.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(file_path), "pdf"
    return extract_text_from_image(file_path), "image"
