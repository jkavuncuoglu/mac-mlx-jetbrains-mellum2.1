import asyncio
from concurrent.futures import ThreadPoolExecutor

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from mlx_lm import load, generate

MODEL_ID = "mlx-community/Mellum2.1-12B-A2.5B-Thinking-6bit"

gpu_executor = ThreadPoolExecutor(max_workers=1)

app = FastAPI(title="Mellum 2.1 Local Server")

print("🚀 Loading Mellum 2.1 onto M4 GPU cores...")
model, tokenizer = gpu_executor.submit(load, MODEL_ID).result()
print("✨ Model loaded and ready on port 8000!")

class ChatRequest(BaseModel):
    prompt: str
    max_tokens: int = 400

def run_generation(prompt: str, max_tokens: int) -> str:
    return generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=max_tokens,
        verbose=False
    )

@app.get("/health")
def health_check():
    return {"status": "healthy", "model": MODEL_ID}

@app.post("/generate")
async def ask_mellum(request: ChatRequest):
    response = await asyncio.get_running_loop().run_in_executor(
        gpu_executor,
        run_generation,
        request.prompt,
        request.max_tokens,
    )
    return {"response": response}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
