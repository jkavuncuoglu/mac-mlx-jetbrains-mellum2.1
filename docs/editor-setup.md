# Using the Local Server from Your Editor

The server speaks the OpenAI API on `http://127.0.0.1:8000/v1`, so anything that supports a custom OpenAI-compatible endpoint can use it. Start the server first (see the README: manual or launchd), then confirm it is up:

```bash
curl http://127.0.0.1:8000/health
```

## Connection details

Use these in any client:

| Setting | Value |
| --- | --- |
| Base URL | `http://127.0.0.1:8000/v1` |
| API key | any non-empty string (for example `local`); it is not checked |
| Chat model name | `mellum` |
| Embedding model name | `embeddinggemma-2` |
| Provider type | "OpenAI" or "OpenAI-compatible" |

## What each model is for

| Job | Use | Why |
| --- | --- | --- |
| Chat, edit, apply | `mellum` | The code-focused chat model |
| Codebase indexing and `@codebase` search | `embeddinggemma-2` | Produces 768-dim embeddings |
| Tab autocomplete | Not this server | The server has no completions/FIM endpoint. Use a small dedicated autocomplete model, for example a Qwen2.5-Coder base model served by Ollama |

Tool calling and `stop` sequences are not implemented. Features that depend on tool calls (some agent modes) will not work against this server.

## Recommended client: Continue

[Continue](https://continue.dev) is open source and the best fit for this setup:

- **Same config everywhere.** One file, `~/.continue/config.yaml`, drives the VS Code extension, the JetBrains plugin, and the Continue CLI. Configure the models once and every editor and terminal uses them.
- **Model roles.** Continue assigns models by role (`chat`, `edit`, `apply`, `autocomplete`, `embed`). That maps directly onto this setup: Mellum for chat/edit/apply, EmbeddingGemma for embeddings, and a separate small model for autocomplete.
- **Local-first.** It talks to any OpenAI-compatible URL and does codebase indexing with whatever `embed` model you give it, so code stays on your machine.
- **A CLI that shares the config.** The Continue CLI gives you the same models and rules in a terminal, useful for scripting and SSH sessions.

### Config

Edit `~/.continue/config.yaml`:

```yaml
name: Local Config
version: 1.0.0
schema: v1
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

  - name: Qwen2.5-Coder 1.5B
    provider: ollama
    model: qwen2.5-coder:1.5b-base
    roles:
      - autocomplete

  - name: EmbeddingGemma 2 (Local)
    provider: openai
    model: embeddinggemma-2
    apiBase: http://127.0.0.1:8000/v1
    apiKey: local
    roles:
      - embed
```

Notes:

- The key is `apiBase` (camelCase). `api_base` is ignored.
- `provider: openai` with a custom `apiBase` is how Continue talks to any OpenAI-compatible server. There is no separate provider for this server.
- The autocomplete model above is optional and runs on Ollama (`ollama pull qwen2.5-coder:1.5b-base`). Swap in any model you prefer, or drop the entry to disable autocomplete.
- After changing the `embed` model, Continue has to reindex your codebases. Old vectors from a different embedding model are not compatible.

### JetBrains (IntelliJ, PhpStorm, WebStorm, PyCharm, and others)

1. Install the **Continue** plugin, then restart the IDE. Either:
   - **From the IDE:** Settings > Plugins > Marketplace, search for "Continue". It may not show up in the in-app search for every IDE or version; if you cannot find it, use the next option.
   - **From disk:** open the [Continue plugin page on the JetBrains Marketplace](https://plugins.jetbrains.com/plugin/22707-continue), download the plugin file for your IDE version from the Versions tab, then in the IDE go to Settings > Plugins > gear icon > **Install Plugin from Disk...** and select the downloaded `.zip`.
2. Edit `~/.continue/config.yaml` as above. The plugin reloads it automatically; use the gear icon in the Continue panel to open it.
3. Pick **Mellum 2.1 (Local)** in the model dropdown in the Continue panel.
4. Use chat in the side panel, or select code and use the edit shortcut to rewrite it in place.

### VS Code

1. Install the **Continue** extension. Any one of:
   - **From the editor:** open the Extensions view (`Cmd+Shift+X` on macOS, `Ctrl+Shift+X` elsewhere), search for "Continue", and install the one published by Continue.
   - **From the command line:** `code --install-extension Continue.continue`. The `code` command is available after running "Shell Command: Install 'code' command in PATH" from the Command Palette.
   - **From the web:** the [Continue extension on the Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=Continue.continue) has an Install button that opens VS Code. If you use VSCodium or another editor that cannot reach Microsoft's marketplace, install it from [Open VSX](https://open-vsx.org/extension/Continue/continue).
   - **From a file:** download the `.vsix` from either page, then in the Extensions view use the `...` menu > **Install from VSIX...**.
2. Open the Continue panel from its icon in the sidebar. Continue's default placement is the left side; dragging it to the secondary (right) sidebar keeps it next to your editor.
3. Edit the same `~/.continue/config.yaml` as above. In the panel, the gear icon opens it, and it reloads when you save.
4. Pick **Mellum 2.1 (Local)** in the model dropdown. Chat from the side panel, or select code and use the edit shortcut (`Cmd+I` on macOS, `Ctrl+I` elsewhere) to rewrite it in place.

If other chat models (for example an Ollama model) are also in the config, make sure the dropdown is on Mellum, otherwise requests go to the other model and never reach this server.

### Continue CLI

The Continue CLI reads the same config, so the models above work in a terminal session with no extra setup. Install it by following Continue's current CLI instructions (it is distributed through npm), run it from a project directory, and select the Mellum model if it is not the default. Because tool calling is not implemented in this server, workflows that rely on the CLI executing tools through the model will be limited; plain chat and edit-style prompts work.

## Other clients

Any tool with a custom OpenAI endpoint works for chat. Set the base URL, API key, and model name from the table above. Examples:

- **VS Code extensions** such as Cline, Roo Code, or Kilo: choose the "OpenAI Compatible" provider and enter the values above. These lean heavily on tool calling, so expect limited agent behavior.
- **Aider:** `aider --openai-api-base http://127.0.0.1:8000/v1 --openai-api-key local --model openai/mellum`
- **Open WebUI and similar chat front ends:** add an OpenAI-compatible connection with the base URL above.
- **Zed and other editors with OpenAI-compatible settings:** add a custom OpenAI provider pointing at the base URL.
- **Hosted-first editors** that route requests through their own servers cannot reach `127.0.0.1` on your machine. Use a client that connects from your own computer.

For raw scripting, call the endpoints directly:

```bash
curl http://127.0.0.1:8000/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"mellum","messages":[{"role":"user","content":"Write a PHP function that adds two numbers."}],"max_tokens":200}'
```

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| Connection refused | Server is not running. Start it (README) and check `curl http://127.0.0.1:8000/health` |
| Continue shows "No models configured" | The config failed validation. Check that the top level has `name`, `version`, and `schema: v1` (`name`, not `config_name`) and that each model has `provider`, `model`, and `roles`. Then click the reload icon in the Continue panel |
| Works in one editor, not another | Check that both read the same `~/.continue/config.yaml` and that the model dropdown is on Mellum |
| 404 on a request | The client is using a path the server does not have, such as `/v1/completions`. Only the routes in the README are implemented |
| First request is slow | Models load at server startup (about 12 seconds). After that responses are fast; a long delay means the server is still starting |
| Reply starts with reasoning like "We need to respond with..." | Mellum is a Thinking model and may reason in prose even with thinking disabled. Add a system prompt or rule (Continue supports rules) such as "Respond with code only, no explanation" |
| Output looks truncated | Raise `max_tokens` in the client; the server defaults to 2048 when none is sent |
| Embeddings are not used for search | Confirm an `embed`-role model is set, then force a reindex in Continue |
