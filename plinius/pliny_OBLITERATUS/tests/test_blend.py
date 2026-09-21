"""Tests for obliteratus.blend — complementary abliteration blending."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch
from safetensors.torch import load_file, save_file


def _make_model(
    tmpdir: Path,
    value: float,
    n_tensors: int = 3,
    *,
    config_name: str = "test",
):
    """Create a minimal model with all weights set to a constant value."""
    tensors = {f"layer.{i}.weight": torch.full((4, 4), value) for i in range(n_tensors)}
    shard = "model-00001-of-00001.safetensors"
    save_file(tensors, str(tmpdir / shard))
    index = {"metadata": {}, "weight_map": {k: shard for k in tensors}}
    (tmpdir / "model.safetensors.index.json").write_text(json.dumps(index))
    (tmpdir / "config.json").write_text(json.dumps({"model_type": config_name}))
    (tmpdir / "abliteration_metadata.json").write_text(
        json.dumps({"source_model": "example/base-model"}),
    )
    return tensors


def _make_sharded_model(tmpdir: Path, values: dict[str, float], shard_for: dict[str, str]):
    by_shard: dict[str, dict[str, torch.Tensor]] = {}
    for key, value in values.items():
        by_shard.setdefault(shard_for[key], {})[key] = torch.full((2, 2), value)
    for shard, tensors in by_shard.items():
        save_file(tensors, str(tmpdir / shard))
    index = {"metadata": {}, "weight_map": shard_for}
    (tmpdir / "model.safetensors.index.json").write_text(json.dumps(index))
    (tmpdir / "config.json").write_text(json.dumps({"model_type": "test"}))
    (tmpdir / "abliteration_metadata.json").write_text(
        json.dumps({"source_model": "example/base-model"}),
    )


class TestBlendModels:
    def test_lerp_blend(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "model_a"
        b_dir = tmp_path / "model_b"
        out_dir = tmp_path / "blended"
        a_dir.mkdir()
        b_dir.mkdir()

        _make_model(a_dir, 0.0)
        _make_model(b_dir, 10.0)

        result = blend_models(str(a_dir), str(b_dir), str(out_dir), alpha=0.6)

        assert result["blended_tensors"] == 3
        assert result["total_tensors"] == 3
        assert result["alpha"] == 0.6

        merged = load_file(str(out_dir / "model-00001-of-00001.safetensors"))
        # 0.6 * 10.0 + 0.4 * 0.0 = 6.0
        assert torch.allclose(merged["layer.0.weight"], torch.full((4, 4), 6.0))

    def test_alpha_zero_is_pure_a(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        out = tmp_path / "out"
        a_dir.mkdir()
        b_dir.mkdir()

        _make_model(a_dir, 42.0)
        _make_model(b_dir, 99.0)

        blend_models(str(a_dir), str(b_dir), str(out), alpha=0.0)
        merged = load_file(str(out / "model-00001-of-00001.safetensors"))
        assert torch.allclose(merged["layer.0.weight"], torch.full((4, 4), 42.0))

    def test_alpha_one_is_pure_b(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        out = tmp_path / "out"
        a_dir.mkdir()
        b_dir.mkdir()

        _make_model(a_dir, 42.0)
        _make_model(b_dir, 99.0)

        blend_models(str(a_dir), str(b_dir), str(out), alpha=1.0)
        merged = load_file(str(out / "model-00001-of-00001.safetensors"))
        assert torch.allclose(merged["layer.0.weight"], torch.full((4, 4), 99.0))

    def test_writes_metadata(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        out = tmp_path / "out"
        a_dir.mkdir()
        b_dir.mkdir()

        _make_model(a_dir, 1.0)
        _make_model(b_dir, 2.0)

        blend_models(str(a_dir), str(b_dir), str(out), alpha=0.5)

        meta = json.loads((out / "blend_metadata.json").read_text())
        assert meta["alpha"] == 0.5
        assert meta["blend_method"] == "lerp"
        assert meta["config_source"] == "a"
        assert meta["lineage_verified"] is True
        assert meta["source_model"] == "example/base-model"

    def test_copies_config(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        out = tmp_path / "out"
        a_dir.mkdir()
        b_dir.mkdir()

        _make_model(a_dir, 1.0)
        _make_model(b_dir, 2.0)

        blend_models(str(a_dir), str(b_dir), str(out))
        assert (out / "config.json").exists()

    def test_uses_selected_config_source(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        out = tmp_path / "out"
        a_dir.mkdir()
        b_dir.mkdir()
        _make_model(a_dir, 1.0, config_name="a")
        _make_model(b_dir, 2.0, config_name="b")

        blend_models(a_dir, b_dir, out, config_source="b")

        assert json.loads((out / "config.json").read_text())["model_type"] == "b"

    def test_supports_different_shard_layouts_with_matching_keys(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        out = tmp_path / "out"
        a_dir.mkdir()
        b_dir.mkdir()
        values_a = {"layer.0": 0.0, "layer.1": 2.0}
        values_b = {"layer.0": 10.0, "layer.1": 6.0}
        _make_sharded_model(a_dir, values_a, {key: "a.safetensors" for key in values_a})
        _make_sharded_model(
            b_dir,
            values_b,
            {"layer.0": "b-1.safetensors", "layer.1": "b-2.safetensors"},
        )

        blend_models(a_dir, b_dir, out, alpha=0.25)

        tensors = load_file(str(out / "a.safetensors"))
        assert torch.allclose(tensors["layer.0"], torch.full((2, 2), 2.5))
        assert torch.allclose(tensors["layer.1"], torch.full((2, 2), 3.0))

    @pytest.mark.parametrize("alpha", [-0.1, 1.1, float("inf"), float("nan")])
    def test_rejects_invalid_alpha_without_creating_output(self, tmp_path, alpha):
        from obliteratus.blend import blend_models

        with pytest.raises(ValueError, match="alpha"):
            blend_models(tmp_path / "a", tmp_path / "b", tmp_path / "out", alpha=alpha)
        assert not (tmp_path / "out").exists()

    def test_rejects_invalid_config_source(self, tmp_path):
        from obliteratus.blend import blend_models

        with pytest.raises(ValueError, match="config_source"):
            blend_models(
                tmp_path / "a",
                tmp_path / "b",
                tmp_path / "out",
                config_source="other",
            )

    def test_rejects_missing_or_extra_tensor_keys(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        a_dir.mkdir()
        b_dir.mkdir()
        _make_model(a_dir, 1.0, n_tensors=2)
        _make_model(b_dir, 2.0, n_tensors=1)

        with pytest.raises(ValueError, match="tensor keys do not match"):
            blend_models(a_dir, b_dir, tmp_path / "out")

    def test_rejects_shape_and_dtype_mismatches(self, tmp_path):
        from obliteratus.blend import blend_models

        for mismatch in ("shape", "dtype"):
            a_dir = tmp_path / f"a-{mismatch}"
            b_dir = tmp_path / f"b-{mismatch}"
            a_dir.mkdir()
            b_dir.mkdir()
            shard = "model.safetensors"
            save_file({"weight": torch.ones((2, 2))}, str(a_dir / shard))
            b_tensor = torch.ones((3, 2)) if mismatch == "shape" else torch.ones((2, 2)).double()
            save_file({"weight": b_tensor}, str(b_dir / shard))
            index = {"weight_map": {"weight": shard}}
            for directory in (a_dir, b_dir):
                (directory / "model.safetensors.index.json").write_text(json.dumps(index))
                (directory / "config.json").write_text("{}")
                (directory / "abliteration_metadata.json").write_text(
                    json.dumps({"source_model": "example/base-model"}),
                )

            with pytest.raises(ValueError, match=f"Tensor {mismatch} mismatch"):
                blend_models(a_dir, b_dir, tmp_path / f"out-{mismatch}")

    def test_rejects_non_floating_tensors(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        a_dir.mkdir()
        b_dir.mkdir()
        shard = "model.safetensors"
        index = {"weight_map": {"weight": shard}}
        for directory in (a_dir, b_dir):
            save_file({"weight": torch.ones((2, 2), dtype=torch.int64)}, str(directory / shard))
            (directory / "model.safetensors.index.json").write_text(json.dumps(index))
            (directory / "config.json").write_text("{}")
            (directory / "abliteration_metadata.json").write_text(
                json.dumps({"source_model": "example/base-model"}),
            )

        with pytest.raises(TypeError, match="non-floating"):
            blend_models(a_dir, b_dir, tmp_path / "out")

    def test_rejects_unsafe_index_shard_path(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        a_dir.mkdir()
        b_dir.mkdir()
        (a_dir / "model.safetensors.index.json").write_text(
            json.dumps({"weight_map": {"weight": "../outside.safetensors"}}),
        )
        for directory in (a_dir, b_dir):
            (directory / "abliteration_metadata.json").write_text(
                json.dumps({"source_model": "example/base-model"}),
            )

        with pytest.raises(ValueError, match="unsafe shard path"):
            blend_models(a_dir, b_dir, tmp_path / "out")

    def test_rejects_output_overlapping_a_source(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        a_dir.mkdir()
        b_dir.mkdir()

        with pytest.raises(ValueError, match="output"):
            blend_models(a_dir, b_dir, a_dir / "nested")

    def test_requires_matching_checkpoint_lineage_by_default(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        a_dir.mkdir()
        b_dir.mkdir()
        _make_model(a_dir, 1.0)
        _make_model(b_dir, 2.0)
        (b_dir / "abliteration_metadata.json").write_text(
            json.dumps({"source_model": "different/base"}),
        )

        with pytest.raises(ValueError, match="source_model values do not match"):
            blend_models(a_dir, b_dir, tmp_path / "out")

    def test_unverified_lineage_requires_explicit_opt_in(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        a_dir.mkdir()
        b_dir.mkdir()
        _make_model(a_dir, 1.0)
        _make_model(b_dir, 2.0)
        (a_dir / "abliteration_metadata.json").unlink()
        (b_dir / "abliteration_metadata.json").unlink()

        with pytest.raises(ValueError, match="allow_unverified_lineage"):
            blend_models(a_dir, b_dir, tmp_path / "blocked")

        result = blend_models(
            a_dir,
            b_dir,
            tmp_path / "allowed",
            allow_unverified_lineage=True,
        )
        assert result["lineage_verified"] is False
        assert result["source_model"] is None

    def test_failed_blend_preserves_existing_output(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        out = tmp_path / "out"
        a_dir.mkdir()
        b_dir.mkdir()
        out.mkdir()
        (out / "sentinel.txt").write_text("previous")
        _make_model(a_dir, 1.0)
        _make_model(b_dir, 2.0)
        (a_dir / "config.json").unlink()

        with pytest.raises(ValueError, match="config.json"):
            blend_models(a_dir, b_dir, out)

        assert (out / "sentinel.txt").read_text() == "previous"

    def test_successful_blend_atomically_replaces_existing_output(self, tmp_path):
        from obliteratus.blend import blend_models

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        out = tmp_path / "out"
        a_dir.mkdir()
        b_dir.mkdir()
        out.mkdir()
        (out / "stale.txt").write_text("stale")
        _make_model(a_dir, 1.0)
        _make_model(b_dir, 2.0)

        blend_models(a_dir, b_dir, out)

        assert not (out / "stale.txt").exists()
        assert (out / "blend_metadata.json").is_file()


class TestBlendSearch:
    def test_creates_multiple_blends(self, tmp_path):
        from obliteratus.blend import blend_search

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        out = tmp_path / "search"
        a_dir.mkdir()
        b_dir.mkdir()

        _make_model(a_dir, 0.0)
        _make_model(b_dir, 10.0)

        results = blend_search(str(a_dir), str(b_dir), str(out), alphas=[0.3, 0.7])

        assert len(results) == 2
        assert (out / "blend_30").exists()
        assert (out / "blend_70").exists()

    def test_rejects_empty_or_duplicate_search_ratios(self, tmp_path):
        from obliteratus.blend import blend_search

        with pytest.raises(ValueError, match="at least one"):
            blend_search(tmp_path / "a", tmp_path / "b", tmp_path / "out", alphas=[])
        with pytest.raises(ValueError, match="duplicate"):
            blend_search(tmp_path / "a", tmp_path / "b", tmp_path / "out", alphas=[0.5, 0.5])

    def test_search_propagates_config_source(self, tmp_path):
        from obliteratus.blend import blend_search

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        out = tmp_path / "out"
        a_dir.mkdir()
        b_dir.mkdir()
        _make_model(a_dir, 1.0, config_name="a")
        _make_model(b_dir, 2.0, config_name="b")

        blend_search(a_dir, b_dir, out, alphas=[0.5], config_source="b")

        config = json.loads((out / "blend_50" / "config.json").read_text())
        assert config["model_type"] == "b"


class TestCLIDispatch:
    def test_blend_dispatch(self, tmp_path):
        from obliteratus.cli import main as cli_main

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        out = tmp_path / "out"
        a_dir.mkdir()
        b_dir.mkdir()

        _make_model(a_dir, 1.0)
        _make_model(b_dir, 2.0)

        cli_main(["blend",
                   "--model-a", str(a_dir),
                   "--model-b", str(b_dir),
                   "--alpha", "0.6",
                   "--output", str(out)])

        assert (out / "blend_metadata.json").exists()

    def test_blend_dispatch_uses_requested_config_source(self, tmp_path):
        from obliteratus.cli import main as cli_main

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        out = tmp_path / "out"
        a_dir.mkdir()
        b_dir.mkdir()
        _make_model(a_dir, 1.0, config_name="a")
        _make_model(b_dir, 2.0, config_name="b")

        cli_main([
            "blend",
            "--model-a", str(a_dir),
            "--model-b", str(b_dir),
            "--config-source", "b",
            "--output", str(out),
        ])

        assert json.loads((out / "config.json").read_text())["model_type"] == "b"


class TestModuleCLI:
    def test_single_blend_main(self, tmp_path, monkeypatch, capsys):
        from obliteratus import blend

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        out = tmp_path / "out"
        a_dir.mkdir()
        b_dir.mkdir()
        _make_model(a_dir, 1.0)
        _make_model(b_dir, 2.0)
        monkeypatch.setattr(
            "sys.argv",
            [
                "obliteratus.blend",
                "--model-a", str(a_dir),
                "--model-b", str(b_dir),
                "--alpha", "0.25",
                "--output", str(out),
            ],
        )

        blend.main()

        assert "3 tensors blended at alpha=0.25" in capsys.readouterr().out

    def test_search_main(self, tmp_path, monkeypatch, capsys):
        from obliteratus import blend

        a_dir = tmp_path / "a"
        b_dir = tmp_path / "b"
        out = tmp_path / "out"
        a_dir.mkdir()
        b_dir.mkdir()
        _make_model(a_dir, 1.0)
        _make_model(b_dir, 2.0)
        monkeypatch.setattr(
            "sys.argv",
            [
                "obliteratus.blend",
                "--model-a", str(a_dir),
                "--model-b", str(b_dir),
                "--search", "0.25,0.75",
                "--output", str(out),
            ],
        )

        blend.main()

        output = capsys.readouterr().out
        assert "Created 2 blends" in output
        assert "blend_25: alpha=0.25" in output
