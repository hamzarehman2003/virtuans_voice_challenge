import asyncio
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from . import config, llm, retrieval
from .schemas import QARequest, QAResponse, SourceChunk


router = APIRouter()


@router.post("/qa", response_model=QAResponse)
async def qa(req: QARequest):
    # Non-streaming QA response (kept for compatibility).
    q = req.question.strip()
    top_k = req.top_k or config.TOP_K

    chunks, has_context = retrieval.retrieve(router.collection, router.genai_client, q, top_k)

    sources = []
    for c in chunks[: config.MAX_CONTEXT_CHUNKS]:
        m = c["meta"] or {}
        sources.append(
            SourceChunk(
                id=c["id"],
                similarity=float(c["sim"]),
                url=m.get("url"),
                title=m.get("title"),
                source_file=m.get("source_file"),
                chunk_index=m.get("chunk_index"),
                preview=(c["doc"][:220].replace("\n", " ") + "..."),
            )
        )

    if not has_context:
        return QAResponse(
            question=q,
            has_context=False,
            answers={"gemini": "No context found.", "deepseek": "No context found.", "kimi": "No context found."},
            sources=sources,
        )

    context = retrieval.build_context(chunks)
    prompt = retrieval.make_prompt(q, context)

    async def _safe_call(coro) -> str:
        try:
            return await coro
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    tasks: Dict[str, asyncio.Task] = {
        "gemini": asyncio.create_task(_safe_call(llm.call_gemini(router.genai_client, prompt))),
        "deepseek": asyncio.create_task(_safe_call(llm.call_openrouter_model(config.DEEPSEEK_MODEL, prompt))),
        "kimi": asyncio.create_task(_safe_call(llm.call_openrouter_model(config.KIMI_MODEL, prompt))),
    }

    done, pending = await asyncio.wait(set(tasks.values()), timeout=config.QA_OVERALL_TIMEOUT_S)
    results: Dict[str, str] = {}

    for name, task in tasks.items():
        if task in done:
            try:
                results[name] = task.result()
            except Exception as e:
                results[name] = f"Error: {type(e).__name__}: {e}"

    for task in pending:
        task.cancel()
    for name, task in tasks.items():
        if task in pending:
            results[name] = f"Error: Timeout after {config.QA_OVERALL_TIMEOUT_S:.0f}s"

    return QAResponse(
        question=q,
        has_context=True,
        answers={
            "gemini": results.get("gemini") or "No context found.",
            "deepseek": results.get("deepseek") or "No context found.",
            "kimi": results.get("kimi") or "No context found.",
        },
        sources=sources,
    )


@router.get("/qa/stream")
async def qa_stream(question: str, top_k: Optional[int] = None):
    # Streaming QA response (SSE).
    q = (question or "").strip()
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Question too short")

    top_k_val = top_k or config.TOP_K
    chunks, has_context = retrieval.retrieve(router.collection, router.genai_client, q, top_k_val)

    sources = []
    for c in chunks[: config.MAX_CONTEXT_CHUNKS]:
        m = c["meta"] or {}
        sources.append(
            SourceChunk(
                id=c["id"],
                similarity=float(c["sim"]),
                url=m.get("url"),
                title=m.get("title"),
                source_file=m.get("source_file"),
                chunk_index=m.get("chunk_index"),
                preview=(c["doc"][:220].replace("\n", " ") + "..."),
            )
        )

    def _sse(event: str, data_obj: Any) -> str:
        return f"event: {event}\ndata: {json.dumps(data_obj, ensure_ascii=False)}\n\n"

    async def gen():
        yield _sse("meta", {"question": q, "has_context": has_context, "sources": [s.model_dump() for s in sources]})

        if not has_context:
            for m in ("gemini", "deepseek", "kimi"):
                yield _sse("answer", {"model": m, "text": "No context found."})
                yield _sse("model_done", {"model": m, "ok": True})
            yield _sse("done", {"ok": True})
            return

        context = retrieval.build_context(chunks)
        prompt = retrieval.make_prompt(q, context)

        queue: asyncio.Queue = asyncio.Queue()
        finals: Dict[str, str] = {"gemini": "", "deepseek": "", "kimi": ""}

        async def _emit(event: str, payload: dict):
            await queue.put((event, payload))

        async def _run_model(model: str):
            try:
                async with asyncio.timeout(config.MODEL_TIMEOUT_S):
                    if model == "gemini":
                        async for d in llm.stream_gemini(router.genai_client, prompt):
                            finals[model] += d
                            await _emit("delta", {"model": model, "delta": d})
                    elif model == "deepseek":
                        async for d in llm.stream_openrouter_model(config.DEEPSEEK_MODEL, prompt):
                            finals[model] += d
                            await _emit("delta", {"model": model, "delta": d})
                    elif model == "kimi":
                        async for d in llm.stream_openrouter_model(config.KIMI_MODEL, prompt):
                            finals[model] += d
                            await _emit("delta", {"model": model, "delta": d})
            except TimeoutError:
                await _emit("answer", {"model": model, "text": f"Error: Timeout after {config.MODEL_TIMEOUT_S:.0f}s"})
            except Exception as e:
                await _emit("answer", {"model": model, "text": f"Error: {type(e).__name__}: {e}"})
            finally:
                if finals.get(model):
                    await _emit("answer", {"model": model, "text": finals[model]})
                await _emit("model_done", {"model": model, "ok": True})

        producers = [
            asyncio.create_task(_run_model("gemini")),
            asyncio.create_task(_run_model("deepseek")),
            asyncio.create_task(_run_model("kimi")),
        ]

        done_models: set[str] = set()
        while len(done_models) < 3:
            event, payload = await queue.get()
            if event == "model_done":
                done_models.add(payload.get("model"))
            yield _sse(event, payload)

        for t in producers:
            if not t.done():
                t.cancel()

        yield _sse("done", {"ok": True})

    return StreamingResponse(gen(), media_type="text/event-stream")

