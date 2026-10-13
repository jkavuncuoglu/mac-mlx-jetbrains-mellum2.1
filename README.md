# Local Mellum 2.1 + EmbeddingGemma 2 Server (Apple Silicon, MLX)

Runs two models locally on an Apple Silicon Mac as a persistent `launchd` service behind one FastAPI server on `127.0.0.1:8000`:

- **JetBrains Mellum 2.1** (12B-A2.5B MoE, 6-bit MLX) for chat, edit, and apply
- **google/embeddinggemma-2** (768-dim) for codebase indexing

It exposes OpenAI-compatible routes so editors such as [Continue](https://continue.dev) can use it directly.

## Layout

- `run_mellum.py` — FastAPI/Uvicorn server. Loads both models once and serves them.
- `test_mellum.py` — smoke test against `/generate`.
- `mellum.py` — one-off script that loads Mellum and prints a completion.
- `launchd/com.user.mellum.plist` — LaunchAgent definition (copy to `~/Library/LaunchAgents/`).
- Weights cache: `~/.cache/huggingface/hub/`
- Logs: `/tmp/mellum.out.log`, `/tmp/mellum.err.log`

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install mlx-lm fastapi uvicorn requests sentence-transformers torchvision
cp launchd/com.user.mellum.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.mellum.plist
```

`torchvision` is required even though only text is embedded: the EmbeddingGemma 2 processor imports the Gemma4 image processor, and without it startup fails with `Could not import module 'EmbeddingGemma2Processor'`, which makes `KeepAlive` restart the service in a loop.

Paths in the plist are absolute; edit them if the project lives elsewhere. Tested with `mlx-lm 0.32.0`, `sentence-transformers 6.1.0`, `transformers 5.19.0`, `torch 2.14.1`, `torchvision 0.29.1`.

## Endpoints

| Route | Purpose |
| --- | --- |
| `GET /health` | Liveness and loaded model ids |
| `POST /generate` | Raw completion: `{"prompt": "...", "max_tokens": 400}` returns `{"response": "..."}` |
| `POST /embed` | `{"input": "text" \| ["text", ...]}` returns `{"embeddings": [[...]]}` |
| `GET /v1/models` | OpenAI-style model list (`mellum`, `embeddinggemma-2`) |
| `POST /v1/chat/completions` | OpenAI-style chat, with `stream: true` SSE support |
| `POST /v1/embeddings` | OpenAI-style embeddings |

`/v1/chat/completions` applies Mellum's chat template with `enable_thinking=False`, so no `<think>` blocks appear in the output. `/generate` sends the prompt untemplated. `stop` sequences and tool calls are not implemented.

## Continue (`~/.continue/config.yaml`)

```yaml
models:
  - name: Mellum 2.1 (Local)
    provider: openai
    model: mellum
    apiBase: http://127.0.0.1:8000/v1
    apiKey: local
    roles:
      - chat
      - edit
      - apply

  - name: EmbeddingGemma 2 (Local)
    provider: openai
    model: embeddinggemma-2
    apiBase: http://127.0.0.1:8000/v1
    apiKey: local
    roles:
      - embed
```

Switching embedding models requires Continue to reindex your codebases.

## Operations

```bash
curl http://127.0.0.1:8000/health
tail -f /tmp/mellum.err.log
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.user.mellum.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.mellum.plist
launchctl kickstart -k gui/$(id -u)/com.user.mellum
.venv/bin/python3 test_mellum.py
```

Startup takes about 12 seconds while both models load.

## Notes

MLX GPU streams are thread-local. Mellum is loaded and all generation runs on a single dedicated worker thread (`gpu_executor` in `run_mellum.py`); running `generate` from FastAPI's default threadpool fails with `There is no Stream(gpu, 1) in current thread`. Embedding calls run in FastAPI's threadpool and are unaffected.
