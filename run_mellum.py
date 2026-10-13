import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, List, Optional, Union
from mlx_lm import load, generate, stream_generate
from mlx_lm.sample_utils import make_sampler
from sentence_transformers import SentenceTransformer

app = FastAPI(title="Local M4 Dual Model Server")

# --- 1. Load Mellum 2.1 (Chat/Edit) ---
print("🚀 Loading Mellum 2.1 onto M4 GPU cores...")
MELLUM_ID = "mlx-community/Mellum2.1-12B-A2.5B-Thinking-6bit"
gpu_executor = ThreadPoolExecutor(max_workers=1)
mellum_model, mellum_tokenizer = gpu_executor.submit(load, MELLUM_ID).result()

# --- 2. Load EmbeddingGemma2 (Codebase Indexing) ---
print("🛰️ Loading EmbeddingGemma2 into Unified Memory...")
EMBED_ID = "google/embeddinggemma-2"
# Loads the 740M model natively; sentence-transformers taps straight into Apple Silicon torch acceleration
embed_model = SentenceTransformer(EMBED_ID)

print("✨ All models preloaded and active on port 8000!")

# Pydantic Schemas
class ChatRequest(BaseModel):
    prompt: str
    max_tokens: int = 400

class EmbedRequest(BaseModel):
    input: Union[str, List[str]]

@app.get("/health")
def health_check():
    return {"status": "healthy", "chat_model": MELLUM_ID, "embed_model": EMBED_ID}

# Chat Route (Continue Chat, Edit, Apply)
def run_generation(prompt: str, max_tokens: int) -> str:
    return generate(
        mellum_model,
        mellum_tokenizer,
        prompt=prompt,
        max_tokens=max_tokens,
        verbose=False
    )

@app.post("/generate")
async def ask_mellum(request: ChatRequest):
    response = await asyncio.get_running_loop().run_in_executor(
        gpu_executor,
        run_generation,
        request.prompt,
        request.max_tokens,
    )
    return {"response": response}

# Embedding Route (Continue Codebase Indexing)
@app.post("/embed")
def embed_text(request: EmbedRequest):
    texts = [request.input] if isinstance(request.input, str) else request.input
    # Generate 768-dimensional normalized vectors
    embeddings = embed_model.encode(texts)
    
    return {"embeddings": embeddings.tolist()}

class ChatCompletionRequest(BaseModel):
    messages: List[dict]
    model: str = "mellum"
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: bool = False

class EmbeddingsRequest(BaseModel):
    input: Union[str, List[str]]
    model: str = "embeddinggemma-2"

def flatten_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content

    return "".join(
        part.get("text", "")
        for part in content or []
        if isinstance(part, dict)
    )

def build_chat_prompt(messages: List[dict]) -> str:
    normalized = [
        {"role": message["role"], "content": flatten_message_content(message.get("content"))}
        for message in messages
    ]

    return mellum_tokenizer.apply_chat_template(
        normalized,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )

def build_sampler(request: ChatCompletionRequest):
    if request.temperature is None:
        return None

    return make_sampler(temp=request.temperature)

def run_chat_generation(request: ChatCompletionRequest) -> str:
    return generate(
        mellum_model,
        mellum_tokenizer,
        prompt=build_chat_prompt(request.messages),
        max_tokens=request.max_tokens or 2048,
        sampler=build_sampler(request),
        verbose=False
    )

def produce_chat_chunks(request: ChatCompletionRequest, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> None:
    try:
        for chunk in stream_generate(
            mellum_model,
            mellum_tokenizer,
            prompt=build_chat_prompt(request.messages),
            max_tokens=request.max_tokens or 2048,
            sampler=build_sampler(request),
        ):
            loop.call_soon_threadsafe(queue.put_nowait, chunk.text)
    finally:
        loop.call_soon_threadsafe(queue.put_nowait, None)

def format_sse_chunk(completion_id: str, model: str, delta: dict, finish_reason: Optional[str]) -> str:
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }

    return f"data: {json.dumps(payload)}\n\n"

async def stream_chat_completion(request: ChatCompletionRequest):
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    loop.run_in_executor(gpu_executor, produce_chat_chunks, request, loop, queue)

    yield format_sse_chunk(completion_id, request.model, {"role": "assistant"}, None)

    while True:
        text = await queue.get()

        if text is None:
            break

        yield format_sse_chunk(completion_id, request.model, {"content": text}, None)

    yield format_sse_chunk(completion_id, request.model, {}, "stop")
    yield "data: [DONE]\n\n"

@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "mellum", "object": "model", "owned_by": "local"},
            {"id": "embeddinggemma-2", "object": "model", "owned_by": "local"},
        ],
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if request.stream:
        return StreamingResponse(stream_chat_completion(request), media_type="text/event-stream")

    text = await asyncio.get_running_loop().run_in_executor(gpu_executor, run_chat_generation, request)

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
    }

@app.post("/v1/embeddings")
def create_embeddings(request: EmbeddingsRequest):
    texts = [request.input] if isinstance(request.input, str) else request.input
    vectors = embed_model.encode(texts).tolist()

    return {
        "object": "list",
        "model": request.model,
        "data": [
            {"object": "embedding", "index": index, "embedding": vector}
            for index, vector in enumerate(vectors)
        ],
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
