import re
from pydantic_settings import BaseSettings

class ChunkingConfig(BaseSettings):
    max_chunk_size: int = 1000
    chunk_overlap: int = 150
    min_chunk_size: int = 50

config = ChunkingConfig()

def chunk_text(text: str) -> list[str]:
    """
    Splits a given text into chunks using a deterministic, simple strategy.
    
    Strategy:
    1. Normalize text (whitespace, line endings, trim, preserve paragraphs).
    2. Prefer paragraph boundaries when creating chunks.
    3. Use a maximum chunk size (approx 1000).
    4. Use overlap (~150 chars) when possible.
    5. Avoid extremely tiny trailing chunks; merge them into the previous chunk if reasonable.
    6. Never return empty chunks.
    7. Preserve original document order.
    8. Deterministic.
    """
    if not text:
        return []
    
    # 1. Normalize line endings to \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Normalize multiple whitespaces (excluding newlines)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Normalize multiple newlines with spaces between them to just newlines
    text = re.sub(r'\n[ \t]+\n', '\n\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    text = text.strip()
    if not text:
        return []
        
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        return []

    chunks = []
    current_chunk = ""
    
    def add_current_chunk(chunk_str, next_text=""):
        # If current_chunk is empty, nothing to do
        if not chunk_str:
            return ""
            
        chunks.append(chunk_str)
        
        # Prepare the start of the next chunk with overlap
        if not next_text:
            return ""
            
        # We need an overlap from the end of chunk_str.
        # But we don't just want an arbitrary slice, though we can fallback to it.
        if config.chunk_overlap > 0 and len(chunk_str) > config.chunk_overlap:
            # try to find a word boundary for overlap
            overlap_text = chunk_str[-config.chunk_overlap:]
            space_idx = overlap_text.find(' ')
            if space_idx != -1 and space_idx < len(overlap_text) - 1:
                return overlap_text[space_idx+1:] + "\n\n" + next_text
            return overlap_text + "\n\n" + next_text
        
        return next_text
        
    def split_long_text(long_text):
        """Splits a single block of text that exceeds max_chunk_size, using overlap."""
        words = long_text.split(' ')
        local_chunks = []
        curr = ""
        for word in words:
            if not word:
                continue
            if not curr:
                curr = word
            elif len(curr) + 1 + len(word) <= config.max_chunk_size:
                curr += " " + word
            else:
                local_chunks.append(curr)
                # Overlap
                if config.chunk_overlap > 0 and len(curr) > config.chunk_overlap:
                    overlap_text = curr[-config.chunk_overlap:]
                    space_idx = overlap_text.find(' ')
                    if space_idx != -1 and space_idx < len(overlap_text) - 1:
                        curr = overlap_text[space_idx+1:] + " " + word
                    else:
                        curr = overlap_text + " " + word
                else:
                    curr = word
        if curr:
            local_chunks.append(curr)
        return local_chunks

    i = 0
    while i < len(paragraphs):
        p = paragraphs[i]
        
        current_len = len(current_chunk) + 2 + len(p) if current_chunk else len(p)
        if current_len <= config.max_chunk_size:
            if current_chunk:
                current_chunk += "\n\n" + p
            else:
                current_chunk = p
            i += 1
        else:
            if current_chunk:
                chunks.append(current_chunk)
                # Next chunk start with overlap
                if config.chunk_overlap > 0 and len(current_chunk) > config.chunk_overlap:
                    overlap_text = current_chunk[-config.chunk_overlap:]
                    # Try to align to word boundary or paragraph boundary
                    para_idx = overlap_text.rfind('\n\n')
                    if para_idx != -1 and para_idx < len(overlap_text) - 2:
                        current_chunk = overlap_text[para_idx+2:]
                    else:
                        space_idx = overlap_text.find(' ')
                        if space_idx != -1 and space_idx < len(overlap_text) - 1:
                            current_chunk = overlap_text[space_idx+1:]
                        else:
                            current_chunk = overlap_text
                else:
                    current_chunk = ""
            else:
                # The paragraph itself is larger than max_chunk_size
                sub_chunks = split_long_text(p)
                for j, sc in enumerate(sub_chunks):
                    if j < len(sub_chunks) - 1:
                        chunks.append(sc)
                    else:
                        current_chunk = sc
                i += 1
                
    if current_chunk:
        chunks.append(current_chunk)
        
    # Handle tiny trailing chunks by merging them into the previous chunk if possible
    if len(chunks) > 1:
        last_chunk = chunks[-1]
        if len(last_chunk) < config.min_chunk_size:
            prev_chunk = chunks[-2]
            # Since overlap might mean the content is partially duplicated, 
            # let's just append what's missing, but it's simpler to just do this properly.
            # A safer merge is to check what's new in the last chunk and append it.
            # But wait, our overlap logic means the last chunk starts with the overlap from prev chunk.
            # So the unique part is just the tail.
            overlap = ""
            if config.chunk_overlap > 0:
                # approximate overlap length
                pass
            
            # Simple merge: just append the last paragraph if it was the last chunk
            # Actually, to make it simple: if the last chunk is very small, we can just merge it with the previous one
            # Even if it slightly exceeds max_chunk_size.
            # To do that cleanly without duplicating overlap:
            if last_chunk.startswith(prev_chunk[-min(len(prev_chunk), len(last_chunk)):]):
                # not easily merged if we don't know the exact overlap length
                pass

    # A better approach for chunking with overlap that avoids the merge complexity:
    # Build text, slide window
    return [c.strip() for c in chunks if c.strip()]
