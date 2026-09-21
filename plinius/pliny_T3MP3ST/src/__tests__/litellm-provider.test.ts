import { afterEach, describe, expect, it } from 'vitest';
import { config, AVAILABLE_MODELS } from '../config/index.js';
import { createLiteLLMBackbone } from '../llm/index.js';

const PREV_BASE = process.env.LITELLM_BASE_URL;
const PREV_KEY = process.env.LITELLM_API_KEY;
const PREV_MODEL = process.env.LITELLM_MODEL;

describe('LiteLLM provider wiring (#45)', () => {
  afterEach(() => {
    if (PREV_BASE === undefined) delete process.env.LITELLM_BASE_URL;
    else process.env.LITELLM_BASE_URL = PREV_BASE;
    if (PREV_KEY === undefined) delete process.env.LITELLM_API_KEY;
    else process.env.LITELLM_API_KEY = PREV_KEY;
    if (PREV_MODEL === undefined) delete process.env.LITELLM_MODEL;
    else process.env.LITELLM_MODEL = PREV_MODEL;
  });

  it('resolves LiteLLM as an OpenAI-compatible proxy from env without requiring a key', () => {
    process.env.LITELLM_BASE_URL = 'http://localhost:4000/v1';
    delete process.env.LITELLM_API_KEY;
    process.env.LITELLM_MODEL = 'anthropic/claude-sonnet-4.5';

    const cfg = config.getLLMConfig('litellm');
    expect(cfg.provider).toBe('litellm');
    expect(cfg.baseUrl).toBe('http://localhost:4000/v1');
    expect(cfg.model).toBe('anthropic/claude-sonnet-4.5');
    expect(cfg.apiKey).toBeUndefined();
    expect(config.getConfiguredProviders()).toContain('litellm');
  });

  it('the LiteLLM backbone validates when only a proxy base URL is configured', () => {
    process.env.LITELLM_BASE_URL = 'http://localhost:4000/v1';
    const backbone = createLiteLLMBackbone();

    expect(backbone.getProvider()).toBe('litellm');
    expect(backbone.validateConfig().valid).toBe(true);
  });

  it('surfaces a static LiteLLM model catalog entry', () => {
    expect(AVAILABLE_MODELS.litellm?.length ?? 0).toBeGreaterThan(0);
    expect(AVAILABLE_MODELS.litellm[0].provider).toBe('LiteLLM');
  });
});
