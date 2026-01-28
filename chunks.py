"""
Chunk all scraped .txt files into JSONL for embeddings.

Input:  folder with .txt files (default: ./out)
Output: ./chunks.jsonl

Each JSONL line = one chunk with metadata:
{
  "chunk_id": "...",
  "source_file": "...",
  "url": "...",
  "title": "...",
  "chunk_index": 0,
  "text": "...",
  "char_len": 1234
}
"""

import os
import re
import json
import glob
import hashlib
from datetime import datetime

# ---------------- CONFIG ----------------
INPUT_DIR = "out"              # folder where your 70 txt files are
OUTPUT_JSONL = "chunks.jsonl"

# Chunking: prefer token-based if tiktoken exists; otherwise word-based.
TARGET_TOKENS = 900            # good default for embeddings
OVERLAP_TOKENS = 120

# Fallback (if no tiktoken):
TARGET_WORDS = 650
OVERLAP_WORDS = 80

MIN_CHARS_PER_CHUNK = 200      # skip tiny chunks
# ---------------------------------------


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def parse_header_and_body(raw: str):
    """
    If your txt file was saved like:
      URL: ...
      TITLE: ...

      <body>
    we extract URL/title; else url/title = None and body = raw
    """
    url = None
    title = None

    lines = raw.splitlines()
    if len(lines) >= 2 and lines[0].startswith("URL:"):
        url = lines[0].replace("URL:", "", 1).strip() or None
    if len(lines) >= 2 and lines[1].startswith("TITLE:"):
        title = lines[1].replace("TITLE:", "", 1).strip() or None

    # Body starts after the first blank line after header (if present)
    body = raw
    if (url is not None) or (title is not None):
        # find first empty line after line 0/1
        cut_idx = None
        for i in range(min(len(lines), 10)):
            if lines[i].strip() == "":
                cut_idx = i + 1
                break
        if cut_idx is not None:
            body = "\n".join(lines[cut_idx:])
        else:
            body = "\n".join(lines[2:])  # fallback

    return url, title, body

def get_tokenizer():
    """
    Try to use tiktoken if available. Otherwise return None.
    """
    try:
        import tiktoken  # type: ignore
        enc = tiktoken.get_encoding("cl100k_base")
        return enc
    except Exception:
        return None

def chunk_by_tokens(text: str, enc, target_tokens: int, overlap_tokens: int):
    tokens = enc.encode(text)
    chunks = []
    start = 0
    n = len(tokens)

    while start < n:
        end = min(start + target_tokens, n)
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens).strip()
        if len(chunk_text) >= MIN_CHARS_PER_CHUNK:
            chunks.append(chunk_text)

        if end == n:
            break
        start = max(0, end - overlap_tokens)

    return chunks

def chunk_by_words(text: str, target_words: int, overlap_words: int):
    words = text.split()
    chunks = []
    start = 0
    n = len(words)

    while start < n:
        end = min(start + target_words, n)
        chunk_text = " ".join(words[start:end]).strip()
        if len(chunk_text) >= MIN_CHARS_PER_CHUNK:
            chunks.append(chunk_text)

        if end == n:
            break
        start = max(0, end - overlap_words)

    return chunks

def main():
    enc = get_tokenizer()
    files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.txt")))

    if not files:
        raise FileNotFoundError(f"No .txt files found in '{INPUT_DIR}'")

    out_count = 0
    skipped_empty = 0

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as out:
        for file_path in files:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()

            url, title, body = parse_header_and_body(raw)
            body = normalize_whitespace(body)

            if not body or len(body) < MIN_CHARS_PER_CHUNK:
                skipped_empty += 1
                continue

            if enc:
                chunks = chunk_by_tokens(body, enc, TARGET_TOKENS, OVERLAP_TOKENS)
                method = "tokens"
                target = TARGET_TOKENS
                overlap = OVERLAP_TOKENS
            else:
                chunks = chunk_by_words(body, TARGET_WORDS, OVERLAP_WORDS)
                method = "words"
                target = TARGET_WORDS
                overlap = OVERLAP_WORDS

            base = os.path.basename(file_path)
            source_id = sha1(base + (url or ""))

            for idx, ch in enumerate(chunks):
                record = {
                    "chunk_id": f"{source_id}_{idx}",
                    "source_file": base,
                    "url": url,
                    "title": title,
                    "chunk_index": idx,
                    "text": ch,
                    "char_len": len(ch),
                    "chunking": {
                        "method": method,
                        "target": target,
                        "overlap": overlap,
                    },
                    "created_at": datetime.utcnow().isoformat() + "Z",
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_count += 1

    print(f"✅ Done.")
    print(f"- Input files: {len(files)}")
    print(f"- Chunks written: {out_count}")
    print(f"- Files skipped (too small/empty): {skipped_empty}")
    if enc:
        print("- Chunking mode: token-based (tiktoken detected)")
    else:
        print("- Chunking mode: word-based (tiktoken not installed)")
    print(f"- Output: {OUTPUT_JSONL}")

if __name__ == "__main__":
    main()
