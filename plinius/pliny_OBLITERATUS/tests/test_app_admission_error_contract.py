"""Static UI contracts for actionable GPU admission failures."""

from pathlib import Path


def test_obliterate_catches_admission_before_cuda_cleanup():
    source = Path("app.py").read_text(encoding="utf-8")
    obliterate = source.index("def obliterate(")
    loading = source.index("_gpu_lifecycle.loading(model_id)", obliterate)
    handler = source.index("except AdmissionError as exc:", loading)
    cleanup = source.index("_clear_gpu(release_lifecycle=False)", handler)

    assert obliterate < loading < handler < cleanup
    block = source[loading:cleanup]
    assert "exc.user_message()" in block
    assert "exc.diagnostic_message()" in block
    assert '_state["status"] = "idle"' in block
    assert "return" in block
