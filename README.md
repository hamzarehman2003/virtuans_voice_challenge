# Sunmarke Voice Agent

This repository contains a voice-enabled retrieval-augmented QA (RAG) service: a FastAPI backend that queries a Chroma vectorstore and multiple LLM providers, and a Vite + React frontend for voice input and question answering.

**Prerequisites**
- Python 3.10+ and pip
- Node 16+ (for the frontend)
- Docker & Docker Compose (optional)

**Required environment variables**
- `GEMINI_API_KEY` (required) — Google GenAI / Gemini API key
- `OPENROUTER_API_KEY` (required) — OpenRouter API key
- `DEEPGRAM_API_KEY` (optional) — Deepgram API key for speech-to-text
- Other optional env vars are in `backend/config.py` with sensible defaults (e.g. `CHROMA_PATH`, `COLLECTION_NAME`).

Setup (backend)
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate   # Windows
   source .venv/bin/activate # macOS / Linux
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file at the repo root and add the required keys:
   ```env
   GEMINI_API_KEY=your_gemini_key
   OPENROUTER_API_KEY=your_openrouter_key
   DEEPGRAM_API_KEY=optional_deepgram_key
   ```
4. Ensure the `chroma_db` folder exists (this repository includes a `chroma_db/chroma.sqlite3` file for persistence).

Run (backend)
- Local (dev):
  ```bash
  uvicorn app:app --reload --host 0.0.0.0 --port 8000
  ```
- Docker: build and run via the included `Dockerfile` or `docker-compose.yml`:
  ```bash
  docker-compose up --build
  ```

API
- POST `/qa` — non-streaming QA (JSON request with `question`)
- GET `/qa/stream` — streaming QA (Server-Sent Events; query param `question`)
- Voice routes are in `backend/routes_voice.py`.

Frontend
1. Install and run the frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. The frontend expects the backend API URL via `VITE_API_URL` (see `docker-compose.yml`).

Where to look
- Backend entry: `app.py` -> `backend/main.py` (FastAPI app creation)
- Config and environment: `backend/config.py`
- Vector DB client: `backend/clients.py` (Chroma persistent collection)
- Retrieval logic: `backend/retrieval.py`
- LLM calls + streaming: `backend/llm.py`
- QA routes: `backend/routes_qa.py`; voice routes: `backend/routes_voice.py`

Developer notes
- Required env vars are validated at startup in `backend/main.py` (via `config.validate_required_config()`).
- The app uses Gemini for embeddings and one or more LLMs (Gemini + models via OpenRouter). Adjust models in `backend/config.py`.

If you want, I can also run a smoke test (start backend and call `/qa`) or create a sample `.env.example` file.
