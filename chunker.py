def chunk_text(text, chunk_size=500, overlap=100):
    """
    Splits text into overlapping chunks.
    """
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i: i + chunk_size]
        chunks.append(" ".join(chunk))
        i += chunk_size - overlap
    return chunks

def chunk_all(scraped_dict):
    """
    scraped_dict: {url: full_clean_text}
    returns: list of dicts
    """
    all_chunks = []
    for url, content in scraped_dict.items():
        chunks = chunk_text(content)
        for idx, c in enumerate(chunks):
            all_chunks.append({
                "url": url,
                "chunk_index": idx,
                "text": c,
            })
    return all_chunks
