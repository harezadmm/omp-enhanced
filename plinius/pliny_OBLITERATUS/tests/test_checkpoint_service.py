"""Public producer-neutral checkpoint service contracts."""

from __future__ import annotations

import torch
from safetensors.torch import save_file

from obliteratus.checkpoint_capabilities import AdapterRegistry
from obliteratus.checkpoint_inspection import InspectionLimits
from obliteratus.checkpoint_service import CheckpointService


def test_service_inspects_canonical_checkpoint_with_injected_limits(tmp_path):
    save_file({"weight": torch.ones(2)}, tmp_path / "model.safetensors")
    service = CheckpointService(inspection_limits=InspectionLimits(max_files=4))

    report = service.inspect(tmp_path)

    assert report.primary_format == "hf_safetensors"
    assert report.support_decision == "canonical_hf_ready"


def test_service_has_no_trusted_reader_adapter_or_conversion_entrypoint():
    service = CheckpointService()

    assert service.adapter_registry == AdapterRegistry()
    assert not hasattr(service, "trusted_inspect")
    assert not hasattr(service, "load_vendor_checkpoint")
    assert not hasattr(service, "convert")
