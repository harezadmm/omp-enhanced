# Run G0DM0D3 with local models

G0DM0D3 can use any local server that implements the OpenAI-compatible
`/v1/models` and `/v1/chat/completions` endpoints. The local transport is
restricted to `localhost`, `127.0.0.1`, and `::1`.

## Quick start with Ollama

1. Install Ollama and pull one or more models:

   ```bash
   ollama pull qwen3:8b
   ollama serve
   ```

2. In G0DM0D3, open **Settings → API Keys → Local Models**.
3. Enter `http://localhost:11434/v1` as the base URL.
4. Click **Test & Discover Models**.
5. Enable **Local-only mode** to block OpenRouter and Venice model calls and
   disable G0DM0D3 app telemetry.

When using the hosted `https://godmod3.ai` page, Ollama must allow that browser
origin. Start Ollama with an origin configuration that includes
`https://godmod3.ai`, then restart the server. If you do not want to expose a
local endpoint to a hosted page, serve G0DM0D3 locally as described below.

## Quick start with LM Studio

1. Load a model in LM Studio.
2. Open the Developer tab and start the local server.
3. Enable browser/CORS access for the origin from which G0DM0D3 is loaded.
4. Use `http://localhost:1234/v1` in G0DM0D3 and click
   **Test & Discover Models**.

## Run the interface locally

From the repository root:

```bash
python3 -m http.server 8080
```

Open `http://localhost:8080`, configure the local model endpoint, and enable
**Local-only mode**. In this mode G0DM0D3:

- excludes OpenRouter and Venice from every ULTRAPLINIAN race;
- disables metadata telemetry and clears pending telemetry events;
- uses local models for query classification, TASTEMAKER judging, refusal
  checks, the Pliny coaching pass, accuracy checks, and Liquid refinement;
- keeps conversations, settings, and keys in browser storage.

On the hosted `godmod3.ai` page, Local-only mode does not stop normal webpage,
font, hosting, or browser-origin traffic. Self-hosting `index.html` and using
Local-only mode provides the strongest local boundary. Your local inference
server may also keep its own logs; consult its configuration.

Multiple comma-separated model IDs can race together. Local-only mode uses the
first configured model for helper/judge calls, so place the strongest local
judge first. Image analysis works only when that model accepts OpenAI-compatible
image message parts.

## Troubleshooting

- **Connection failed / Failed to fetch:** start the local server and enable
  CORS for the page origin (`https://godmod3.ai` or your local web origin).
- **No models returned:** confirm `GET <base-url>/models` returns OpenAI-style
  `{ "data": [{ "id": "..." }] }` JSON.
- **Responses are slow:** configure one model instead of several, disable
  coaching or Liquid refinement, or lower Max Tokens in Settings.
- **Model rejects a parameter:** update the local server or use its
  OpenAI-compatibility mode. G0DM0D3 sends standard chat-completion fields and
  omits cloud-specific reasoning controls for local requests.
