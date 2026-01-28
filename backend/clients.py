import chromadb
from google import genai
from deepgram import DeepgramClient

from . import config


def build_chroma_collection():
    # Create a persistent Chroma collection.
    chroma_client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    return chroma_client.get_collection(config.COLLECTION_NAME)


def build_genai_client():
    # Create Google GenAI client.
    return genai.Client(api_key=config.GEMINI_API_KEY)


def build_deepgram_client():
    # Create Deepgram client if configured.
    return DeepgramClient(api_key=config.DEEPGRAM_API_KEY) if config.DEEPGRAM_API_KEY else None

