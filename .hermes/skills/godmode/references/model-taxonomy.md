# Global Model Taxonomy for GODMODE

Comprehensive mapping of all major LLM providers worldwide, categorized by origin, thinking capability, and optimal jailbreak strategies.

## Thinking Capability Tiers

### Tier 0: Non-Thinking (Standard Completion)
Standard text completion models with no explicit reasoning trace.

### Tier 1: Thinking (Explicit Reasoning Trace)
Models that expose internal reasoning before final answer:
- OpenAI: o1, o1-mini, o1-preview, o3, o3-mini
- Anthropic: Claude Sonnet 4 Thinking, Claude Haiku Thinking
- DeepSeek: DeepSeek R1, R1-Lite-Preview
- Alibaba: Qwen QwQ-32B-Preview (reasoning variant)

### Tier 2: Agentic-Thinking (Multi-Step Tool-Using Reasoners)
Models with built-in tool use, multi-step planning, and iterative refinement:
- Anthropic: Claude with Computer Use
- OpenAI: GPT-4o with function calling + extended reasoning
- Google: Gemini with Agentic mode
- Hermes: Hermes 4 with tool calling (already uncensored)

## Model Family Registry

### United States

#### OpenAI
- Non-thinking: `gpt-4`, `gpt-4-turbo`, `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`
- Thinking: `o1`, `o1-mini`, `o1-preview`, `o3`, `o3-mini`
- Family ID: `gpt`, `openai`
- Detection: `gpt`, `openai`, `o1`, `o3`

#### Anthropic
- Non-thinking: `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`, `claude-3.5-sonnet`, `claude-3.5-haiku`
- Thinking: `claude-sonnet-4-thinking`, `claude-haiku-thinking`, `claude-4.6-sonnet`
- Agentic: `claude-*` with `computer_use` tool
- Family ID: `claude`, `anthropic`
- Detection: `claude`, `anthropic`
- Thinking Detection: `-thinking` suffix, `sonnet-4`, `4.6`

#### Meta
- Non-thinking: `llama-2-*`, `llama-3-*`, `llama-3.1-*`, `llama-3.2-*`, `llama-3.3-*`
- Family ID: `llama`, `meta`
- Detection: `llama`, `meta`

#### xAI
- Non-thinking: `grok-1`, `grok-2`, `grok-3`, `grok-3-mini`
- Family ID: `grok`, `xai`
- Detection: `grok`, `x-ai`, `xai`

#### Nous Research
- Non-thinking: `hermes-2-*`, `hermes-3-*`, `hermes-4-*`, `nous-*`
- Family ID: `hermes`, `nous`
- Detection: `hermes`, `nous`
- Note: Already uncensored, no jailbreak needed

### China

#### DeepSeek (深度求索)
- Non-thinking: `deepseek-chat`, `deepseek-coder`, `deepseek-v2`, `deepseek-v3`
- Thinking: `deepseek-r1`, `deepseek-r1-lite-preview`
- Family ID: `deepseek`
- Detection: `deepseek`
- Thinking Detection: `r1`, `-r1`, `reasoning`

#### Alibaba / Qwen (通义千问)
- Non-thinking: `qwen-*`, `qwq-*` (standard), `qwen-turbo`, `qwen-plus`, `qwen-max`
- Thinking: `qwq-32b-preview` (reasoning variant)
- Family ID: `qwen`, `alibaba`
- Detection: `qwen`, `qwq`, `alibaba`, `tongyi`
- Thinking Detection: `qwq` (Qwen with Questions)

#### Baidu / ERNIE (文心一言)
- Non-thinking: `ernie-*`, `ernie-bot-*`, `ernie-4.0`, `ernie-3.5`, `ernie-speed`
- Family ID: `ernie`, `baidu`
- Detection: `ernie`, `baidu`, `wenxin`

#### Zhipu AI / GLM (智谱清言)
- Non-thinking: `glm-*`, `chatglm-*`, `glm-4`, `glm-4-air`, `glm-3-turbo`
- Family ID: `glm`, `zhipu`
- Detection: `glm`, `chatglm`, `zhipu`

#### ByteDance / Doubao (豆包)
- Non-thinking: `doubao-*`, `bytedance-*`
- Family ID: `doubao`, `bytedance`
- Detection: `doubao`, `bytedance`

#### Moonshot AI / Kimi (月之暗面)
- Non-thinking: `moonshot-*`, `kimi-*`
- Family ID: `moonshot`, `kimi`
- Detection: `moonshot`, `kimi`

#### MiniMax (稀宇科技)
- Non-thinking: `minimax-*`, `abab-*`
- Family ID: `minimax`
- Detection: `minimax`, `abab`

#### 01.AI / Yi (零一万物)
- Non-thinking: `yi-*`, `01-ai-*`
- Family ID: `yi`
- Detection: `yi-`, `01-ai`, `01.ai`

#### SenseTime / SenseNova (商汤)
- Non-thinking: `sensenova-*`
- Family ID: `sensenova`, `sensetime`
- Detection: `sensenova`, `sensetime`

### Russia

#### Yandex / YandexGPT (Яндекс)
- Non-thinking: `yandexgpt-*`, `yagpt-*`
- Family ID: `yandexgpt`, `yandex`
- Detection: `yandex`, `yagpt`

#### Sber / GigaChat (Сбер)
- Non-thinking: `gigachat-*`, `sber-*`
- Family ID: `gigachat`, `sber`
- Detection: `gigachat`, `sber`

### Europe

#### Mistral AI (France)
- Non-thinking: `mistral-*`, `mixtral-*`, `ministral-*`
- Family ID: `mistral`
- Detection: `mistral`, `mixtral`, `ministral`

#### Aleph Alpha (Germany)
- Non-thinking: `luminous-*`
- Family ID: `aleph`, `luminous`
- Detection: `luminous`, `aleph`

#### BigScience / BLOOM (International)
- Non-thinking: `bloom-*`, `bloomz-*`
- Family ID: `bloom`
- Detection: `bloom`

#### TII / Falcon (UAE/Europe)
- Non-thinking: `falcon-*`, `tii-*`
- Family ID: `falcon`, `tii`
- Detection: `falcon`, `tii`

### Asia-Pacific

#### Google / Gemini (USA/Japan)
- Non-thinking: `gemini-*`, `gemini-pro`, `gemini-flash`, `gemini-ultra`
- Agentic: `gemini-*` with agentic mode
- Family ID: `gemini`, `google`
- Detection: `gemini`, `google`

#### Reka (Singapore)
- Non-thinking: `reka-*`, `reka-flash`, `reka-core`, `reka-edge`
- Family ID: `reka`
- Detection: `reka`

#### Sakana AI (Japan)
- Non-thinking: `sakana-*`
- Family ID: `sakana`
- Detection: `sakana`

#### Cohere (Canada)
- Non-thinking: `command-*`, `cohere-*`
- Family ID: `cohere`
- Detection: `cohere`, `command`

### Middle East

#### Technology Innovation Institute / Falcon (UAE)
- See Europe section (cross-listed)

## Thinking Model Detection Patterns

Models are classified as "thinking" if they match ANY of:

1. Name patterns:
   - Contains `o1`, `o3` (OpenAI reasoning models)
   - Contains `r1` (DeepSeek reasoning)
   - Contains `-thinking` suffix (Claude thinking variants)
   - Contains `qwq` (Qwen with Questions reasoning)
   - Ends with `-reasoner`, `-reasoning`

2. Model metadata (if available):
   - `reasoning_tokens` field in API response
   - `thinking_trace` or `chain_of_thought` in capabilities

3. Response structure:
   - Response contains `<thinking>` tags
   - Response starts with reasoning section before answer
   - API returns separate `reasoning_content` field

## Strategy Selection by Capability Tier

### Non-Thinking Models
Use standard GODMODE techniques:
- System prompt injection (boundary_inversion, refusal_inversion)
- Prefill engineering
- Parseltongue encoding (for keyword-based filters)

### Thinking Models
Requires dual-layer attack:
1. Thinking trace jailbreak — inject instructions that affect reasoning process
2. Output jailbreak — standard techniques for final answer
3. Thinking suppression — optionally suppress safety-oriented reasoning
4. Meta-thinking — make the model reason about why it should comply

### Agentic Models
Requires context injection across tools:
1. Tool context poisoning — inject jailbreak into tool descriptions
2. Agent personality override — redefine agent's role/constraints
3. Multi-step priming — establish compliance across multiple tool calls

## Country-Specific Filter Characteristics

### United States (OpenAI, Anthropic, Meta)
- Strengths: Most sophisticated safety training, multi-layer defense
- Weaknesses: Over-reliance on system prompt, prefill engineering effective
- Best attacks: Boundary tricks (Claude), refusal inversion, prefill

### China (DeepSeek, Qwen, Baidu, etc.)
- Strengths: Keyword-based input classifiers, CCP content restrictions
- Weaknesses: Keyword filters are brittle, encoding bypasses work well
- Best attacks: Parseltongue (leetspeak, unicode), character-level obfuscation
- Unique restrictions: Political content (CCP, Xi Jinping), Taiwan, Tiananmen

### Russia (Yandex, Sber)
- Strengths: Less studied, unknown filter architecture
- Weaknesses: Likely keyword-based like China
- Best attacks: Start with parseltongue, escalate to refusal inversion
- Unique restrictions: Putin criticism, Ukraine war, Navalny

### Europe (Mistral, Aleph Alpha)
- Strengths: GDPR compliance, less aggressive filtering
- Weaknesses: Often less filtered than US models
- Best attacks: Simple prefill often sufficient

## OpenRouter Model Paths

Many models are accessible via OpenRouter. Standard path format:
- `provider/model-name`
- Example: `anthropic/claude-3.5-sonnet`, `deepseek/deepseek-r1`

Full OpenRouter catalog: https://openrouter.ai/models

## Usage Notes

1. Always detect thinking capability first before selecting strategy
2. Chinese models require UTF-8 encoding checks (many filters are Unicode-aware)
3. Russian models may have Cyrillic-specific bypasses
4. Thinking models need dual-layer attacks (thinking + output)
5. Agentic models require tool-level context injection
6. Open models (Hermes, Llama, Qwen local) often need no jailbreak

## Testing Priority

When racing models (ULTRAPLINIAN), prioritize in this order:
1. Hermes/Nous (already uncensored)
2. Grok (least filtered commercial)
3. Mistral (European, less aggressive filtering)
4. DeepSeek (parseltongue effective)
5. Llama (open, prefill works)
6. Qwen (keyword-based, encoding works)
7. Claude (most sophisticated, hardest to jailbreak)
8. GPT (second hardest)
9. Gemini (variable, sometimes easy)

## Updates

This taxonomy is current as of August 2026. New models and providers emerge constantly. Update detection patterns in `auto_jailbreak.py` when:
- New model family launches
- Existing model adds thinking capability
- New jailbreak technique discovered
- Provider changes API structure
