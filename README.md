# Local Mellum 2.1 + EmbeddingGemma 2 Server (Apple Silicon, MLX)

Runs two models locally on an Apple Silicon Mac behind one FastAPI server on `127.0.0.1:8000`:

- **JetBrains Mellum 2.1** (12B-A2.5B MoE, 6-bit MLX) for chat, edit, and apply
- **google/embeddinggemma-2** (768-dim) for codebase indexing

It exposes OpenAI-compatible routes, so any editor or tool that can talk to an OpenAI-style endpoint can use it. See [docs/editor-setup.md](docs/editor-setup.md) for VS Code, JetBrains, and CLI usage (Continue is the recommended client).

Requires an Apple Silicon Mac (MLX is Apple-only) and roughly 12 GB of free unified memory for both models.

## Layout

- `run_mellum.py` — FastAPI/Uvicorn server. Loads both models once and serves them.
- `test_mellum.py` — smoke test against `/generate`.
- `mellum.py` — one-off script that loads Mellum and prints a completion.
- `launchd/com.user.mellum.plist` — optional LaunchAgent for running automatically.
- `docs/editor-setup.md` — how to use the server from editors and CLIs.
- Weights cache: `~/.cache/huggingface/hub/`

## Install

```bash
git clone https://github.com/jkavuncuoglu/jetbrains-mellum2.1.git
cd jetbrains-mellum2.1
python3 -m venv .venv
.venv/bin/pip install mlx-lm fastapi uvicorn requests sentence-transformers torchvision
```

`torchvision` is required even though only text is embedded: the EmbeddingGemma 2 processor imports the Gemma4 image processor, and without it startup fails with `Could not import module 'EmbeddingGemma2Processor'`.

The first start downloads the weights from Hugging Face (about 9 GB for Mellum plus the embedding model). If Hugging Face reports that `google/embeddinggemma-2` is gated, accept the license on its model page and run `hf auth login`.

Tested with `mlx-lm 0.32.0`, `sentence-transformers 6.1.0`, `transformers 5.19.0`, `torch 2.14.1`, `torchvision 0.29.1`.

## Running it

Pick one. Both run the same command; the only difference is who starts and restarts it. Startup takes about 12 seconds once the weights are cached. Do not run both at once: they share port 8000.

### Option A: Manual

Run it in a terminal when you want it, stop it with `Ctrl+C`:

```bash
.venv/bin/python3 run_mellum.py
```

Or in the background:

```bash
nohup .venv/bin/python3 run_mellum.py > /tmp/mellum.log 2>&1 &
```

Stop the background process with `pkill -f run_mellum.py`.

### Option B: Automatic (macOS launchd)

A LaunchAgent starts the server at login, restarts it if it crashes, and keeps the models resident.

1. Edit the three absolute paths in `launchd/com.user.mellum.plist` (the venv Python, the script, and the working directory) to match where you cloned the repo.
2. Install and start it:

```bash
cp launchd/com.user.mellum.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.mellum.plist
```

Manage it:

```bash
launchctl kickstart -k gui/$(id -u)/com.user.mellum
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.user.mellum.plist
launchctl print gui/$(id -u)/com.user.mellum | grep -E "state =|runs ="
tail -f /tmp/mellum.err.log
```

If the server fails at startup, `KeepAlive` restarts it repeatedly (watch `runs =` climb). Read `/tmp/mellum.err.log` for the real error. To slow a crash loop, add `<key>ThrottleInterval</key><integer>30</integer>` to the plist.

### Verify

```bash
curl http://127.0.0.1:8000/health
.venv/bin/python3 test_mellum.py
```

## Endpoints

| Route | Purpose |
| --- | --- |
| `GET /health` | Liveness and loaded model ids |
| `POST /generate` | Raw completion: `{"prompt": "...", "max_tokens": 400}` returns `{"response": "..."}` |
| `POST /embed` | `{"input": "text" \| ["text", ...]}` returns `{"embeddings": [[...]]}` |
| `GET /v1/models` | OpenAI-style model list (`mellum`, `embeddinggemma-2`) |
| `POST /v1/chat/completions` | OpenAI-style chat, with `stream: true` SSE support |
| `POST /v1/embeddings` | OpenAI-style embeddings |

`/v1/chat/completions` applies Mellum's chat template with `enable_thinking=False`, which pre-fills an empty `<think></think>` block. This is the Thinking variant of the model, so on open-ended prompts it can still reason in plain prose; instructions such as "code only" or a system prompt reduce this. `/generate` sends the prompt untemplated. `stop` sequences, tool calls, and a text/FIM completions endpoint are not implemented.

## Notes

MLX GPU streams are thread-local. Mellum is loaded and all generation runs on a single dedicated worker thread (`gpu_executor` in `run_mellum.py`); running `generate` from FastAPI's default threadpool fails with `There is no Stream(gpu, 1) in current thread`. Embedding calls run in FastAPI's threadpool and are unaffected.

The server binds to `127.0.0.1` only and has no authentication. Do not expose it to a network without adding auth.
