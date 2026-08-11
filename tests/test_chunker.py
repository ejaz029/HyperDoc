from app.ingestion.chunker import chunk_pages


def test_chunk_pages_preserves_provenance():
    pages = [
        {
            "page_number": 3,
            "section": "Payment Terms",
            "text": "A" * 2500,
        }
    ]

    chunks = chunk_pages(pages, max_chars=1000, overlap=100)

    assert len(chunks) == 3

    assert chunks[0].page_number == 3
    assert chunks[0].section == "Payment Terms"

    assert chunks[1].page_number == 3
    assert chunks[1].section == "Payment Terms"

    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1