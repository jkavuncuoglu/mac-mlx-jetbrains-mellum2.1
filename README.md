# Local Mellum 2.1 Server (Apple Silicon, MLX)

Runs **JetBrains Mellum 2.1 (12B-A2.5B MoE, 6-bit MLX)** locally on an Apple Silicon Mac as a persistent `launchd` service exposing a small FastAPI server on `127.0.0.1:8000`.

## Layout

- `run_mellum.py` — FastAPI/Uvicorn server. Loads the model once and serves it.
- `test_mellum.py` — smoke test against `/generate`.
- `mellum.py` — one-off script that loads the model and prints a completion.
- `launchd/com.user.mellum.plist` — LaunchAgent definition (copy to `~/Library/LaunchAgents/`).
- Weights cache: `~/.cache/huggingface/hub/` (~9.3 GB)
- Logs: `/tmp/mellum.out.log`, `/tmp/mellum.err.log`

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install mlx-lm fastapi uvicorn requests
cp launchd/com.user.mellum.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.mellum.plist
```

Paths in the plist are absolute; edit them if the project lives elsewhere.

## Endpoints

- `GET /health`
- `POST /generate` with `{"prompt": "...", "max_tokens": 400}` returning `{"response": "..."}`

## Operations

```bash
curl http://127.0.0.1:8000/health
tail -f /tmp/mellum.err.log
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.user.mellum.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.mellum.plist
launchctl kickstart -k gui/$(id -u)/com.user.mellum
.venv/bin/python3 test_mellum.py
```

## Notes

MLX GPU streams are thread-local. The model is loaded and all generation runs on a single dedicated worker thread (`gpu_executor` in `run_mellum.py`); running `generate` from FastAPI's default threadpool fails with `There is no Stream(gpu, 1) in current thread`.
