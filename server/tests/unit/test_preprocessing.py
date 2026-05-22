from app.core.preprocessing import preprocess, chunk_text

def test_preprocess_strips_whitespace():
    assert preprocess("  hello world  ") == "hello world"

def test_preprocess_masks_urls():
    assert "[URL]" in preprocess("visit https://example.com today")

def test_chunk_text_splits_long_text():
    text = "Sentence one. " * 100
    chunks = chunk_text(text, chunk_size=100)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
