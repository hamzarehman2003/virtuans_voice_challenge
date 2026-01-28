from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import clients, config
from .routes_qa import router as qa_router
from .routes_voice import router as voice_router


def create_app() -> FastAPI:
    # Build the FastAPI app and wire dependencies.
    config.validate_required_config()
    print(f"✅ Deepgram: {'Enabled' if config.DEEPGRAM_API_KEY else 'Disabled'}")

    app = FastAPI(title="RAG QA: Gemini + DeepSeek + Kimi (OpenRouter)")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    collection = clients.build_chroma_collection()
    genai_client = clients.build_genai_client()
    deepgram_client = clients.build_deepgram_client()

    # Attach shared clients to routers.
    qa_router.collection = collection
    qa_router.genai_client = genai_client
    voice_router.collection = collection
    voice_router.deepgram_client = deepgram_client

    app.include_router(qa_router)
    app.include_router(voice_router)
    return app


app = create_app()

