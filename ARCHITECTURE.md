# Architecture Overview

This document describes the high-level architecture of the Sunmarke Voice Agent.

Components
- Frontend: Vite + React app in the `frontend` folder. Provides a voice recorder UI, text query input, and displays model answers and source chunks. Communicates with backend via REST and SSE (`/qa`, `/qa/stream`).
- Backend API: FastAPI app (`app.py` -> `backend/main.py`). Exposes QA and voice endpoints. Handles routing, CORS, and client wiring.
- Vector store: ChromaDB persistent collection stored under `chroma_db` (persistent sqlite at `chroma_db/chroma.sqlite3`). Used for nearest-neighbor retrieval.
- LLM providers:
  - Gemini (Google GenAI): used for embeddings and optionally text generation (`GEMINI_API_KEY`).
  - OpenRouter models: used for additional generation models (configured via `OPENROUTER_API_KEY` and model names in `backend/config.py`).
  - Deepgram: optional STT for voice routes (`DEEPGRAM_API_KEY`).

Data flow
1. User submits a question (voice or text) from the frontend.
2. Backend `retrieval.retrieve()` embeds the query (via Gemini), queries the Chroma collection, and returns the top matching chunks.
3. `retrieval.build_context()` constructs a compact context block from the top chunks.
4. The backend builds a prompt (`retrieval.make_prompt()`) combining the system rules and context.
5. The backend calls multiple LLMs in parallel:
   - Gemini via `backend/llm.py` (non-streaming or streaming)
   - OpenRouter models (configured `DEEPSEEK_MODEL` and `KIMI_MODEL`) via HTTP
6. For streaming endpoints (`/qa/stream`) the backend aggregates incremental deltas from each model and emits Server-Sent Events (SSE) to the client.

Key implementation files
- `backend/config.py` — environment, timeouts, model names, and system prompt rules.
- `backend/clients.py` — builds Chroma, GenAI (Gemini), and Deepgram clients.
- `backend/retrieval.py` — embedding, vector search, context construction, and prompt composition.
- `backend/llm.py` — synchronous and streaming model call helpers (Gemini + OpenRouter).
- `backend/routes_qa.py` — QA endpoints and streaming SSE implementation.

Deployment
- Containerized via `Dockerfile` (Python 3.11) and `docker-compose.yml` which configures backend and frontend services.

Notes
- System rules (strict retrieval-only answers, brevity, and no hallucination) are in `backend/config.py` as `SYSTEM_RULES` and used when creating prompts.
- Chroma path and collection name are configurable via env vars. The app uses a persistent Chroma client so the `chroma_db` folder should be persisted between runs.

**Simple Architecture Diagram**

This minimal diagram shows what connects to what (no internals):

```
[Frontend (React UI)] ---> [Backend (FastAPI)]
       (sends text or audio)      |
                                  |
                                  v
                          [ChromaDB (vector store)]
                                  ^
                                  |
  [Gemini (embeddings & optional model)]
                 ^                |
                 |                v
           (embeddings)     [OpenRouter (models: DeepSeek, Kimi)]

[Backend] ---> [Deepgram (optional STT)]

Legend:
- Arrows indicate direction of request/response.
- Brackets are components; Backend mediates all interactions with LLMs and the vector store.
```
