import os
from dotenv import load_dotenv

# Load env vars once.
load_dotenv()

# Vector DB
CHROMA_PATH = os.getenv("CHROMA_PATH", "chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "sunmarke_chunks")

# Retrieval
TOP_K = int(os.getenv("TOP_K", "6"))
MAX_CONTEXT_CHUNKS = int(os.getenv("MAX_CONTEXT_CHUNKS", "4"))
MAX_CHARS_PER_CHUNK = int(os.getenv("MAX_CHARS_PER_CHUNK", "1800"))
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.25"))

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
EMBED_TASK_TYPE = "RETRIEVAL_QUERY"
GEN_MODEL = os.getenv("GEN_MODEL", "gemini-2.5-flash")

# OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "tngtech/deepseek-r1t2-chimera:free")
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshotai/kimi-k2:free")
HTTP_TIMEOUT_S = float(os.getenv("HTTP_TIMEOUT_S", "60"))
MODEL_TIMEOUT_S = float(os.getenv("MODEL_TIMEOUT_S", str(HTTP_TIMEOUT_S)))
QA_OVERALL_TIMEOUT_S = float(os.getenv("QA_OVERALL_TIMEOUT_S", "30"))

# Voice
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# Prompts
SYSTEM_RULES = (
    "You are a strict retrieval QA assistant.\n"
    "You MUST answer using ONLY the information in the CONTEXT.\n"
    "Keep your answers upto 3 lines maximum.\n"
    'If the CONTEXT does not contain the answer, reply exactly: "No context found."\n'
    "Do NOT use outside knowledge. Do NOT guess.\n"
    "Keep the answer concise.\n"
    "Do not add explanations, assumptions, or background information.\n"
    "Do not rephrase the question in your answer.\n"
    "If multiple facts are present, only include the most relevant ones.\n"
    "Do not generate examples unless they are explicitly in the CONTEXT.\n"
    "Do not include any information that cannot be directly traced to the CONTEXT.\n"
)

def validate_required_config() -> None:
    # Fail fast if core keys are missing.
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY")
    if not OPENROUTER_API_KEY:
        raise RuntimeError("Missing OPENROUTER_API_KEY")

