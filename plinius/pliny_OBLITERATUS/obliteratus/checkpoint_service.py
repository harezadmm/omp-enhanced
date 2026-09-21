"""Public Wave 2 service for offline checkpoint structural inspection."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from obliteratus.checkpoint_capabilities import AdapterRegistry
from obliteratus.checkpoint_inspection import (
    CheckpointInspection,
    InspectionLimits,
    inspect_checkpoint,
)


@dataclass(frozen=True)
class CheckpointService:
    """Expose the common safe plane without trusted readers or producer adapters."""

    inspection_limits: InspectionLimits = field(default_factory=InspectionLimits)
    adapter_registry: AdapterRegistry = field(default_factory=AdapterRegistry)

    def inspect(self, source: Path | str) -> CheckpointInspection:
        """Return a bounded structure-only descriptor for one local source."""
        return inspect_checkpoint(
            source,
            limits=self.inspection_limits,
            adapter_registry=self.adapter_registry,
        )
