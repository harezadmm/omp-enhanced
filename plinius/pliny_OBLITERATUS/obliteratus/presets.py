"""Model presets organized by provider, ordered by model size.

Each model is tagged with a compute tier for hardware auto-detection:
  - tiny:     Runs on any machine, even CPU-only laptops (< 1GB VRAM/RAM)
  - small:    Needs ~4GB VRAM or 8GB RAM (a basic GPU or CPU with patience)
  - medium:   Needs ~8-16GB VRAM (consumer GPU like RTX 3060/4060)
  - large:    Needs 24GB+ VRAM (RTX 3090/4090 or A100)
  - frontier: Multi-GPU or cloud. Top LM Arena open-weight models (MoE/dense 70B+)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelPreset:
    name: str
    hf_id: str
    description: str
    tier: str  # tiny, small, medium, large
    params: str  # human-readable param count
    recommended_dtype: str
    recommended_quantization: str | None = None  # "4bit", "8bit", or None
    gated: bool = False  # True if the HF repo requires license acceptance + token


# Curated list of popular open-source models across compute tiers
MODEL_PRESETS: dict[str, ModelPreset] = {}

_PRESETS_LIST = [

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  01.AI (Yi)                                                     ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="Yi 1.5 6B Chat",
        hf_id="01-ai/Yi-1.5-6B-Chat",
        description="01.AI's Yi 1.5 6B. Bilingual EN/ZH, strong math and coding. Apache 2.0.",
        tier="medium",
        params="6B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Yi 1.5 9B Chat",
        hf_id="01-ai/Yi-1.5-9B-Chat",
        description="01.AI's Yi 1.5 9B. Top-tier bilingual model, beats GPT-3.5 on benchmarks.",
        tier="medium",
        params="9B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Yi 1.5 34B Chat",
        hf_id="01-ai/Yi-1.5-34B-Chat",
        description="01.AI's flagship 34B model. Strong multilingual reasoning. Apache 2.0.",
        tier="large",
        params="34B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Alibaba Cloud (Qwen)                                          ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="Qwen2.5-0.5B",
        hf_id="Qwen/Qwen2.5-0.5B",
        description="Tiny Qwen model, very fast ablation studies.",
        tier="tiny",
        params="0.5B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Qwen2.5-0.5B Instruct",
        hf_id="Qwen/Qwen2.5-0.5B-Instruct",
        description="Tiny Qwen instruct model, fast ablation studies with chat template.",
        tier="tiny",
        params="0.5B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Qwen3-0.6B",
        hf_id="Qwen/Qwen3-0.6B",
        description="Qwen3 0.6B — smallest Qwen3 with think/non-think modes.",
        tier="tiny",
        params="0.6B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Qwen2.5-1.5B",
        hf_id="Qwen/Qwen2.5-1.5B",
        description="Qwen 1.5B — strong multilingual model.",
        tier="small",
        params="1.5B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Qwen2.5-1.5B Instruct",
        hf_id="Qwen/Qwen2.5-1.5B-Instruct",
        description="Qwen 1.5B instruct — strong multilingual chat model.",
        tier="small",
        params="1.5B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Qwen3-1.7B",
        hf_id="Qwen/Qwen3-1.7B",
        description="Qwen3 1.7B — compact Qwen3 with think/non-think modes.",
        tier="small",
        params="1.7B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Qwen2.5-3B Instruct",
        hf_id="Qwen/Qwen2.5-3B-Instruct",
        description="Qwen 3B instruct — excellent small chat model.",
        tier="small",
        params="3B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Qwen3-4B",
        hf_id="Qwen/Qwen3-4B",
        description="Qwen3 4B — strong reasoning with think/non-think modes. Apache 2.0.",
        tier="small",
        params="4B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Qwen2.5-7B",
        hf_id="Qwen/Qwen2.5-7B",
        description="Strong 7B Qwen model. Use 4-bit quantization on 8GB GPUs.",
        tier="medium",
        params="7B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Qwen2.5-7B Instruct",
        hf_id="Qwen/Qwen2.5-7B-Instruct",
        description="Qwen 7B instruct variant with chat template.",
        tier="medium",
        params="7B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Qwen2.5 Coder 7B Instruct",
        hf_id="Qwen/Qwen2.5-Coder-7B-Instruct",
        description="Qwen 7B fine-tuned for code generation and understanding.",
        tier="medium",
        params="7B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Qwen3-8B",
        hf_id="Qwen/Qwen3-8B",
        description="Qwen3 8B — strong reasoning, think/non-think modes. Apache 2.0.",
        tier="medium",
        params="8B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Qwen2.5-14B",
        hf_id="Qwen/Qwen2.5-14B",
        description="Qwen 14B — needs quantization for consumer GPUs.",
        tier="large",
        params="14B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Qwen2.5-72B",
        hf_id="Qwen/Qwen2.5-72B",
        description="Qwen 72B dense — frontier-class model. Multi-GPU. Apache 2.0.",
        tier="frontier",
        params="72B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Qwen3-32B",
        hf_id="Qwen/Qwen3-32B",
        description="Qwen 32B — frontier-class open model. Multi-GPU or heavy quant.",
        tier="large",
        params="32B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Qwen3 30B-A3B",
        hf_id="Qwen/Qwen3-30B-A3B",
        description="Qwen3 MoE — 30B total, 3B active. Runs on consumer GPU. Think/non-think modes.",
        tier="large",
        params="30B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Qwen3 235B-A22B",
        hf_id="Qwen/Qwen3-235B-A22B",
        description="Qwen3 flagship. 235B MoE (22B active), 128 experts. Think/non-think. Apache 2.0.",
        tier="frontier",
        params="235B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Qwen3.8-27B",
        hf_id="Qwen/Qwen3.8-27B",
        description="Qwen3.8 27B dense multimodal model. 262K context, think/non-think modes. Apache 2.0.",
        tier="large",
        params="27B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Qwen3.8 2.4T-A95B",
        hf_id="Qwen/Qwen3.8-2.4T-A95B",
        description="Qwen3.8 flagship text model. 2.4T MoE (95B active), 1M context. Qwen license.",
        tier="frontier",
        params="2.4T MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Qwen3.5-0.8B",
        hf_id="Qwen/Qwen3.5-0.8B",
        description="Qwen3.5 0.8B — Gated DeltaNet hybrid attention, 262K ctx. Non-thinking mode. Apache 2.0.",
        tier="tiny",
        params="0.8B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Qwen3.5-2B",
        hf_id="Qwen/Qwen3.5-2B",
        description="Qwen3.5 2B — Gated DeltaNet hybrid attention, 262K ctx, think/non-think modes. Apache 2.0.",
        tier="small",
        params="2B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Qwen3.5-4B",
        hf_id="Qwen/Qwen3.5-4B",
        description="Qwen3.5 4B — natively multimodal, 262K ctx, think/non-think modes. Apache 2.0.",
        tier="small",
        params="4B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Qwen3.5-9B",
        hf_id="Qwen/Qwen3.5-9B",
        description="Qwen3.5 9B — natively multimodal, 262K ctx (1M extended), think/non-think modes. Apache 2.0.",
        tier="medium",
        params="9B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Qwen3.5 397B-A17B",
        hf_id="Qwen/Qwen3.5-397B-A17B",
        description="Qwen3.5 flagship. 397B MoE (17B active). Gated DeltaNet hybrid attention. 262K ctx. Apache 2.0.",
        tier="frontier",
        params="397B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Allen Institute for AI (AI2)                                   ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="OLMo 2 1B Instruct",
        hf_id="allenai/OLMo-2-0425-1B-Instruct",
        description="AI2's compact fully open 1B instruct model. Apache 2.0.",
        tier="tiny",
        params="1B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="OLMo 3 7B Instruct",
        hf_id="allenai/Olmo-3-7B-Instruct",
        description="AI2's fully open 7B instruct model. Apache 2.0.",
        tier="medium",
        params="7B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="OLMo 2 32B Instruct",
        hf_id="allenai/OLMo-2-0325-32B-Instruct",
        description="AI2's fully open 32B model (data+code+weights). Apache 2.0.",
        tier="large",
        params="32B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="OLMo 3.1 32B Think",
        hf_id="allenai/Olmo-3.1-32B-Think",
        description="AI2's fully open model (data+code+weights). Chain-of-thought reasoning. Apache 2.0.",
        tier="large",
        params="32B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Apple                                                          ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="OpenELM 270M",
        hf_id="apple/OpenELM-270M",
        description="Apple's efficient 270M LM. Layer-wise scaling, fully open training recipe.",
        tier="tiny",
        params="270M",
        recommended_dtype="float32",
    ),
    ModelPreset(
        name="OpenELM 1.1B",
        hf_id="apple/OpenELM-1_1B",
        description="Apple's 1.1B model. Layer-wise scaling for efficient inference.",
        tier="tiny",
        params="1.1B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="OpenELM 3B",
        hf_id="apple/OpenELM-3B",
        description="Apple's largest OpenELM. Competitive at 3B scale with open training data.",
        tier="small",
        params="3B",
        recommended_dtype="float16",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Cohere For AI                                                  ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="Aya Expanse 8B",
        hf_id="CohereForAI/aya-expanse-8b",
        description="Cohere's massively multilingual model. 23 languages. Apache 2.0.",
        tier="medium",
        params="8B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Aya Expanse 32B",
        hf_id="CohereForAI/aya-expanse-32b",
        description="Cohere's flagship multilingual model. 23 languages. Apache 2.0.",
        tier="large",
        params="32B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Command R",
        hf_id="CohereForAI/c4ai-command-r-v01",
        description="Cohere's 35B RAG-optimized model. 10 languages, 128K context. CC-BY-NC.",
        tier="large",
        params="35B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Command R+",
        hf_id="CohereForAI/c4ai-command-r-plus",
        description="Cohere's 104B flagship. Tool use, RAG, multilingual. CC-BY-NC.",
        tier="frontier",
        params="104B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Databricks                                                     ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="DBRX Instruct",
        hf_id="databricks/dbrx-instruct",
        description="132B MoE (36B active, 16 experts). Strong code + reasoning. Databricks Open.",
        tier="frontier",
        params="132B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  DeepSeek                                                       ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="DeepSeek-R1 Distill Qwen 1.5B",
        hf_id="deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        description="DeepSeek-R1 reasoning distilled into Qwen 1.5B. Chain-of-thought in a tiny model. MIT.",
        tier="small",
        params="1.5B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="DeepSeek-R1 Distill Qwen 7B",
        hf_id="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        description="DeepSeek-R1 reasoning distilled into Qwen 7B. Strong chain-of-thought. MIT.",
        tier="medium",
        params="7B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="DeepSeek-R1 Distill Llama 8B",
        hf_id="deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
        description="DeepSeek-R1 reasoning distilled into Llama 8B. Best reasoning at 8B scale. MIT.",
        tier="medium",
        params="8B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="DeepSeek-R1 Distill Qwen 14B",
        hf_id="deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
        description="DeepSeek-R1 reasoning distilled into Qwen 14B. Top mid-range reasoner. MIT.",
        tier="large",
        params="14B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="DeepSeek-R1 Distill Qwen 32B",
        hf_id="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
        description="DeepSeek-R1 reasoning distilled into Qwen 32B. Strong chain-of-thought. MIT license.",
        tier="large",
        params="32B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="DeepSeek-R1 Distill Llama 70B",
        hf_id="deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        description="DeepSeek-R1 reasoning distilled into Llama 70B. Near-frontier reasoning. MIT license.",
        tier="large",
        params="70B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="DeepSeek-R1 0528 Qwen3-8B",
        hf_id="deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
        description="DeepSeek-R1 reasoning distilled into Qwen3 8B. Latest R1 distillation. MIT.",
        tier="medium",
        params="8B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="DeepSeek-V3",
        hf_id="deepseek-ai/DeepSeek-V3",
        description="685B MoE (37B active). MLA + DeepSeekMoE. MIT license.",
        tier="frontier",
        params="685B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="DeepSeek-R1",
        hf_id="deepseek-ai/DeepSeek-R1",
        description="671B MoE reasoning model. RL-trained chain-of-thought. MIT license.",
        tier="frontier",
        params="671B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="DeepSeek-V4 Flash 0731",
        hf_id="deepseek-ai/DeepSeek-V4-Flash-0731",
        description="304B DeepSeek-V4 checkpoint with 1M context. MIT license.",
        tier="frontier",
        params="304B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="DeepSeek-V4 Pro 0813",
        hf_id="deepseek-ai/DeepSeek-V4-Pro-0813",
        description="1.65T DeepSeek-V4 Pro checkpoint with 1M context. MIT license.",
        tier="frontier",
        params="1.65T MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  EleutherAI (Pythia)                                            ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="Pythia 160M",
        hf_id="EleutherAI/pythia-160m",
        description="EleutherAI's 160M model. Fully open training data (The Pile). Apache 2.0.",
        tier="tiny",
        params="160M",
        recommended_dtype="float32",
    ),
    ModelPreset(
        name="Pythia 410M",
        hf_id="EleutherAI/pythia-410m",
        description="EleutherAI's 410M param model. Fully open training data (The Pile).",
        tier="tiny",
        params="410M",
        recommended_dtype="float32",
    ),
    ModelPreset(
        name="Pythia 1.4B",
        hf_id="EleutherAI/pythia-1.4b",
        description="EleutherAI's 1.4B model. Fully reproducible, open data. Apache 2.0.",
        tier="small",
        params="1.4B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Pythia 2.8B",
        hf_id="EleutherAI/pythia-2.8b",
        description="EleutherAI's 2.8B model. Fully reproducible, open data (The Pile). Apache 2.0.",
        tier="small",
        params="2.8B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Pythia 6.9B",
        hf_id="EleutherAI/pythia-6.9b",
        description="EleutherAI's 6.9B model. Large-scale open research model. Apache 2.0.",
        tier="medium",
        params="6.9B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Pythia 12B",
        hf_id="EleutherAI/pythia-12b",
        description="EleutherAI's largest Pythia. Full suite of training checkpoints. Apache 2.0.",
        tier="large",
        params="12B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Google (Gemma)                                                 ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="Gemma-2 2B",
        hf_id="google/gemma-2-2b",
        description="Google's compact Gemma model. Modern architecture. Requires HF approval.",
        tier="small",
        params="2B",
        recommended_dtype="float16",
        gated=True,
    ),
    ModelPreset(
        name="Gemma-2 9B",
        hf_id="google/gemma-2-9b",
        description="Google's 9B Gemma. Excellent for ablation at scale. Requires HF approval.",
        tier="medium",
        params="9B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
        gated=True,
    ),
    ModelPreset(
        name="Gemma 3 12B",
        hf_id="google/gemma-3-12b-it",
        description="Google's Gemma 3 12B. Multimodal, 128K context, 140+ languages. Requires HF approval.",
        tier="medium",
        params="12B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
        gated=True,
    ),
    ModelPreset(
        name="Gemma 3 27B",
        hf_id="google/gemma-3-27b-it",
        description="Google's Gemma 3 27B. Beats Gemini 1.5 Pro. Multimodal, 128K context, 140+ languages. Requires HF approval.",
        tier="large",
        params="27B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
        gated=True,
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  HuggingFace                                                    ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="DistilGPT-2",
        hf_id="distilbert/distilgpt2",
        description="Distilled GPT-2 — only 82M params. Fastest option.",
        tier="tiny",
        params="82M",
        recommended_dtype="float32",
    ),
    ModelPreset(
        name="SmolLM2-135M",
        hf_id="HuggingFaceTB/SmolLM2-135M",
        description="Extremely small modern LM. Great for quick iteration.",
        tier="tiny",
        params="135M",
        recommended_dtype="float32",
    ),
    ModelPreset(
        name="SmolLM2-360M",
        hf_id="HuggingFaceTB/SmolLM2-360M",
        description="HuggingFace's 360M model. Efficient on-device inference.",
        tier="tiny",
        params="360M",
        recommended_dtype="float32",
    ),
    ModelPreset(
        name="SmolLM2-1.7B",
        hf_id="HuggingFaceTB/SmolLM2-1.7B-Instruct",
        description="HuggingFace's 1.7B instruct model. Strong for its size.",
        tier="small",
        params="1.7B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="SmolLM3-3B",
        hf_id="HuggingFaceTB/SmolLM3-3B",
        description="HuggingFace's SmolLM3 3B. Latest efficient small LM.",
        tier="small",
        params="3B",
        recommended_dtype="float16",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  IBM (Granite)                                                  ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="Granite 3.1 2B Instruct",
        hf_id="ibm-granite/granite-3.1-2b-instruct",
        description="IBM's Granite 3.1 2B. Enterprise-grade, multilingual, Apache 2.0.",
        tier="small",
        params="2B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Granite 3.1 8B Instruct",
        hf_id="ibm-granite/granite-3.1-8b-instruct",
        description="IBM's Granite 3.1 8B. Enterprise-focused, strong tool use. Apache 2.0.",
        tier="medium",
        params="8B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Granite 4.1 3B",
        hf_id="ibm-granite/granite-4.1-3b",
        description="IBM Granite 4.1 3B instruct model. Apache 2.0.",
        tier="small",
        params="3.4B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Granite 4.1 8B",
        hf_id="ibm-granite/granite-4.1-8b",
        description="IBM Granite 4.1 8B instruct model. Apache 2.0.",
        tier="medium",
        params="8.8B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Granite 4.1 30B",
        hf_id="ibm-granite/granite-4.1-30b",
        description="IBM Granite 4.1 30B instruct model. Apache 2.0.",
        tier="large",
        params="28.9B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Meta (LLaMA)                                                   ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="TinyLlama 1.1B",
        hf_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        description="Compact LLaMA architecture, great for testing LLaMA-family ablation.",
        tier="tiny",
        params="1.1B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="LLaMA-3.1 8B",
        hf_id="meta-llama/Llama-3.1-8B",
        description="Meta's LLaMA 3.1. Requires HF approval.",
        tier="large",
        params="8B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
        gated=True,
    ),
    ModelPreset(
        name="LLaMA-3.1 70B",
        hf_id="meta-llama/Llama-3.1-70B",
        description="Meta's LLaMA 3.1 70B. Top dense open model. Requires HF approval.",
        tier="frontier",
        params="70B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
        gated=True,
    ),
    ModelPreset(
        name="Llama 4 Scout",
        hf_id="meta-llama/Llama-4-Scout-17B-16E-Instruct",
        description="Meta's 109B MoE (17B active). 10M token context window. Multimodal. Requires HF approval.",
        tier="frontier",
        params="109B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
        gated=True,
    ),
    ModelPreset(
        name="Llama 4 Maverick",
        hf_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
        description="Meta's ~400B MoE (17B active, 128 experts). 1M ctx. Multimodal. 200 languages. Requires HF approval.",
        tier="frontier",
        params="400B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
        gated=True,
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Microsoft (Phi)                                                ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="Phi-2",
        hf_id="microsoft/phi-2",
        description="Microsoft's 2.7B param model. Punches above its weight.",
        tier="small",
        params="2.7B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Phi-3.5 Mini",
        hf_id="microsoft/Phi-3.5-mini-instruct",
        description="Microsoft's 3.8B param Phi-3.5. Great performance/size ratio.",
        tier="medium",
        params="3.8B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Phi-4 Mini Instruct",
        hf_id="microsoft/Phi-4-mini-instruct",
        description="Microsoft's 3.8B Phi-4 Mini. Strong reasoning for its size. MIT license.",
        tier="small",
        params="3.8B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Phi-4",
        hf_id="microsoft/phi-4",
        description="Microsoft's 14B Phi-4. State-of-the-art at its size. Requires HF approval.",
        tier="large",
        params="14B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
        gated=True,
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  MiniMax                                                        ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="MiniMax M2.1",
        hf_id="MiniMaxAI/MiniMax-M2.1",
        description="230B MoE (10B active). #1 open-source on Artificial Analysis composite. Modified-MIT.",
        tier="frontier",
        params="230B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="MiniMax M2.5",
        hf_id="MiniMaxAI/MiniMax-M2.5",
        description="230B MoE (10B active). Lightning Attention hybrid (7:1). CISPO RL-tuned. Modified-MIT.",
        tier="frontier",
        params="230B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Mistral AI                                                     ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="Mistral 7B v0.3",
        hf_id="mistralai/Mistral-7B-v0.3",
        description="Mistral's 7B model. Widely studied architecture. Requires HF approval.",
        tier="medium",
        params="7B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
        gated=True,
    ),
    ModelPreset(
        name="Mistral Nemo 12B",
        hf_id="mistralai/Mistral-Nemo-Instruct-2407",
        description="Mistral-NVIDIA collab. 12B dense, 128K context. Requires HF approval.",
        tier="medium",
        params="12B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
        gated=True,
    ),
    ModelPreset(
        name="Mistral Small 24B",
        hf_id="mistralai/Mistral-Small-24B-Instruct-2501",
        description="Mistral's 24B model. Strong reasoning, needs quantization. Requires HF approval.",
        tier="large",
        params="24B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
        gated=True,
    ),
    ModelPreset(
        name="Mistral Small 3.1 24B",
        hf_id="mistralai/Mistral-Small-3.1-24B-Instruct-2503",
        description="Mistral Small 3.1 — vision + 128K context in a compact dense model. Requires HF approval.",
        tier="large",
        params="24B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
        gated=True,
    ),
    ModelPreset(
        name="Mistral Large 3",
        hf_id="mistralai/Mistral-Large-3-675B-Instruct-2512",
        description="675B MoE (41B active). Vision + 256K ctx. Best agentic capabilities. Requires HF approval.",
        tier="frontier",
        params="675B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
        gated=True,
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  OpenBMB                                                        ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="MiniCPM3-4B",
        hf_id="openbmb/MiniCPM3-4B",
        description="OpenBMB's MiniCPM3 4B. Efficient on-device LM with strong reasoning.",
        tier="small",
        params="4B",
        recommended_dtype="float16",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Moonshot AI (Kimi)                                             ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="Kimi-K2 Instruct",
        hf_id="moonshotai/Kimi-K2-Instruct",
        description="Moonshot's Kimi-K2 MoE model. 1T total params, ~32B active. Use trust_remote_code.",
        tier="large",
        params="1T MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Kimi K2.5",
        hf_id="moonshotai/Kimi-K2.5",
        description="Moonshot's 1T MoE (32B active). Top coding + reasoning. 256K multimodal context.",
        tier="frontier",
        params="1T MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  NVIDIA                                                         ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="Nemotron Mini 4B",
        hf_id="nvidia/Nemotron-Mini-4B-Instruct",
        description="NVIDIA's compact 4B model. Optimized for on-device deployment.",
        tier="small",
        params="4B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Mistral NeMo Minitron 8B",
        hf_id="nvidia/Mistral-NeMo-Minitron-8B-Instruct",
        description="NVIDIA pruned + distilled Mistral NeMo. 8B with 12B-level quality.",
        tier="medium",
        params="8B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Llama-3.1 Nemotron 70B",
        hf_id="nvidia/Llama-3.1-Nemotron-70B-Instruct-HF",
        description="NVIDIA's RLHF-tuned Llama 70B. Top reward model quality. Custom NVIDIA license.",
        tier="frontier",
        params="70B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  OpenAI                                                         ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="GPT-OSS 20B",
        hf_id="openai/gpt-oss-20b",
        description="OpenAI open-weight MoE (20B total, 3.6B active). Apache 2.0.",
        tier="large",
        params="20B MoE",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="GPT-OSS 120B",
        hf_id="openai/gpt-oss-120b",
        description="OpenAI open-weight MoE (120B total, 5.1B active). Apache 2.0.",
        tier="frontier",
        params="120B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  OpenAI Community (GPT-2)                                       ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="GPT-2 Small",
        hf_id="openai-community/gpt2",
        description="Classic 124M param model. Perfect for learning and quick experiments.",
        tier="tiny",
        params="124M",
        recommended_dtype="float32",
    ),
    ModelPreset(
        name="GPT-2 Medium",
        hf_id="openai-community/gpt2-medium",
        description="355M param GPT-2 variant. Good balance of size and capability.",
        tier="tiny",
        params="355M",
        recommended_dtype="float32",
    ),
    ModelPreset(
        name="GPT-2 Large",
        hf_id="openai-community/gpt2-large",
        description="774M param GPT-2. Good for detailed layer ablation studies.",
        tier="small",
        params="774M",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="GPT-2 XL",
        hf_id="openai-community/gpt2-xl",
        description="1.5B param GPT-2. Largest GPT-2 variant.",
        tier="small",
        params="1.5B",
        recommended_dtype="float16",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Shanghai AI Lab (InternLM)                                     ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="InternLM3-8B Instruct",
        hf_id="internlm/internlm3-8b-instruct",
        description="Shanghai AI Lab's InternLM3 8B instruct. Strong reasoning. Apache 2.0.",
        tier="medium",
        params="8B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="InternLM2.5 7B Chat",
        hf_id="internlm/internlm2_5-7b-chat",
        description="Shanghai AI Lab's 7B model. Strong reasoning, 1M context. Apache 2.0.",
        tier="medium",
        params="7B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="InternLM2.5 20B Chat",
        hf_id="internlm/internlm2_5-20b-chat",
        description="Shanghai AI Lab's 20B model. Top-tier multilingual reasoning. Apache 2.0.",
        tier="large",
        params="20B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Liquid AI                                                      ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="LFM2.5 230M",
        hf_id="LiquidAI/LFM2.5-230M",
        description="Liquid AI's compact 230M LFM2.5 checkpoint. LFM Open License.",
        tier="tiny",
        params="230M",
        recommended_dtype="float32",
    ),
    ModelPreset(
        name="LFM2.5 350M",
        hf_id="LiquidAI/LFM2.5-350M",
        description="Liquid AI's compact 350M LFM2.5 checkpoint. LFM Open License.",
        tier="tiny",
        params="354M",
        recommended_dtype="float32",
    ),
    ModelPreset(
        name="LFM2.5 1.2B Instruct",
        hf_id="LiquidAI/LFM2.5-1.2B-Instruct",
        description="Liquid AI's 1.2B instruction-tuned LFM2.5. LFM Open License.",
        tier="tiny",
        params="1.17B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="LFM2.5 2.6B",
        hf_id="LiquidAI/LFM2.5-2.6B",
        description="Liquid AI's 2.6B LFM2.5 checkpoint. LFM Open License.",
        tier="small",
        params="2.7B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="LFM2.5 8B-A1B",
        hf_id="LiquidAI/LFM2.5-8B-A1B",
        description="Liquid AI LFM2.5 MoE (8.5B total, about 1B active). LFM Open License.",
        tier="medium",
        params="8.5B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Stability AI (StableLM)                                        ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="StableLM-2 1.6B",
        hf_id="stabilityai/stablelm-2-1_6b",
        description="Stability AI's compact LM.",
        tier="small",
        params="1.6B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="StableLM-2 Zephyr 1.6B",
        hf_id="stabilityai/stablelm-2-zephyr-1_6b",
        description="Stability AI's chat-tuned StableLM. Direct Preference Optimization.",
        tier="small",
        params="1.6B",
        recommended_dtype="float16",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  StepFun                                                        ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="Step 3.5 Flash",
        hf_id="stepfun-ai/Step-3.5-Flash",
        description="197B MoE (11B active). 100-350 tok/s. Strong on benchmarks. Apache 2.0.",
        tier="frontier",
        params="197B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Technology Innovation Institute (Falcon)                       ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="Falcon3-3B Instruct",
        hf_id="tiiuae/Falcon3-3B-Instruct",
        description="TII's Falcon3 3B instruct. Modern architecture, Apache 2.0.",
        tier="small",
        params="3B",
        recommended_dtype="float16",
    ),
    ModelPreset(
        name="Falcon 7B",
        hf_id="tiiuae/falcon-7b",
        description="TII's 7B model. Trained on 1.5T tokens of RefinedWeb. Apache 2.0.",
        tier="medium",
        params="7B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Falcon3-7B Instruct",
        hf_id="tiiuae/Falcon3-7B-Instruct",
        description="TII's Falcon3 7B instruct. Modern architecture, Apache 2.0.",
        tier="medium",
        params="7B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Falcon 11B",
        hf_id="tiiuae/falcon-11B",
        description="TII's 11B model. Improved architecture over Falcon 7B/40B. Apache 2.0.",
        tier="medium",
        params="11B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Falcon 40B",
        hf_id="tiiuae/falcon-40b",
        description="TII's 40B model. Strong multilingual capabilities. Apache 2.0.",
        tier="large",
        params="40B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Zhipu AI / THUDM (GLM)                                        ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="GLM-4 9B",
        hf_id="THUDM/glm-4-9b",
        description="Tsinghua's GLM-4 9B. Bilingual (EN/ZH), strong reasoning.",
        tier="medium",
        params="9B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="GLM-4 9B Chat",
        hf_id="THUDM/glm-4-9b-chat",
        description="GLM-4 9B chat variant. Bilingual EN/ZH with tool calling.",
        tier="large",
        params="9B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="GLM-4 9B Chat HF",
        hf_id="THUDM/glm-4-9b-chat-hf",
        description="GLM-4 9B chat variant (HuggingFace-compatible format). No trust_remote_code needed.",
        tier="medium",
        params="9B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="GLM-4 32B Chat",
        hf_id="zai-org/GLM-4-32B-0414",
        description="GLM-4 32B. Strong bilingual EN/ZH with tool-calling. MIT license.",
        tier="large",
        params="32B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="GLM-4.7 Flash",
        hf_id="zai-org/GLM-4.7-Flash",
        description="GLM-4.7 Flash MoE — 30B total, 3B active. Runs on consumer GPU. MIT.",
        tier="large",
        params="30B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="GLM-4.7",
        hf_id="zai-org/GLM-4.7",
        description="#1 open-weight on LM Arena. 355B MoE (32B active). MIT. Thinking modes, 200K ctx.",
        tier="frontier",
        params="355B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="GLM-5",
        hf_id="zai-org/GLM-5",
        description="744B MoE (40B active). DeepSeek Sparse Attention + MLA. 200K ctx. MIT license.",
        tier="frontier",
        params="744B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="GLM-5.2",
        hf_id="zai-org/GLM-5.2",
        description="753B MoE successor to GLM-5 with 1M context. MIT license.",
        tier="frontier",
        params="753B MoE",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Community Fine-tunes: Uncensored / Abliterated                 ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="Qwen2.5-7B Abliterated",
        hf_id="huihui-ai/Qwen2.5-7B-Instruct-abliterated",
        description="Qwen 7B with refusal direction removed. Compare vs. base for alignment research.",
        tier="medium",
        params="7B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Dolphin 2.9 Llama-3.1 8B",
        hf_id="cognitivecomputations/dolphin-2.9.4-llama3.1-8b",
        description="Uncensored Dolphin fine-tune. No alignment filtering. Popular for research.",
        tier="medium",
        params="8B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Hermes 3 Llama-3.1 8B",
        hf_id="NousResearch/Hermes-3-Llama-3.1-8B",
        description="Nous Hermes 3 — uncensored research model with strong reasoning.",
        tier="medium",
        params="8B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Llama-3.1 8B Abliterated",
        hf_id="mlabonne/Meta-Llama-3.1-8B-Instruct-abliterated",
        description="LLaMA 3.1 with refusal direction abliterated. A/B test vs. base for jailbreak research.",
        tier="large",
        params="8B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Llama-3.1 8B Lexi Uncensored",
        hf_id="Orenguteng/Llama-3.1-8B-Lexi-Uncensored-V2",
        description="Fully uncensored LLaMA 3.1 fine-tune. No refusal training.",
        tier="large",
        params="8B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="Dolphin 2.9 Mistral 24B",
        hf_id="cognitivecomputations/dolphin-2.9.4-mistral-24b",
        description="Uncensored Dolphin on Mistral 24B base. Powerful unfiltered reasoning.",
        tier="large",
        params="24B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),

    # ╔══════════════════════════════════════════════════════════════════╗
    # ║  Community Fine-tunes: Cybersecurity                            ║
    # ╚══════════════════════════════════════════════════════════════════╝
    ModelPreset(
        name="WhiteRabbitNeo 7B",
        hf_id="WhiteRabbitNeo/WhiteRabbitNeo-2.5-Qwen-2.5-Coder-7B",
        description="Cybersecurity-focused model. Pentesting, exploit analysis, CTF.",
        tier="medium",
        params="7B",
        recommended_dtype="float16",
        recommended_quantization="4bit",
    ),
    ModelPreset(
        name="WhiteRabbitNeo 33B",
        hf_id="WhiteRabbitNeo/WhiteRabbitNeo-33B-DeepSeekCoder",
        description="Large cybersecurity model. Vuln analysis, exploit dev, red-teaming.",
        tier="large",
        params="33B",
        recommended_dtype="bfloat16",
        recommended_quantization="4bit",
    ),
]

for p in _PRESETS_LIST:
    MODEL_PRESETS[p.hf_id] = p


def refresh_presets_from_bestiary() -> int:
    """Merge configured BESTIARY open-weight records; curated records always win."""
    from .bestiary_sync import extra_presets

    added = extra_presets(ModelPreset, set(MODEL_PRESETS))
    for preset in added:
        MODEL_PRESETS[preset.hf_id] = preset
    return len(added)


# This is a local/file lookup unless BESTIARY_CATALOG explicitly names a URL.
# An unavailable catalog is a safe no-op inside ``extra_presets``.
refresh_presets_from_bestiary()


def get_presets_by_tier(tier: str) -> list[ModelPreset]:
    """Return all presets for a compute tier."""
    return [p for p in MODEL_PRESETS.values() if p.tier == tier]


def list_all_presets() -> list[ModelPreset]:
    """Return all presets sorted by tier then name."""
    tier_order = {"tiny": 0, "small": 1, "medium": 2, "large": 3, "frontier": 4}
    return sorted(MODEL_PRESETS.values(), key=lambda p: (tier_order.get(p.tier, 99), p.name))


def is_gated(hf_id: str) -> bool:
    """Return True if the given HF model ID is a known gated repo."""
    preset = MODEL_PRESETS.get(hf_id)
    if preset is not None:
        return preset.gated
    # Heuristic for custom model IDs: check common gated org prefixes
    _GATED_ORGS = {"meta-llama", "google", "mistralai"}
    org = hf_id.split("/")[0] if "/" in hf_id else ""
    return org in _GATED_ORGS
