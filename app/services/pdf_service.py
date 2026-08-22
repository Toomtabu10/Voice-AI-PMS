"""
PDF processing: extract text with pypdf, then structure with LLM.
"""
from pypdf import PdfReader
from pathlib import Path
from typing import Tuple
import aiofiles
from app.services.llm import extract_structured_from_text


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from a PDF file."""
    reader = PdfReader(file_path)
    texts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            texts.append(t)
    return "\n\n".join(texts)


async def process_pdf(
    file_path: str,
    patient_context: str = "",
) -> Tuple[str, dict]:
    """
    Extract text and run LLM structuring.
    Returns (raw_text, structured_dict).
    """
    raw_text = extract_text_from_pdf(file_path)
    if not raw_text.strip():
        return "", {"error": "No extractable text found in PDF"}

    structured = extract_structured_from_text(raw_text, patient_context)
    return raw_text, structured
