/**
 * Offline fallback when OpenRouter model API is unreachable.
 * Live lists are loaded via OpenRouterModels.fetch() using the user's API key.
 */
window.OPENROUTER_MODELS_FALLBACK = [
    { id: 'openrouter/free', name: 'Free router', summary: 'Zero cost — random free model', provider: 'OpenRouter', virtual: true },
    { id: 'openrouter/auto', name: 'Auto router', summary: 'Smart routing — billed per model', provider: 'OpenRouter', virtual: true },
    { id: 'google/gemma-3-27b-it', name: 'Gemma 3 27B', provider: 'Google' },
    { id: 'google/gemma-3-12b-it', name: 'Gemma 3 12B', provider: 'Google' },
    { id: 'anthropic/claude-sonnet-4.6', name: 'Claude Sonnet 4.6', provider: 'Anthropic' },
    { id: 'openai/gpt-4.1', name: 'GPT-4.1', provider: 'OpenAI' },
    { id: 'google/gemini-2.5-flash-preview', name: 'Gemini 2.5 Flash', provider: 'Google' },
    { id: 'deepseek/deepseek-chat-v3-0324', name: 'DeepSeek V3', provider: 'DeepSeek' },
    { id: 'meta-llama/llama-3.3-70b-instruct', name: 'Llama 3.3 70B', provider: 'Meta' },
    { id: 'nousresearch/hermes-3-llama-3.1-405b', name: 'Hermes 3 405B', provider: 'Nous' }
];

/** @deprecated Use OPENROUTER_MODELS_FALLBACK or OpenRouterModels.fetch() */
window.OPENROUTER_MODELS = window.OPENROUTER_MODELS_FALLBACK;
