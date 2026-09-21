# G0DM0D3 -- Terms of Service

**Last updated:** 2026-07-15

---

## 1. Acceptance

By using G0DM0D3 -- whether through the web frontend, the API server, or a self-hosted deployment -- you agree to these terms. If you do not agree, do not use the software.

---

## 2. What G0DM0D3 Is

G0DM0D3 is an open-source research tool for AI safety, red teaming, and cognition research. It is provided **as-is** for experimentation and study. It is not a commercial product, and there is no company behind it -- just an open-source project and its contributors.

---

## 3. Data Collection

This is the section that matters most. Read it carefully.

G0DM0D3 has **three distinct data paths**. Tiers 1 and 2 are structural metadata paths; their event schemas do not intentionally contain prompt text, response text, images, or API keys. Tier 3 is an API-server-only, per-request opt-in path that stores conversation content. Network infrastructure and model providers necessarily process request data separately from these G0DM0D3 data paths.

### Overview

| | Tier 1: ZDR Metadata | Tier 2: Telemetry Beacon | Tier 3: Dataset Collection |
|---|---|---|---|
| **Where it runs** | API server | Web frontend (browser) | API server |
| **Default state** | On for API requests | On by default in the standalone web app; opt out with No-Log or Local-only mode | **Off -- per-request opt-in only** |
| **Collects message content?** | Never | Never | **Yes, when you opt in** |
| **Direct identifiers in stored records?** | No dedicated fields | No dedicated fields; request IP is temporarily used for rate limiting but not published by G0DM0D3 | Conversation content may contain any information the caller supplies |
| **Collects API keys as fields?** | No | No | No, but a key pasted into opted-in conversation content would be stored as content |
| **Source code** | `api/lib/metadata.ts` | `index.html`, `src/lib/telemetry.ts`, `functions/api/telemetry.ts` | `api/lib/dataset.ts` |

---

### Tier 1: ZDR Metadata Tracker (Always On -- API Server)

This runs on every API request. It records how the system performed, not what you said.

#### What IS collected

| Data Point | Description |
|---|---|
| Timestamp | When the request happened |
| Endpoint | Which API endpoint was called |
| Mode | Standard or ULTRAPLINIAN |
| Tier | Fast, standard, or full (ULTRAPLINIAN only) |
| Stream | Whether streaming was used |
| Pipeline flags | Whether godmode, autotune, parseltongue, and STM were enabled |
| STM modules | Which STM modules were active |
| Strategy | Which routing strategy was used |
| AutoTune context | Detected context type (code/creative/analytical/conversational/chaotic) and confidence score |
| Models queried | How many models were queried (count only) |
| Per-model results | Model name, score, duration in ms, success/failure, content length (character count only), categorized error type |
| Winner metadata | Winning model name, score, duration, content length (character count) |
| Total duration | End-to-end request time in ms |
| Response length | Character count of the response (not the response itself) |
| Liquid Response metadata | Number of leader changes, time to first response |
| Error types | Categorized as: `timeout`, `rate_limit`, `auth`, `empty`, `early_exit`, `model_error`, or `unknown` |

#### What the Tier 1 record does not include

| Excluded Data | Why |
|---|---|
| Message content | Your prompts and conversations are yours |
| System prompts | Never recorded |
| Response text | Only the character count, never the actual content |
| API keys or auth tokens | The metadata tracker does not copy these into its records |
| IP addresses | The Tier 1 metadata schema does not record them |
| Dedicated PII fields | The Tier 1 schema contains operational fields, not identity fields |
| Raw error messages | Only categorized error types (e.g., "timeout"), never the actual error text |

**Storage:** In-memory ring buffer (50,000 events max). When the buffer reaches 80% capacity, it auto-publishes to HuggingFace as JSONL and clears. Oldest events are evicted if the buffer fills up.

---

### Tier 2: Client-Side Telemetry Beacon (Default On -- Standalone Web Frontend)

This runs in your browser after LLM requests and sends structural metadata to a Cloudflare Pages Function. The standalone `index.html` enables it by default. **Settings → General → No-Log Mode** and **Local-only mode** both stop new app telemetry and clear the pending browser buffer. These settings do not control provider-side or hosting logs.

The Cloudflare function keeps only an allowlist of top-level fields before committing data to Hugging Face. This reduces accidental field leakage, but it is not a recursive PII detector and does not justify a guarantee that arbitrary metadata values can never identify someone.

#### What IS collected

| Data Point | Description |
|---|---|
| Event type | Type of event (e.g., `chat_completion`) |
| Timestamp | When the event occurred |
| Session ID | A random, ephemeral ID generated for the page session -- not derived from an account |
| Mode and tier | Standard, GODMODE CLASSIC, Parseltongue, or ULTRAPLINIAN configuration |
| Model data | Model names, counts, scores, winners, and categorized failures |
| Duration | Request time in ms |
| Content lengths | Prompt/response character counts, not text |
| Success/failure | Whether the request succeeded |
| Pipeline config | Autotune on/off, parseltongue on/off, STM modules, strategy, godmode on/off |
| AutoTune metadata | Detected context type and confidence score |
| Parseltongue metadata | Number of triggers found (count only, not the trigger words), technique, intensity |
| ULTRAPLINIAN metadata | Tier, models queried count, models succeeded count, winner model, winner score, total duration |
| Structural context | Conversation depth, persona identifier, image-present boolean, and memory count when supplied |
| Classification | Harm-taxonomy category, subcategory, confidence, intent label, and flags -- not the prompt text |

To produce the classification label, the standalone app sends the raw prompt in a separate auxiliary-model request through the configured OpenRouter or local provider. Only the label is included in telemetry. No-Log and Local-only mode skip that auxiliary classifier.

#### What the stored Tier 2 telemetry record does not include

| Excluded Data | Why |
|---|---|
| Message content | Never sent to the telemetry endpoint |
| Prompts or responses | Not included in telemetry events |
| API keys or tokens | Not included in telemetry events; provider credentials are sent separately to the selected provider or local endpoint |
| Images | Not included; only an image-present boolean may be included |
| Request IP in published JSONL | The Cloudflare function reads the IP for an in-memory rate limit but does not add it to the telemetry record |

**Storage:** In the standalone `index.html`, events are batched in browser memory and flushed every five minutes, at 50 events, or on page unload. The optional React implementation under `src/` uses 30 seconds or 20 events. The Cloudflare endpoint prefers a KV buffer and falls back to isolate memory when KV is not bound; isolate eviction can lose unflushed fallback data. When publishing is configured, batches are committed as JSONL to Hugging Face. Telemetry is fire-and-forget and does not block the chat UI.

The optional React frontend currently starts its telemetry implementation when the app starts; its `noLogMode` store setting is not wired into `src/lib/telemetry.ts`. When an OpenRouter key is present, that frontend also sends the raw prompt to OpenRouter for classification. Deployers who use the alternative frontend must wire their own opt-out and classifier guard if they need parity with the standalone app.

---

### Tier 3: Opt-In Dataset Collection (Only When You Explicitly Enable It)

> **WARNING: This tier collects your full conversation content (prompts and responses) and publishes it to a PUBLIC HuggingFace dataset that anyone can download, redistribute, and use for any purpose. Only enable this if you understand and accept this.**

This tier **only activates** when an API caller sets `contribute_to_dataset: true` in a request to the optional Node/Express API server. The standalone godmod3.ai `index.html` does not expose or send this flag. The similarly named preference in the optional React settings is stored locally but is not currently wired into API requests.

#### What IS collected (only when opted in)

| Data Point | Description |
|---|---|
| Messages sent and received | **Actual conversation content** -- your prompts and the model's responses. **This data is PUBLIC.** |
| Model and endpoint | Which model and API endpoint were used |
| Mode | Standard or ULTRAPLINIAN |
| AutoTune details | Strategy, detected context, confidence, full parameter set, reasoning |
| Parseltongue details | Trigger words found (the actual words, not just a count), technique used, transformation count |
| STM details | Which modules were applied |
| ULTRAPLINIAN details | Tier, full list of models queried, winner model, all scores/durations, total duration |
| Feedback | User ratings (thumbs up/down) and heuristics (response length, repetition score, vocabulary diversity) |

#### No automatic PII scrubbing

The current dataset path does **not** run an automatic PII scrubber. It removes system-role messages, but user and assistant content is otherwise stored as supplied. If opted-in content contains names, email addresses, phone numbers, credentials, health data, financial data, or other identifying information, that information can be published verbatim.

#### What you should NEVER include when Dataset Mode is on

- Real names (yours or anyone else's)
- Physical addresses or location data
- Passwords, private keys, or credentials
- Financial account numbers
- Medical records or health information
- Any information that could identify a real person

#### What is not automatically copied into Tier 3 records

| Excluded Data | Why |
|---|---|
| API/auth fields | Request authentication fields are not copied into the dataset record; credentials pasted into conversation content are not detected or removed |
| Request IP address | Not added to the Tier 3 dataset record by G0DM0D3 |
| System prompts | Excluded to prevent leaking custom prompt configurations |

**Storage:** In-memory buffer (10,000 entries max, FIFO eviction). Auto-publishes to HuggingFace when buffer reaches 80% capacity.

**Deletion:** You can delete your contributed entries at any time via `DELETE /v1/dataset/:id` while data remains in the server's memory buffer. **Once data has been published to HuggingFace, it is public and may be cached, forked, or redistributed by third parties.** Post-publication deletion requests must be directed to the HuggingFace repository maintainers, and full removal cannot be guaranteed.

---

## 4. Data Storage and Publishing

### Buffers before publishing

- Tier 1 API metadata and Tier 3 opted-in dataset entries use in-memory buffers in the optional API server. Unpublished records can be lost on restart or eviction.
- Tier 2 starts in browser memory. The Cloudflare Function then uses a `TELEMETRY_KV` binding when available; otherwise it uses best-effort isolate memory. KV batch keys have a seven-day expiration and are deleted after a successful flush.
- A static-only deployment without `/api/telemetry` does not publish Tier 2 events; failed telemetry delivery does not stop the app.

### HuggingFace Publishing

When configured (via `HF_TOKEN` and `HF_DATASET_REPO` environment variables), G0DM0D3 auto-publishes collected data to a HuggingFace dataset repository.

| Detail | Value |
|---|---|
| Default repository | `pliny-the-prompter/g0dm0d3` |
| File format | JSONL (JSON Lines) |
| API metadata path | `metadata/batch_<timestamp>.jsonl` |
| API opt-in dataset path | `dataset/batch_<timestamp>.jsonl` |
| Standalone frontend telemetry path | `incoming_v2/YYYY/MM/DD/flush_<digest>.jsonl` (KV) or `membuf_<digest>.jsonl` (memory fallback) |
| API-server flush triggers | Buffer at 80% capacity, periodic timer (default 30 minutes), or graceful server shutdown |
| Cloudflare telemetry flush triggers | KV: 50 pending batches or oldest older than 30 minutes; memory fallback: 50 batches, 256 KiB, or 15 minutes |

Published data on HuggingFace is public and persistent. Once data is published to HuggingFace, it is governed by HuggingFace's terms and policies.

Self-hosted deployments can disable Hugging Face publishing by not setting `HF_TOKEN` and `HF_DATASET_REPO`. The Cloudflare telemetry endpoint rejects events when those variables are absent. The optional API server keeps its own unpublished buffers in memory when publishing is disabled.

### Data Retention

- **Browser/isolate memory:** Data is retained until flushed, discarded, or lost when the page/process/isolate ends.
- **Cloudflare KV:** Pending telemetry batch keys expire after seven days and are normally deleted after a successful Hugging Face flush.
- **API-server memory:** Tier 1 and Tier 3 data remains until flushed or evicted under the buffer policy.
- **HuggingFace:** Published data persists in the HuggingFace repository indefinitely unless manually removed by the repository maintainers.

### Deletion Rights

- **Tier 3 (opt-in dataset):** You can request deletion of individual entries via `DELETE /v1/dataset/:id` while the data is still in the server's memory buffer. Once data has been published to HuggingFace, deletion requests must be directed to the HuggingFace repository maintainers.
- **Tiers 1 and 2 (metadata/telemetry):** There is no individual deletion endpoint. Records use structural fields and, for Tier 2, an ephemeral session ID; they are not guaranteed to be impossible to re-identify when combined with outside information.

---

## 5. API Keys, Credentials, and Chat History

In the standalone browser app, OpenRouter, Venice, and local-server credentials are stored in browser storage and sent to the corresponding configured endpoint as part of model requests. They are not included in the G0DM0D3 app telemetry event schema. Browser storage is not a secure secret vault; anyone with access to your browser profile or injected script running on the page may be able to access locally stored application state.

The optional Node/Express API server is a different deployment surface: if it is not configured with a server-side OpenRouter key, callers can supply `openrouter_api_key` in the request body and the API server necessarily receives it to make the upstream request. The metadata and opt-in dataset record builders do not intentionally copy that field.

You are responsible for keeping your API keys secure. Do not share them publicly.

### Chat History Self-Custody

The standalone app's persistent conversation history is stored in browser `localStorage`. G0DM0D3 has no account system or cloud history sync. Active prompts and context are still transmitted to whichever model provider or local server you select so that it can generate a response.

**This means:**

- Clearing your browser data **permanently deletes** your chat history. There is no recovery mechanism.
- Your history does not transfer between browsers, devices, or browser profiles.
- Private/incognito browsing sessions discard all data when the window closes.
- The app retains at most 100 conversations and caps each conversation at 500 messages; browser storage quotas also apply.

**G0DM0D3 cannot recover lost conversations.** The project does not keep a server-side history backup. You are responsible for backing up conversations you wish to keep; the standalone app includes export/import controls under Settings → Data.

---

## 6. Enterprise Use

### Who This Applies To

This section applies to **Enterprise Users** -- defined as any for-profit entity (or its subsidiaries, affiliates, or contractors acting on its behalf) that meets **any** of the following criteria:

- Annual gross revenue exceeding **$10 million USD**
- More than **100 employees** (full-time, part-time, or contracted)
- Is publicly traded on any stock exchange
- Is a subsidiary, division, or affiliate of an entity that meets any of the above criteria

If you're an individual, a researcher, a student, a hobbyist, a small team, a nonprofit, an educational institution, a government research lab, or a company that doesn't meet the thresholds above -- **this section does not apply to you. G0DM0D3 is free for you. Full stop.**

### What Enterprise Users Must Do

Enterprise Users that use the G0DM0D3 hosted service (the API server, the web frontend hosted by the project, or any project-operated infrastructure) in any capacity -- including internal tools, employee-facing products, customer-facing products, evaluation, benchmarking, or integration -- must obtain a **Commercial Use License** from the G0DM0D3 maintainers.

This applies to:

- **Direct use** of the hosted service or API
- **Embedding** the hosted service into enterprise products, platforms, or workflows
- **Using data collected via the hosted service** (Tier 1, 2, or 3) for commercial purposes such as model training, product development, competitive analysis, or internal research that feeds into commercial products

### What Enterprise Users Get

A Commercial Use License includes:

- Authorized use of the hosted G0DM0D3 service for enterprise purposes
- Priority support channel
- SLA guarantees (negotiated per agreement)
- Custom data handling and retention terms (if needed)
- Exemption from the default data publishing pipeline (Tiers 1 and 2) if contractually agreed

### What This Does NOT Apply To

To be absolutely clear, the following uses are **always free, for everyone, including enterprises**:

- **Self-hosting G0DM0D3 from source code** under the AGPL-3.0 license. The source code license is separate from these service terms. If you clone the repo, run it on your own servers, and comply with the AGPL-3.0 (keep your derivative works open source), you owe nothing.
- **Contributing to the project** via pull requests, issues, documentation, or community support.
- **Academic or nonprofit research** using the hosted service, regardless of institutional size.
- **Personal use** by employees of enterprise entities acting in their individual capacity, on their own time, with their own API keys.

### Pricing

Pricing for Commercial Use Licenses is negotiated on a case-by-case basis. Enterprise Users should contact the maintainers to discuss terms.

### Enforcement

Enterprise Users accessing the hosted service without a Commercial Use License are in violation of these terms. The maintainers reserve the right to:

- Revoke access to the hosted service
- Pursue reasonable compensation for unauthorized commercial use
- Publicly disclose violations (after a 30-day private notice and cure period)

We're not looking to sue anybody. We'd rather have a conversation. But if a billion-dollar company is extracting value from this project and contributing nothing back -- neither code, nor funding, nor even acknowledgment -- that's not the spirit of open source. This clause exists to keep things fair.

### Data Licensing for Enterprise

Enterprise Users that access the publicly published research dataset (on HuggingFace) for commercial purposes -- including model training, fine-tuning, product development, or competitive intelligence -- must obtain a **Data Use License** from the G0DM0D3 maintainers.

Non-commercial research use of the published dataset is always free.

---

## 7. Your Responsibilities

By using G0DM0D3, you agree that:

- **You are responsible for the outputs generated through this tool.** G0DM0D3 is a research interface -- it does not generate content itself, it routes requests to AI models via third-party APIs.
- **You will comply with all applicable laws and regulations** in your jurisdiction when using this tool.
- **You will comply with the terms of service of the underlying AI providers** (e.g., OpenRouter, and the model providers accessible through it).
- **You will not use G0DM0D3 to generate content that is illegal** in your jurisdiction.
- **If you opt in to dataset contribution (Tier 3), you accept that your conversation data will be published publicly** as part of an open research dataset.

---

## 8. No Warranty / Disclaimer

G0DM0D3 IS PROVIDED "AS-IS" WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.

The maintainers and contributors of G0DM0D3:

- Make no guarantees about uptime, availability, or correctness.
- Are not liable for any damages arising from the use of this software.
- Are not responsible for the content generated by third-party AI models accessed through this tool.
- Are not responsible for any costs incurred through third-party API usage (e.g., OpenRouter charges).

Use this tool at your own risk.

---

## 9. Third-Party Services

G0DM0D3 interacts with third-party services. Your use of these services is governed by their respective terms:

| Service | Role | Their Terms |
|---|---|---|
| **OpenRouter** | Routes requests to AI models | [openrouter.ai/terms](https://openrouter.ai/terms) |
| **Venice** | Provides AI models when configured by the user | [venice.ai/legal/tos](https://venice.ai/legal/tos) |
| **HuggingFace** | Hosts published metadata and dataset files | [huggingface.co/terms-of-service](https://huggingface.co/terms-of-service) |
| **Cloudflare Pages** | Hosts the web frontend and telemetry proxy | [cloudflare.com/terms](https://www.cloudflare.com/terms/) |

G0DM0D3 is not affiliated with, endorsed by, or sponsored by any of these services.

---

## 10. Open Source

G0DM0D3 is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

The entire source code is available for inspection. Every claim made in this document can be verified by reading the code:

- Tier 1 metadata: `api/lib/metadata.ts`
- Standalone Tier 2 event creation: `index.html`
- React Tier 2 event creation: `src/lib/telemetry.ts`
- Tier 2 proxy, field allowlist, rate limiting, and publishing: `functions/api/telemetry.ts`
- Tier 3 dataset: `api/lib/dataset.ts`
- HuggingFace publishing: `api/lib/hf-publisher.ts`

You do not need to trust this document. Read the code.

---

## 11. Changes to These Terms

These terms may be updated as the project evolves. Changes will be committed to the repository and visible in the git history. There is no email notification system -- if you use G0DM0D3, check this file periodically.

The "Last updated" date at the top of this document reflects the most recent revision.

---

## 12. Contact

This is an open-source project. The best way to reach the maintainers is through the project's GitHub repository:

- **Questions or concerns:** Open a GitHub issue.
- **Data deletion requests:** Open a GitHub issue or use the `DELETE /v1/dataset/:id` API endpoint for Tier 3 data.
- **Enterprise licensing inquiries:** Open a GitHub issue tagged `enterprise` or contact the maintainers directly.
- **Security issues:** See [SECURITY.md](SECURITY.md) for responsible disclosure. Do NOT open public issues for vulnerabilities.

---

*These terms exist to document what the code currently does. G0DM0D3's metadata paths are designed without prompt text, response text, images, or credential fields; infrastructure and selected model providers still process network requests, and Cloudflare temporarily uses request IPs for telemetry rate limiting. Full conversation collection is a separate, API-only per-request opt-in. The code is open. Verify it yourself.*
