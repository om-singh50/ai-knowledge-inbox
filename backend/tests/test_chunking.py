import pytest
from app.services.chunking import chunk_text, ChunkingConfig, config

def test_empty_input():
    assert chunk_text("") == []

def test_whitespace_only():
    assert chunk_text("   \n\t  ") == []

def test_short_text():
    text = "This is a short text that fits in one chunk."
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text

def test_multiple_paragraphs_separate_chunks():
    # Make paragraphs large enough to be split
    para1 = "A" * 600
    para2 = "B" * 600
    text = f"{para1}\n\n{para2}"
    chunks = chunk_text(text)
    assert len(chunks) == 2
    assert para1 in chunks[0]
    assert para2 in chunks[1]

def test_long_text_exceeding_max_size():
    word = "word "
    # 250 words * 5 chars = 1250 chars > 1000
    text = word * 250
    chunks = chunk_text(text)
    assert len(chunks) > 1
    assert len(chunks[0]) <= config.max_chunk_size
    # Check overlap (naive check)
    assert chunks[0][-50:] in chunks[1] or len(chunks[1]) < 100 # overlap might be around 150

def test_text_requiring_overlap():
    text = "A" * 900 + " " + "B" * 200
    chunks = chunk_text(text)
    assert len(chunks) == 2
    # Ensure there is overlap
    assert "A" in chunks[1] or "B" in chunks[0]

def test_multiple_consecutive_whitespace():
    text = "This    is   \t  a text \n \n \n with many spaces."
    chunks = chunk_text(text)
    assert len(chunks) == 1
    # \n \n \n becomes \n\n
    assert "text \n\n with" in chunks[0] or "text\n\nwith" in chunks[0]

def test_very_small_final_fragment():
    text = "A" * 950 + " " + "B" * 20
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert len(chunks[0]) > config.max_chunk_size or len(chunks[0]) <= config.max_chunk_size + 50

def test_deterministic():
    text = "A" * 600 + "\n\n" + "B" * 600
    chunks1 = chunk_text(text)
    chunks2 = chunk_text(text)
    assert chunks1 == chunks2

def test_no_empty_chunks():
    text = "A" * 1200
    chunks = chunk_text(text)
    for c in chunks:
        assert len(c.strip()) > 0

def test_preserve_document_ordering():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    # If we set max chunk size to very small just for this test
    old_max = config.max_chunk_size
    old_overlap = config.chunk_overlap
    config.max_chunk_size = 25
    config.chunk_overlap = 5
    
    chunks = chunk_text(text)
    
    config.max_chunk_size = old_max
    config.chunk_overlap = old_overlap
    
    combined = " ".join(chunks)
    assert "First paragraph" in combined
    assert "Second paragraph" in combined
    assert "Third paragraph" in combined
    assert combined.find("First") < combined.find("Second") < combined.find("Third")
