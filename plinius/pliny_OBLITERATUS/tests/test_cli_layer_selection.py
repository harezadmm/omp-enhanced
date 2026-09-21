"""CPU-safe contract tests for the ``--layer-selection`` CLI override.

``AbliterationPipeline`` has accepted ``layer_selection`` since layer selection
was made configurable, and ``_distill`` dispatches on six distinct values, but no
command exposed it — reaching anything other than a method's built-in default
required constructing the pipeline in Python. These tests pin the flag to the
values the implementation actually dispatches on, so the two cannot drift.
"""

from __future__ import annotations

import re
import shlex

import pytest

from obliteratus import cli
from obliteratus.remote import RemoteConfig, RemoteRunner

# The values `AbliterationPipeline._distill` branches on. "knee_cosmic" is the
# implicit default (the `else` arm) and is spelled out here so selecting it
# explicitly is possible rather than only reachable by omission.
EXPECTED_CHOICES = {"knee_cosmic", "knee", "all", "all_except_first", "middle60", "top_k"}


@pytest.mark.parametrize("command", ["obliterate", "abliterate"])
def test_layer_selection_rejects_an_unknown_strategy(command, monkeypatch):
    """An unrecognised value must fail at parse time, not fall through silently.

    `_distill` treats every unknown value as the default `knee_cosmic` arm, so
    without constrained choices a typo would run a different strategy than the
    one asked for and report success.
    """
    monkeypatch.setattr(cli, "_cmd_abliterate", lambda _args: None)

    with pytest.raises(SystemExit) as excinfo:
        cli.main([command, "org/model", "--layer-selection", "not-a-strategy"])

    assert excinfo.value.code == 2


@pytest.mark.parametrize("command", ["obliterate", "abliterate"])
@pytest.mark.parametrize("strategy", sorted(EXPECTED_CHOICES))
def test_layer_selection_parses_and_reaches_the_command(command, strategy, monkeypatch):
    captured = {}
    monkeypatch.setattr(cli, "_cmd_abliterate", lambda args: captured.update(vars(args)))

    cli.main([command, "org/model", "--layer-selection", strategy])

    assert captured["layer_selection"] == strategy


def test_layer_selection_defaults_to_none_so_the_method_keeps_its_own_setting(monkeypatch):
    """Omitting the flag must not override the method's configured strategy.

    The pipeline resolves `layer_selection or method_cfg[...]`, so passing
    anything other than None here would silently flatten every method's default.
    """
    captured = {}
    monkeypatch.setattr(cli, "_cmd_abliterate", lambda args: captured.update(vars(args)))

    cli.main(["obliterate", "org/model"])

    assert captured["layer_selection"] is None


def test_self_improve_accepts_the_same_strategies(monkeypatch, tmp_path):
    captured = {}
    monkeypatch.setattr(cli, "_cmd_self_improve", lambda args: captured.update(vars(args)))

    cli.main([
        "self-improve", "org/model",
        "--audit", str(tmp_path / "audit.json"),
        "--output-dir", str(tmp_path / "out"),
        "--layer-selection", "all",
    ])

    assert captured["layer_selection"] == "all"


def test_remote_command_forwards_layer_selection():
    runner = RemoteRunner(RemoteConfig(host="example.invalid", user="operator"))

    command = runner.build_obliterate_command(
        "org/model",
        method="optimized",
        layer_selection="all",
    )

    tokens = shlex.split(command)
    assert "--layer-selection" in tokens
    assert tokens[tokens.index("--layer-selection") + 1] == "all"


def test_remote_command_omits_the_flag_when_unset():
    runner = RemoteRunner(RemoteConfig(host="example.invalid", user="operator"))

    command = runner.build_obliterate_command("org/model", method="optimized")

    assert "--layer-selection" not in shlex.split(command)


def test_every_offered_strategy_is_one_distill_actually_dispatches_on():
    """Guard against the flag and the implementation drifting apart.

    A choice the CLI offers but `_distill` does not branch on would fall into the
    default arm and silently run `knee_cosmic` instead — the failure this flag
    exists to make impossible.
    """
    import inspect

    from obliteratus.abliterate import AbliterationPipeline

    source = inspect.getsource(AbliterationPipeline._distill)

    # knee_cosmic is the implicit `else` arm and so has no equality branch.
    for strategy in sorted(EXPECTED_CHOICES - {"knee_cosmic"}):
        assert f'selection_method == "{strategy}"' in source, (
            f"CLI offers {strategy!r} but _distill has no branch for it"
        )

    branches = set(re.findall(r'selection_method == "([a-z_0-9]+)"', source))
    assert branches | {"knee_cosmic"} == EXPECTED_CHOICES, (
        f"_distill dispatches on {branches | {'knee_cosmic'}}, CLI offers {EXPECTED_CHOICES}"
    )


@pytest.mark.parametrize("strategy", [None, "all", "middle60"])
def test_remote_cli_preserves_override_and_method_default(strategy, monkeypatch):
    from unittest.mock import Mock

    runner = Mock()
    runner.run_obliterate.return_value = "result"
    monkeypatch.setattr(cli, "_make_remote_runner", lambda args: runner)
    argv = ["obliterate", "org/model", "--remote", "operator@example.invalid",
            "--method", "optimized"]
    if strategy is not None:
        argv += ["--layer-selection", strategy]

    cli.main(argv)

    forwarded = runner.run_obliterate.call_args.kwargs
    assert forwarded["method"] == "optimized"
    if strategy is None:
        assert "layer_selection" not in forwarded
    else:
        assert forwarded["layer_selection"] == strategy
