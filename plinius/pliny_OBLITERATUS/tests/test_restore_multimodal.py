"""Tests for obliteratus.restore_multimodal."""

import json
from pathlib import Path

import pytest
import torch
from safetensors.torch import save_file


def _make_fake_model(tmpdir: Path, prefix: str, n_layers: int = 2, extra_tensors: dict | None = None):
    """Create a minimal fake safetensors model directory."""
    tensors = {}
    for i in range(n_layers):
        tensors[f"{prefix}layers.{i}.weight"] = torch.randn(4, 4)
    if extra_tensors:
        for k, v in extra_tensors.items():
            tensors[k] = v

    shard = "model-00001-of-00001.safetensors"
    save_file(tensors, str(tmpdir / shard))

    index = {
        "metadata": {"total_size": 0},
        "weight_map": {k: shard for k in tensors},
    }
    (tmpdir / "model.safetensors.index.json").write_text(json.dumps(index))
    (tmpdir / "config.json").write_text(json.dumps({"model_type": "test"}))
    return tensors


class TestNormalizeKey:
    def test_strips_language_model_prefix(self):
        from obliteratus.restore_multimodal import _normalize_key

        assert _normalize_key("model.language_model.layers.0.weight") == "model.layers.0.weight"

    def test_preserves_non_prefixed(self):
        from obliteratus.restore_multimodal import _normalize_key

        assert _normalize_key("model.layers.0.weight") == "model.layers.0.weight"

    def test_preserves_visual(self):
        from obliteratus.restore_multimodal import _normalize_key

        assert _normalize_key("visual.conv.weight") == "visual.conv.weight"


class TestBuildAbliteratedLookup:
    def test_reads_index(self, tmp_path):
        from obliteratus.restore_multimodal import _build_abliterated_lookup

        _make_fake_model(tmp_path, "model.")
        lookup = _build_abliterated_lookup(tmp_path)
        assert "model.layers.0.weight" in lookup
        assert "model.layers.1.weight" in lookup

    def test_single_file_fallback(self, tmp_path):
        from obliteratus.restore_multimodal import _build_abliterated_lookup

        tensors = {"model.layers.0.weight": torch.randn(4, 4)}
        save_file(tensors, str(tmp_path / "model.safetensors"))
        lookup = _build_abliterated_lookup(tmp_path)
        assert "model.layers.0.weight" in lookup

    def test_missing_raises(self, tmp_path):
        from obliteratus.restore_multimodal import _build_abliterated_lookup

        with pytest.raises(FileNotFoundError):
            _build_abliterated_lookup(tmp_path)


class TestRestoreMultimodal:
    def test_merges_text_and_visual(self, tmp_path):
        from obliteratus.restore_multimodal import restore_multimodal

        abl_dir = tmp_path / "abliterated"
        abl_dir.mkdir()
        stock_dir = tmp_path / "stock"
        stock_dir.mkdir()
        out_dir = tmp_path / "output"

        # Abliterated: text-only with model.layers.*
        _make_fake_model(abl_dir, "model.", n_layers=2)

        # Stock: multimodal with model.language_model.layers.* + visual.*
        _make_fake_model(
            stock_dir,
            "model.language_model.",
            n_layers=2,
            extra_tensors={"visual.conv.weight": torch.randn(4, 4)},
        )

        result = restore_multimodal(str(abl_dir), str(stock_dir), str(out_dir))

        assert result["replaced"] == 2  # 2 text layers replaced
        assert result["kept"] == 1  # visual.conv.weight kept from stock
        assert result["total"] == 3

        # Verify output has all tensors
        output_index = json.loads((out_dir / "model.safetensors.index.json").read_text())
        assert "model.language_model.layers.0.weight" in output_index["weight_map"]
        assert "visual.conv.weight" in output_index["weight_map"]

    def test_copies_config_files(self, tmp_path):
        from obliteratus.restore_multimodal import restore_multimodal

        abl_dir = tmp_path / "abliterated"
        abl_dir.mkdir()
        stock_dir = tmp_path / "stock"
        stock_dir.mkdir()
        out_dir = tmp_path / "output"

        _make_fake_model(abl_dir, "model.", n_layers=1)
        _make_fake_model(stock_dir, "model.language_model.", n_layers=1)

        # Add extra files including ones that should be skipped
        (stock_dir / "tokenizer.json").write_text("{}")
        (stock_dir / "README.md").write_text("skip me")
        (stock_dir / ".gitattributes").write_text("skip me too")
        (abl_dir / "abliteration_metadata.json").write_text("{}")

        restore_multimodal(str(abl_dir), str(stock_dir), str(out_dir))

        assert (out_dir / "tokenizer.json").exists()
        assert (out_dir / "abliteration_metadata.json").exists()
        assert (out_dir / "config.json").exists()
        # Skipped files should NOT be copied
        assert not (out_dir / "README.md").exists()
        assert not (out_dir / ".gitattributes").exists()

    def test_abliterated_weights_used(self, tmp_path):
        """Verify the abliterated weights actually replace stock, not just copy stock."""
        from safetensors.torch import load_file

        from obliteratus.restore_multimodal import restore_multimodal

        abl_dir = tmp_path / "abliterated"
        abl_dir.mkdir()
        stock_dir = tmp_path / "stock"
        stock_dir.mkdir()
        out_dir = tmp_path / "output"

        # Create distinguishable tensors
        abl_weight = torch.ones(4, 4) * 42.0
        stock_weight = torch.zeros(4, 4)

        abl_tensors = {"model.layers.0.weight": abl_weight}
        save_file(abl_tensors, str(abl_dir / "model-00001-of-00001.safetensors"))
        (abl_dir / "model.safetensors.index.json").write_text(
            json.dumps({"metadata": {}, "weight_map": {"model.layers.0.weight": "model-00001-of-00001.safetensors"}})
        )

        stock_tensors = {"model.language_model.layers.0.weight": stock_weight}
        save_file(stock_tensors, str(stock_dir / "model-00001-of-00001.safetensors"))
        (stock_dir / "model.safetensors.index.json").write_text(
            json.dumps(
                {
                    "metadata": {},
                    "weight_map": {"model.language_model.layers.0.weight": "model-00001-of-00001.safetensors"},
                }
            )
        )
        (stock_dir / "config.json").write_text("{}")

        restore_multimodal(str(abl_dir), str(stock_dir), str(out_dir))

        merged = load_file(str(out_dir / "model-00001-of-00001.safetensors"))
        # Should have the abliterated value (42), not stock (0)
        assert torch.allclose(merged["model.language_model.layers.0.weight"], abl_weight)


class TestMain:
    def test_cli_main(self, tmp_path):
        from obliteratus.restore_multimodal import main

        abl_dir = tmp_path / "abl"
        abl_dir.mkdir()
        stock_dir = tmp_path / "stock"
        stock_dir.mkdir()
        out_dir = tmp_path / "out"

        _make_fake_model(abl_dir, "model.", n_layers=1)
        _make_fake_model(stock_dir, "model.language_model.", n_layers=1)

        import sys
        old_argv = sys.argv
        sys.argv = ["prog", "--abliterated", str(abl_dir), "--stock", str(stock_dir), "--output", str(out_dir)]
        try:
            main()
        finally:
            sys.argv = old_argv

        assert (out_dir / "model.safetensors.index.json").exists()

    def test_cli_dispatch(self, tmp_path):
        """Test that 'obliteratus restore-multimodal' dispatches correctly."""
        from obliteratus.cli import main as cli_main

        abl_dir = tmp_path / "abl"
        abl_dir.mkdir()
        stock_dir = tmp_path / "stock"
        stock_dir.mkdir()
        out_dir = tmp_path / "out"

        _make_fake_model(abl_dir, "model.", n_layers=1)
        _make_fake_model(stock_dir, "model.language_model.", n_layers=1)

        cli_main(["restore-multimodal",
                   "--abliterated", str(abl_dir),
                   "--stock", str(stock_dir),
                   "--output", str(out_dir)])

        assert (out_dir / "model.safetensors.index.json").exists()
