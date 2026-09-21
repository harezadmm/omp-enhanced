"""Fixed-membership launcher and configuration contracts for issue 59."""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import time
from dataclasses import replace

import pytest

from obliteratus.distributed.config import DistributedPreflightConfig
from obliteratus.distributed.contracts import ContractError, RuntimeContractError
from obliteratus.distributed.launcher import (
    TorchrunEnvironment,
    control_group,
)


HEX = "a" * 64


def _teardown_overrun_worker(config, launch, sink_path: str, ready) -> None:
    import obliteratus.distributed.launcher as launcher_module
    import torch.distributed as child_dist

    descriptor = os.open(sink_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.dup2(descriptor, 2)
    os.close(descriptor)
    state = {"initialized": False}
    launcher_module.validate_network_interface = lambda *args, **kwargs: None
    child_dist.is_available = lambda: True  # type: ignore[method-assign]
    child_dist.is_initialized = lambda: state["initialized"]  # type: ignore[method-assign]
    child_dist.init_process_group = (  # type: ignore[method-assign]
        lambda *args, **kwargs: state.update(initialized=True)
    )

    def delayed_native_write() -> None:
        time.sleep(config.teardown_timeout_seconds + 0.25)
        os.write(2, b"LATE_NATIVE_MARKER_FROM_TIMED_OUT_TEARDOWN\n")

    child_dist.destroy_process_group = delayed_native_write  # type: ignore[method-assign]
    ready.set()
    with control_group(config, launch):
        pass
    os._exit(99)


def _profile(tmp_path, **overrides):
    source = tmp_path / "source"
    staging = tmp_path / "staging"
    evidence = staging / ("1" * 32) / "preflight.json"
    source.mkdir(exist_ok=True)
    staging.mkdir(exist_ok=True)
    payload = {
        "schema_version": 1,
        "run": {
            "run_id": "1" * 32,
            "rendezvous_id": "2" * 32,
            "world_size": 2,
            "local_world_size": 1,
        },
        "identity": {
            "source_digest": HEX,
            "model_digest": "b" * 64,
            "tokenizer_digest": "c" * 64,
            "commit_sha": "d" * 40,
            "code_digest": "0" * 64,
        },
        "topology": {
            "tensor_parallel_size": 2,
            "coordinator_rank": 0,
            "placement_plan_digest": "e" * 64,
            "dimension_divisors": [2, 4],
        },
        "network": {
            "master_addr": "10.10.0.10",
            "master_port": 29500,
            "interface": "eth0",
            "allowed_master_cidrs": ["10.10.0.0/24"],
        },
        "source": {"path": str(source)},
        "staging": {"path": str(staging), "storage_digest": "f" * 64},
        "resources": {
            "min_free_device_memory_bytes": 1024,
            "min_free_host_memory_bytes": 2048,
            "min_free_staging_bytes": 4096,
            "max_source_files": 1000,
            "max_source_bytes": 1099511627776,
            "max_source_file_bytes": 1099511627776,
        },
        "timeouts": {
            "source_seconds": 5,
            "init_seconds": 5,
            "collective_seconds": 5,
            "teardown_seconds": 5,
        },
        "software": {
            "python": "3.12.11",
            "platform": "Linux-test",
            "machine": "x86_64",
            "torch": "2.13.0",
            "transformers": "5.15.0",
            "accelerate": "1.10.0",
            "safetensors": "0.6.2",
            "cuda": "13.0",
            "nccl": "2.28.3",
            "driver": "580.65",
        },
        "execution": {
            "device_kind": "cuda",
            "device_name": "NVIDIA Test GPU",
            "compute_capability": "10.0",
            "evidence_tier": "candidate_preflight",
            "allowed_environment_keys": [],
            "local_files_only": True,
            "trust_remote_code": False,
            "allow_runtime_install": False,
            "allow_plugins": False,
            "allow_compilation": False,
            "allow_adapters": False,
            "allow_quantization": False,
        },
        "evidence": {"path": str(evidence)},
    }
    payload.update(overrides)
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return DistributedPreflightConfig.from_file(path)


def _environment(**overrides):
    values = {
        "RANK": "0",
        "LOCAL_RANK": "0",
        "WORLD_SIZE": "2",
        "LOCAL_WORLD_SIZE": "1",
        "GROUP_RANK": "0",
        "ROLE_RANK": "0",
        "ROLE_WORLD_SIZE": "2",
        "MASTER_ADDR": "10.10.0.10",
        "MASTER_PORT": "29500",
        "TORCHELASTIC_RUN_ID": "2" * 32,
        "TORCHELASTIC_RESTART_COUNT": "0",
        "TORCHELASTIC_MAX_RESTARTS": "0",
        "OBLITERATUS_RUN_ID": "1" * 32,
        "GLOO_SOCKET_IFNAME": "eth0",
        "NCCL_SOCKET_IFNAME": "eth0",
    }
    values.update(overrides)
    return values


def test_profile_is_strict_bounded_and_order_independent(tmp_path):
    config = _profile(tmp_path)
    reordered = json.loads((tmp_path / "profile.json").read_text(encoding="utf-8"))
    (tmp_path / "profile.json").write_text(
        json.dumps(dict(reversed(list(reordered.items())))), encoding="utf-8"
    )
    assert DistributedPreflightConfig.from_file(tmp_path / "profile.json").digest == config.digest

    reordered["password"] = "do-not-echo"
    (tmp_path / "profile.json").write_text(json.dumps(reordered), encoding="utf-8")
    with pytest.raises(ContractError, match="unknown profile field"):
        DistributedPreflightConfig.from_file(tmp_path / "profile.json")


def test_profile_byte_bound_is_checked_before_json_parsing(tmp_path):
    profile = tmp_path / "profile.json"
    profile.write_bytes(b" " * (64 * 1024 + 1))
    with pytest.raises(ContractError, match="regular file"):
        DistributedPreflightConfig.from_file(profile)


@pytest.mark.parametrize(
    "field",
    [
        "RANK",
        "LOCAL_RANK",
        "WORLD_SIZE",
        "LOCAL_WORLD_SIZE",
        "GROUP_RANK",
        "ROLE_RANK",
        "ROLE_WORLD_SIZE",
        "MASTER_ADDR",
        "MASTER_PORT",
        "TORCHELASTIC_RUN_ID",
        "TORCHELASTIC_RESTART_COUNT",
        "TORCHELASTIC_MAX_RESTARTS",
        "OBLITERATUS_RUN_ID",
        "GLOO_SOCKET_IFNAME",
        "NCCL_SOCKET_IFNAME",
    ],
)
def test_torchrun_environment_requires_every_fixed_field(tmp_path, field):
    config = _profile(tmp_path)
    environ = _environment()
    del environ[field]
    with pytest.raises(ContractError, match="required torchrun environment is incomplete"):
        TorchrunEnvironment.from_environ(environ, config)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"RANK": "2"}, "rank must be smaller"),
        ({"LOCAL_RANK": "1"}, "local_rank must be smaller"),
        ({"WORLD_SIZE": "3"}, "world_size disagrees"),
        ({"ROLE_WORLD_SIZE": "1"}, "role_world_size disagrees"),
        ({"MASTER_PORT": "0"}, "master_port"),
        ({"MASTER_ADDR": "8.8.8.8"}, "master endpoint disagrees"),
        ({"MASTER_ADDR": "0.0.0.0"}, "master endpoint disagrees"),
        ({"TORCHELASTIC_RESTART_COUNT": "1"}, "restarts are forbidden"),
        ({"TORCHELASTIC_MAX_RESTARTS": "1"}, "restarts are forbidden"),
        ({"TORCHELASTIC_RUN_ID": "3" * 32}, "rendezvous_id disagrees"),
        ({"OBLITERATUS_RUN_ID": "3" * 32}, "run_id disagrees"),
        ({"GLOO_SOCKET_IFNAME": "eth1"}, "interface disagrees"),
        ({"RANK": "9" * 10000}, "unsigned decimal integer"),
    ],
)
def test_torchrun_environment_rejects_dynamic_or_unapproved_membership(
    tmp_path, overrides, message
):
    with pytest.raises(ContractError, match=message):
        TorchrunEnvironment.from_environ(_environment(**overrides), _profile(tmp_path))


def test_torchrun_environment_parses_immutable_identity(tmp_path):
    launch = TorchrunEnvironment.from_environ(_environment(), _profile(tmp_path))
    assert (launch.rank, launch.local_rank, launch.world_size) == (0, 0, 2)
    assert launch.master_endpoint_digest != "10.10.0.10"
    with pytest.raises(Exception):
        launch.rank = 1  # type: ignore[misc]


def test_control_group_always_destroys_and_uses_explicit_timeout(tmp_path, monkeypatch):
    config = _profile(tmp_path)
    launch = TorchrunEnvironment.from_environ(_environment(), config)
    calls = []
    monkeypatch.setattr(
        "obliteratus.distributed.launcher.validate_network_interface",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr("torch.distributed.is_available", lambda: True)
    monkeypatch.setattr("torch.distributed.is_initialized", lambda: bool(calls))
    monkeypatch.setattr("torch.distributed.init_process_group", lambda *a, **kw: calls.append(kw))
    monkeypatch.setattr("torch.distributed.destroy_process_group", lambda: calls.append("destroy"))
    with pytest.raises(RuntimeError, match="injected"):
        with control_group(config, launch):
            raise RuntimeError("injected")
    assert calls[0]["backend"] == "gloo"
    assert calls[0]["rank"] == 0
    assert calls[0]["world_size"] == 2
    assert calls[0]["timeout"].total_seconds() == 5
    assert calls[-1] == "destroy"


def test_control_group_teardown_failure_replaces_success(tmp_path, monkeypatch):
    config = _profile(tmp_path)
    launch = TorchrunEnvironment.from_environ(_environment(), config)
    state = {"initialized": False}
    monkeypatch.setattr(
        "obliteratus.distributed.launcher.validate_network_interface",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr("torch.distributed.is_available", lambda: True)
    monkeypatch.setattr("torch.distributed.is_initialized", lambda: state["initialized"])
    monkeypatch.setattr(
        "torch.distributed.init_process_group",
        lambda *args, **kwargs: state.update(initialized=True),
    )

    def fail_destroy():
        raise RuntimeError("secret-bearing backend diagnostic")

    monkeypatch.setattr("torch.distributed.destroy_process_group", fail_destroy)
    with pytest.raises(ContractError, match="control group teardown failed"):
        with control_group(config, launch):
            pass


def test_control_group_refuses_unbound_interface_before_backend_init(tmp_path, monkeypatch):
    config = _profile(tmp_path)
    launch = TorchrunEnvironment.from_environ(_environment(), config)
    calls = []
    monkeypatch.setattr("torch.distributed.is_available", lambda: True)
    monkeypatch.setattr("torch.distributed.is_initialized", lambda: False)
    monkeypatch.setattr(
        "torch.distributed.init_process_group", lambda *args, **kwargs: calls.append(kwargs)
    )

    def refuse(*args, **kwargs):
        raise RuntimeContractError(
            "LMS_NETWORK_PROFILE_DENIED", "configured interface is unavailable"
        )

    monkeypatch.setattr("obliteratus.distributed.launcher.validate_network_interface", refuse)
    with pytest.raises(RuntimeContractError) as error:
        with control_group(config, launch):
            pass
    assert error.value.code == "LMS_NETWORK_PROFILE_DENIED"
    assert calls == []


@pytest.mark.parametrize("phase", ["init", "collective", "timeout", "teardown"])
def test_control_group_suppresses_native_fd2_and_emits_only_stable_code(
    tmp_path, monkeypatch, capfd, phase
):
    config = _profile(tmp_path)
    launch = TorchrunEnvironment.from_environ(_environment(), config)
    state = {"initialized": False}
    monkeypatch.setattr(
        "obliteratus.distributed.launcher.validate_network_interface",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr("torch.distributed.is_available", lambda: True)
    monkeypatch.setattr("torch.distributed.is_initialized", lambda: state["initialized"])

    def initialize(*args, **kwargs):
        if phase in {"init", "timeout"}:
            os.write(2, b"secret-bearing native backend diagnostic\n")
        if phase == "timeout":
            raise TimeoutError("raw private endpoint")
        state["initialized"] = True

    def destroy():
        if phase == "teardown":
            os.write(2, b"secret-bearing native backend diagnostic\n")
        state["initialized"] = False

    monkeypatch.setattr("torch.distributed.init_process_group", initialize)
    monkeypatch.setattr("torch.distributed.destroy_process_group", destroy)
    with pytest.raises(RuntimeContractError) as error:
        with control_group(config, launch):
            if phase == "collective":
                os.write(2, b"secret-bearing native backend diagnostic\n")
    assert error.value.code == "LMS_DIAGNOSTIC_REDACTION_FAILED"
    assert "secret-bearing" not in str(error.value)
    assert "secret-bearing" not in capfd.readouterr().err


def test_teardown_overrun_terminates_worker_before_late_native_write(tmp_path):
    config = replace(_profile(tmp_path), teardown_timeout_seconds=1)
    launch = TorchrunEnvironment.from_environ(_environment(), config)
    sink = tmp_path / "worker-stderr.bin"
    context = mp.get_context("spawn")
    ready = context.Event()
    process = context.Process(
        target=_teardown_overrun_worker,
        args=(config, launch, str(sink), ready),
    )
    process.start()
    assert ready.wait(20), "teardown-overrun worker did not finish cold startup"
    started = time.monotonic()
    process.join(3)
    elapsed = time.monotonic() - started
    if process.is_alive():
        process.terminate()
        process.join(2)
        pytest.fail("teardown-overrun worker did not terminate within its bound")
    assert process.exitcode == 70
    assert elapsed < 3
    assert sink.read_bytes() == b""


def test_config_rejects_weakened_execution_policy(tmp_path):
    config = _profile(tmp_path)
    with pytest.raises(ContractError, match="trust_remote_code must remain false"):
        replace(config, trust_remote_code=True).validate()


@pytest.mark.parametrize("name", ["HF_TOKEN", "AWS_ACCESS_KEY_ID", "HTTPS_PROXY"])
def test_secret_or_proxy_environment_is_rejected_without_echo(tmp_path, name):
    environ = _environment()
    environ[name] = "private-value"
    with pytest.raises(ContractError, match="secret-bearing") as error:
        TorchrunEnvironment.from_environ(environ, _profile(tmp_path))
    assert "private-value" not in str(error.value)


@pytest.mark.parametrize("address", ["8.8.8.8", "0.0.0.0", "224.0.0.1"])
def test_profiled_endpoint_must_still_be_private_and_allowlisted(tmp_path, address):
    network = {
        "master_addr": address,
        "master_port": 29500,
        "interface": "eth0",
        "allowed_master_cidrs": [f"{address}/32"],
    }
    with pytest.raises(ContractError, match="private"):
        config = _profile(tmp_path, network=network)
        TorchrunEnvironment.from_environ(_environment(MASTER_ADDR=address), config)
