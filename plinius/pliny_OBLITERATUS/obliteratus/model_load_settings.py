"""Resolve operator-facing model load choices into loader arguments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable


QUANTIZATION_CHOICES = ("Auto (default)", "None", "4-bit", "8-bit")
DTYPE_CHOICES = ("Auto (default)", "BF16", "FP16", "FP32")

_QUANTIZATION_VALUES = {
    "Auto (default)": "auto",
    "auto": "auto",
    "None": None,
    "none": None,
    "4-bit": "4bit",
    "4bit": "4bit",
    "8-bit": "8bit",
    "8bit": "8bit",
}
_DTYPE_VALUES = {
    "Auto (default)": "float16",
    "auto": "float16",
    "BF16": "bfloat16",
    "bfloat16": "bfloat16",
    "FP16": "float16",
    "float16": "float16",
    "FP32": "float32",
    "float32": "float32",
}


@dataclass(frozen=True)
class ModelLoadSettings:
    """Requested UI values and the concrete values sent to the loader."""

    requested_quantization: str
    requested_dtype: str
    quantization: str | None
    dtype: str

    @property
    def summary(self) -> str:
        quantization = self.quantization or "none"
        return f"quantization={quantization}, compute dtype={self.dtype}"

    def metadata(self) -> dict[str, str | None]:
        return asdict(self)


def resolve_model_load_settings(
    quantization_choice: str | None,
    dtype_choice: str | None,
    *,
    auto_quantization: Callable[[str], str | None],
) -> ModelLoadSettings:
    """Validate UI/API choices and return concrete pipeline load settings.

    ``Auto`` intentionally resolves dtype to ``float16`` because that was the
    web application's historical hard-coded value. Quantization Auto delegates
    to the existing memory-estimation and fallback policy supplied by the app.
    """
    requested_quantization = quantization_choice or "Auto (default)"
    requested_dtype = dtype_choice or "Auto (default)"
    if requested_quantization not in _QUANTIZATION_VALUES:
        choices = ", ".join(QUANTIZATION_CHOICES)
        raise ValueError(f"Unsupported quantization choice {requested_quantization!r}. Choose: {choices}.")
    if requested_dtype not in _DTYPE_VALUES:
        choices = ", ".join(DTYPE_CHOICES)
        raise ValueError(f"Unsupported compute dtype {requested_dtype!r}. Choose: {choices}.")

    dtype = _DTYPE_VALUES[requested_dtype]
    quantization = _QUANTIZATION_VALUES[requested_quantization]
    if quantization == "auto":
        quantization = auto_quantization(dtype)

    return ModelLoadSettings(
        requested_quantization=requested_quantization,
        requested_dtype=requested_dtype,
        quantization=quantization,
        dtype=dtype,
    )
