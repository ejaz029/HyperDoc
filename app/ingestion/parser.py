from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader


def parse_document(file_path: str) -> list[dict]:
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".pdf":
        return _parse_pdf(path)

    if extension == ".docx":
        return _parse_docx(path)

    if extension == ".txt":
        return _parse_txt(path)

    raise ValueError(f"Unsupported file format: {extension}")


def _parse_pdf(path: Path) -> list[dict]:
    reader = PdfReader(str(path))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        if text.strip():
            pages.append(
                {
                    "page_number": page_number,
                    "section": None,
                    "text": text.strip(),
                }
            )

    return pages


def _parse_docx(path: Path) -> list[dict]:
    document = DocxDocument(str(path))

    text = "\n".join(
        paragraph.text
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    )

    return [
        {
            "page_number": None,
            "section": None,
            "text": text.strip(),
        }
    ]


def _parse_txt(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")

    return [
        {
            "page_number": None,
            "section": None,
            "text": text.strip(),
        }
    ]