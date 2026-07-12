import os
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings

settings = get_settings()

# Allowed file types and their extensions
ALLOWED_EXTENSIONS = {
    "text/plain": ".txt",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def allowed_file(content_type: str) -> bool:
    return content_type in ALLOWED_EXTENSIONS


async def save_upload_file(file: UploadFile) -> str:
    """Save uploaded file to disk, return file path."""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = ALLOWED_EXTENSIONS.get(file.content_type, ".bin")
    file_path = upload_dir / f"{file.filename}"
    # Ensure unique filename
    counter = 1
    while file_path.exists():
        stem = Path(file.filename).stem
        file_path = upload_dir / f"{stem}_{counter}{ext}"
        counter += 1

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValueError(f"File too large, max {settings.MAX_UPLOAD_SIZE_MB}MB")

    file_path.write_bytes(content)
    return str(file_path)


def extract_text(file_path: str, file_type: str) -> str:
    """Extract plain text from uploaded file based on file type."""
    if file_type == "text/plain":
        return Path(file_path).read_text(encoding="utf-8")

    elif file_type == "application/pdf":
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n\n".join(text_parts)

    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        from docx import Document
        doc = Document(file_path)
        text_parts = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(text_parts)

    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks
