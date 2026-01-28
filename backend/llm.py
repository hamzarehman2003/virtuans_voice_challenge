import asyncio
import json

import httpx
from google.genai import types

from . import config


async def call_gemini(genai_client, prompt: str) -> str:
    # Call Gemini (non-streaming).
    def _run():
        try:
            r = genai_client.models.generate_content(
                model=config.GEN_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0),
            )
            return getattr(r, "text", None) or ""
        except Exception as e:
            return f"Gemini error: {e}"

    return await asyncio.to_thread(_run)


async def stream_gemini(genai_client, prompt: str):
    # Stream Gemini text chunks.
    q: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _run_stream():
        try:
            for chunk in genai_client.models.generate_content_stream(
                model=config.GEN_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0),
            ):
                text = getattr(chunk, "text", None) or ""
                if text:
                    loop.call_soon_threadsafe(q.put_nowait, text)
        except Exception as e:
            loop.call_soon_threadsafe(q.put_nowait, f"Error: {type(e).__name__}: {e}")
        finally:
            loop.call_soon_threadsafe(q.put_nowait, None)

    await asyncio.to_thread(_run_stream)

    while True:
        item = await q.get()
        if item is None:
            break
        yield item


async def call_openrouter_model(model_name: str, prompt: str) -> str:
    # Call OpenRouter (non-streaming) with retries.
    url = f"{config.OPENROUTER_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": config.SYSTEM_RULES},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "provider": {"ignore": ["openinference"]},
    }

    async def _attempt():
        async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT_S) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            return resp.json()

    for attempt in range(1, 4):
        try:
            data = await _attempt()
            choice = data.get("choices", [{}])[0].get("message", {}) or {}
            content = choice.get("content") or choice.get("reasoning") or ""
            if content:
                return content
            if "error" in data:
                return f"OpenRouter error ({model_name}): {data.get('error')}"
            return "No content returned from model."
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            text = e.response.text
            if status in (429, 500, 502, 503, 504) and attempt < 3:
                await asyncio.sleep(1.5 * attempt)
                continue
            return f"OpenRouter HTTP {status} ({model_name}): {text}"
        except Exception as e:
            if attempt < 3:
                await asyncio.sleep(1.0 * attempt)
                continue
            return f"OpenRouter error ({model_name}): {e}"


async def stream_openrouter_model(model_name: str, prompt: str):
    # Stream OpenRouter chat completion deltas.
    url = f"{config.OPENROUTER_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    body = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": config.SYSTEM_RULES},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "stream": True,
        "provider": {"ignore": ["openinference"]},
    }

    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT_S) as client:
        async with client.stream("POST", url, headers=headers, json=body) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    payload = json.loads(data)
                except Exception:
                    continue
                delta = payload.get("choices", [{}])[0].get("delta", {}).get("content")
                if delta:
                    yield delta

