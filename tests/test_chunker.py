from app.ingestion.chunker import split_pages

def test_pages():
    chunks = split_pages([{"text": "Hello world", "page": 3}], "example.pdf")
    assert chunks[0].metadata["page"] == 3
