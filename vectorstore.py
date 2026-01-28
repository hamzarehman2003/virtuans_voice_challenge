import os
import chromadb
from dotenv import load_dotenv
import logging
load_dotenv()
logger = logging.getLogger(__name__)


def create_vectorstore(chunks, persist_dir="vectordb"):
    """
    Creates a persistent Chroma vector store from a list of text chunks.

    Arguments:
      chunks: list of dicts with keys "url", "chunk_index", "text"
      persist_dir: directory where the database will be stored

    Returns:
      client: the chromadb.PersistentClient instance
      collection: the Chroma collection storing the vectors
    """
    # Initialize persistent Chroma client
    os.makedirs(persist_dir, exist_ok=True)
    client = chromadb.PersistentClient(path=persist_dir)

    # Create or get the collection
    collection = client.get_or_create_collection(
        name="sunmarke_content"
    )

    # Prepare text list and metadata; filter out empty chunks
    records = [c for c in chunks if c.get("text") and c.get("text").strip()]
    if not records:
        raise ValueError("No non-empty text chunks provided to create_vectorstore")

    texts = [c["text"] for c in records]
    metadatas = [
        {"url": c["url"], "chunk_index": c["chunk_index"]} for c in records
    ]

    # Debug prints: show samples of texts
    print(f"Preparing {len(texts)} text chunks for embedding")
    for i, t in enumerate(texts[:3]):
        print(f"  sample text[{i}] len={len(t)} chars: {t[:200].replace('\n',' ')}")

    # Generate embeddings using available provider:
    # 1) Google Generative API if GOOGLE_API_KEY present
    # 2) Local sentence-transformers if configured/available
    # 3) (Optional) other providers can be added
    vectors = None
    google_key = os.getenv("GOOGLE_API_KEY")
    use_local = os.getenv("USE_LOCAL_EMBEDDINGS", "0") in ("1", "true", "yes")

    if google_key and not use_local:
        try:
            # Try langchain_google_genai wrapper if available
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            embedder = GoogleGenerativeAIEmbeddings(model="embedding-001")
            vectors = embedder.embed_documents(texts)
            logger.info("Generated %d embeddings via langchain_google_genai", len(vectors) if vectors else 0)
            print(f"Generated {len(vectors) if vectors else 0} embeddings via Google (langchain wrapper)")
        except Exception as e:
            # Try google.generativeai package, but don't fail hard — fall back to local model
            try:
                import google.generativeai as genai

                genai.configure(api_key=google_key)
                # The google.generativeai package API surface may vary by version; attempt common call
                if hasattr(genai, "embeddings"):
                    resp = genai.embeddings.create(model="textembedding-gecko-001", input=texts)
                    vectors = [getattr(d, "embedding", None) or d["embedding"] for d in resp.data]
                else:
                    # Unknown genai API; skip and fall back
                    print("google.generativeai installed but embeddings API not available in this version; falling back to local embeddings")
                    vectors = None

                if vectors:
                    logger.info("Generated %d embeddings via google.generativeai", len(vectors))
                    print(f"Generated {len(vectors)} embeddings via google.generativeai")
            except Exception as e2:
                print(f"Google Generative API attempt failed: {e2}; falling back to local embeddings")
                vectors = None

    if vectors is None:
        # Use local sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer
        except Exception:
            raise RuntimeError("No embedding provider available: install sentence-transformers or set GOOGLE_API_KEY")

        model_name = os.getenv("LOCAL_EMBED_MODEL", "all-MiniLM-L6-v2")
        model = SentenceTransformer(model_name)
        embs = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        vectors = [e.tolist() for e in embs]
        logger.info("Generated %d local embeddings using %s", len(vectors), model_name)
        print(f"Generated {len(vectors)} local embeddings using {model_name}")

    # print a small sample of the first embedding
    if vectors:
        sample_vec = vectors[0]
        print(f"  sample embedding[0] len={len(sample_vec)} first5={sample_vec[:5]}")

    # Add vectors to collection
    ids = []
    for i, c in enumerate(records):
        # Create a unique ID per chunk
        uid = f"{c['url']}_{c['chunk_index']}"
        ids.append(uid)

    # Validate embeddings
    if not vectors:
        raise RuntimeError("Embedding provider returned empty embeddings list")
    if len(vectors) != len(texts):
        raise RuntimeError(f"Embeddings length {len(vectors)} does not match texts length {len(texts)}")

    collection.add(
        ids=ids,
        embeddings=vectors,
        metadatas=metadatas,
        documents=texts
    )

    print("✔️ Vector store built and persisted to:", persist_dir)

    return client, collection
