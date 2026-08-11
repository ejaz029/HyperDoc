from dataclasses import dataclass


@dataclass
class Chunk:
    content: str
    page_number: int | None
    section: str | None
    chunk_index: int


def chunk_pages(
    pages: list[dict],
    max_chars: int = 1200,
    overlap: int = 150,
) -> list[Chunk]:
    chunks = []
    chunk_index = 0

    for page in pages:
        text = page["text"].strip()

        if not text:
            continue

        start = 0

        while start < len(text):
            end = min(start + max_chars, len(text))
            content = text[start:end].strip()

            if content:
                chunks.append(
                    Chunk(
                        content=content,
                        page_number=page.get("page_number"),
                        section=page.get("section"),
                        chunk_index=chunk_index,
                    )
                )
                chunk_index += 1

            if end >= len(text):
                break

            start = end - overlap

    return chunks