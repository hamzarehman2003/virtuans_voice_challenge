import asyncio
import base64

from fastapi import APIRouter, File, HTTPException, UploadFile

from .schemas import SynthesisRequest


router = APIRouter()


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    # Transcribe audio to text with Deepgram.
    if not router.deepgram_client:
        raise HTTPException(status_code=400, detail="Deepgram not configured. Set DEEPGRAM_API_KEY in .env")

    audio_bytes = await audio.read()

    def _run_transcribe():
        return router.deepgram_client.listen.v1.media.transcribe_file(
            request=audio_bytes,
            model="nova-2",
            language="en",
            punctuate=True,
            smart_format=True,
        )

    response = await asyncio.to_thread(_run_transcribe)

    transcript = ""
    confidence = None
    try:
        ch0 = (response.results.channels or [])[0]
        alt0 = (ch0.alternatives or [])[0]
        transcript = (alt0.transcript or "").strip()
        confidence = alt0.confidence
    except Exception:
        try:
            transcript = (response["results"]["channels"][0]["alternatives"][0]["transcript"] or "").strip()
            confidence = response["results"]["channels"][0]["alternatives"][0].get("confidence")
        except Exception:
            transcript = ""

    if not transcript:
        raise HTTPException(status_code=400, detail="Could not transcribe audio. Please speak clearly.")

    return {"transcription": transcript, "confidence": confidence}


@router.post("/synthesize")
async def synthesize(req: SynthesisRequest):
    # Convert text to speech with Deepgram.
    if not router.deepgram_client:
        raise HTTPException(status_code=400, detail="Deepgram not configured. Set DEEPGRAM_API_KEY in .env")

    text = req.text.strip()
    model = req.model

    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    if len(text) > 5000:
        raise HTTPException(status_code=400, detail="Text is too long (max 5000 characters)")

    def _run_tts() -> bytes:
        chunks_iter = router.deepgram_client.speak.v1.audio.generate(
            text=text,
            model="aura-asteria-en",
            encoding="mp3",
        )
        return b"".join(chunks_iter)

    audio_bytes = await asyncio.to_thread(_run_tts)
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    return {"status": "success", "model": model, "audio_base64": audio_b64, "audio_type": "audio/mpeg"}


@router.get("/health")
async def health_check():
    # Simple health check endpoint.
    return {"status": "ok", "service": "Sunmarke Voice Agent", "vector_db": "ready" if router.collection else "not-ready"}

