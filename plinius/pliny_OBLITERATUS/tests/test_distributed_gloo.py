"""Two-process CPU/Gloo semantic and failure tests for issue 58."""

from __future__ import annotations

import hashlib
import multiprocessing as mp
import os
import socket
import time
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from queue import Empty
from typing import Any

import pytest
import torch
import torch.distributed as dist

from obliteratus.analysis.numerical_contracts import project_weight_against_direction
from obliteratus.distributed.config import DistributedPreflightConfig
from obliteratus.distributed.consensus import (
    gloo_all_gather_records,
    require_consensus_digest,
    require_record_consensus,
    unanimous_vote,
)
from obliteratus.distributed.contracts import (
    ContractError,
    LogicalPlacement,
    PlacementKind,
    RunIdentity,
    RuntimeStage,
    Vote,
)
from obliteratus.distributed.evidence import read_evidence, read_stage_message
from obliteratus.distributed.numerical import distributed_project_weight
from obliteratus.distributed.launcher import TorchrunEnvironment
from obliteratus.distributed.preflight import (
    LocalSnapshot,
    SourceIdentity,
    execute_preflight,
    run_preflight,
)


WORLD_SIZE = 2


def _preflight_config(root: Path) -> DistributedPreflightConfig:
    root.joinpath("staging").mkdir(exist_ok=True)
    software = (
        ("accelerate", "test"),
        ("cuda", "unavailable"),
        ("driver", "unavailable"),
        ("machine", "test"),
        ("nccl", "unavailable"),
        ("platform", "test"),
        ("python", "test"),
        ("safetensors", "test"),
        ("torch", "test"),
        ("transformers", "test"),
    )
    return DistributedPreflightConfig(
        run_id="1" * 32,
        rendezvous_id="2" * 32,
        world_size=2,
        local_world_size=1,
        source_digest="a" * 64,
        model_digest="b" * 64,
        tokenizer_digest="c" * 64,
        commit_sha="d" * 40,
        code_digest="0" * 64,
        tensor_parallel_size=2,
        coordinator_rank=0,
        placement_plan_digest="e" * 64,
        dimension_divisors=(2, 4),
        master_addr="10.10.0.10",
        master_port=29500,
        network_interface="eth0",
        allowed_master_cidrs=("10.10.0.0/24",),
        source_path=root / "source",
        staging_path=root / "staging",
        storage_digest="f" * 64,
        min_free_device_memory_bytes=1,
        min_free_host_memory_bytes=1,
        min_free_staging_bytes=1,
        max_source_files=1000,
        max_source_bytes=1024,
        max_source_file_bytes=1024,
        source_timeout_seconds=2,
        init_timeout_seconds=2,
        collective_timeout_seconds=2,
        teardown_timeout_seconds=2,
        software_versions=software,
        device_kind="cpu",
        device_name="cpu",
        compute_capability="none",
        evidence_tier="protocol_cpu",
        allowed_environment_keys=(),
        local_files_only=True,
        trust_remote_code=False,
        allow_runtime_install=False,
        allow_plugins=False,
        allow_compilation=False,
        allow_adapters=False,
        allow_quantization=False,
        evidence_path=root / "staging" / ("1" * 32) / "preflight.json",
        digest="9" * 64,
    ).validate()


class _FixedProbes:
    def __init__(self, rank: int, software: tuple[tuple[str, str], ...]):
        self.rank = rank
        self.software = software

    def collect(self, config, launch):
        return LocalSnapshot(
            host_identity=f"host-{self.rank}",
            device_identity=f"cpu-{self.rank}",
            device_name="cpu",
            compute_capability="none",
            device_kind="cpu",
            total_device_memory_bytes=8192,
            free_device_memory_bytes=4096,
            total_host_memory_bytes=16384,
            free_host_memory_bytes=8192,
            free_staging_bytes=8192,
            storage_identity=config.storage_digest,
            source=SourceIdentity(
                config.source_digest,
                config.model_digest,
                config.tokenizer_digest,
                2,
                2,
            ),
            software_versions=self.software,
            commit_sha=config.commit_sha,
            code_digest=config.code_digest,
        )


def _execute_worker(
    rank: int,
    root_text: str,
    mode: str,
    port: int,
    queue: mp.Queue,
) -> None:
    root = Path(root_text)
    config = replace(
        _preflight_config(root),
        master_addr="127.0.0.1",
        master_port=port,
        init_timeout_seconds=10,
        collective_timeout_seconds=10,
    )
    launch = TorchrunEnvironment(
        rank=rank,
        local_rank=0,
        world_size=2,
        local_world_size=1,
        group_rank=rank,
        role_rank=rank,
        role_world_size=2,
        master_endpoint_digest="8" * 64,
        run_id=config.run_id,
        rendezvous_id=config.rendezvous_id,
        network_interface=config.network_interface,
    )
    os.environ["MASTER_ADDR"] = config.master_addr
    os.environ["MASTER_PORT"] = str(config.master_port)
    probes = _FixedProbes(rank, config.software_versions)
    if mode == "identity_failure" and rank == 1:
        original_collect = probes.collect

        def collect_with_wrong_identity(candidate_config, candidate_launch):
            snapshot = original_collect(candidate_config, candidate_launch)
            return replace(
                snapshot,
                source=replace(snapshot.source, source_digest="7" * 64),
            )

        probes.collect = collect_with_wrong_identity  # type: ignore[method-assign]
    if mode == "storage_failure" and rank == 1:
        original_collect = probes.collect

        def collect_with_wrong_storage(candidate_config, candidate_launch):
            snapshot = original_collect(candidate_config, candidate_launch)
            return replace(snapshot, storage_identity="7" * 64)

        probes.collect = collect_with_wrong_storage  # type: ignore[method-assign]
    if mode == "resource_failure" and rank == 1:
        original_collect = probes.collect

        def collect_without_headroom(candidate_config, candidate_launch):
            snapshot = original_collect(candidate_config, candidate_launch)
            return replace(snapshot, free_device_memory_bytes=0)

        probes.collect = collect_without_headroom  # type: ignore[method-assign]
    if mode == "commit_failure" and rank == 1:
        original_collect = probes.collect

        def collect_with_wrong_commit(candidate_config, candidate_launch):
            snapshot = original_collect(candidate_config, candidate_launch)
            return replace(snapshot, commit_sha="7" * 40)

        probes.collect = collect_with_wrong_commit  # type: ignore[method-assign]
    if mode == "code_failure" and rank == 1:
        original_collect = probes.collect

        def collect_with_wrong_code(candidate_config, candidate_launch):
            snapshot = original_collect(candidate_config, candidate_launch)
            return replace(snapshot, code_digest="7" * 64)

        probes.collect = collect_with_wrong_code  # type: ignore[method-assign]
    if mode == "stage_timeout":

        def collect_after_timeout(candidate_config, candidate_launch):
            del candidate_config, candidate_launch
            raise TimeoutError("secret-bearing timeout detail")

        probes.collect = collect_after_timeout  # type: ignore[method-assign]
    if mode == "cancelled":

        def collect_after_cancel(candidate_config, candidate_launch):
            del candidate_config, candidate_launch
            raise KeyboardInterrupt

        probes.collect = collect_after_cancel  # type: ignore[method-assign]
    if mode == "native_stderr":
        original_collect = probes.collect

        def collect_with_native_diagnostic(candidate_config, candidate_launch):
            os.write(2, b"secret-bearing native child diagnostic\n")
            return original_collect(candidate_config, candidate_launch)

        probes.collect = collect_with_native_diagnostic  # type: ignore[method-assign]
    if mode == "rank_exception" and rank == 1:

        def collect_after_error(candidate_config, candidate_launch):
            del candidate_config, candidate_launch
            raise RuntimeError("secret-bearing rank exception")

        probes.collect = collect_after_error  # type: ignore[method-assign]
    if mode == "execute_hang" and rank == 1:
        original_collect = probes.collect

        def collect_after_hang(candidate_config, candidate_launch):
            time.sleep(60)
            return original_collect(candidate_config, candidate_launch)

        probes.collect = collect_after_hang  # type: ignore[method-assign]
    if mode == "execute_early_exit" and rank == 1:

        def exit_before_attestation(candidate_config, candidate_launch):
            del candidate_config, candidate_launch
            os._exit(17)

        probes.collect = exit_before_attestation  # type: ignore[method-assign]

    import obliteratus.distributed.launcher as launcher_module
    import obliteratus.distributed.preflight as preflight_module

    original_network_validator = launcher_module.validate_network_interface
    original_writer = preflight_module.write_stage_message
    original_destroy = dist.destroy_process_group
    launcher_module.validate_network_interface = lambda *args, **kwargs: None
    if mode == "evidence_failure" and rank == 0:

        def fail_prepared(path, evidence):
            if Path(path).name == ".preflight.prepared.stage.json":
                raise OSError("injected secret-bearing sink failure")
            return original_writer(path, evidence)

        preflight_module.write_stage_message = fail_prepared
    if mode == "teardown_failure" and rank == 1:

        def fail_destroy():
            raise RuntimeError("injected secret-bearing teardown failure")

        dist.destroy_process_group = fail_destroy  # type: ignore[method-assign]
    try:
        evidence = execute_preflight(config, launch, probes=probes)
        queue.put((rank, "ok", (evidence.result, evidence.error_code)))
    except Exception as exc:
        queue.put((rank, "error", (getattr(exc, "code", None), str(exc))))
    finally:
        launcher_module.validate_network_interface = original_network_validator
        preflight_module.write_stage_message = original_writer
        dist.destroy_process_group = original_destroy  # type: ignore[method-assign]
        if dist.is_available() and dist.is_initialized():
            original_destroy()


def _run_execute_workers(tmp_path: Path, mode: str, *, timeout: float = 35.0):
    context = mp.get_context("spawn")
    queue = context.Queue()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.close()
    processes = [
        context.Process(
            target=_execute_worker,
            args=(rank, str(tmp_path), mode, port, queue),
        )
        for rank in range(WORLD_SIZE)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout)
        if process.is_alive():
            process.terminate()
            process.join(5)
            pytest.fail(f"{mode} execute worker {process.pid} did not terminate")
        assert process.exitcode == 0
    results = sorted(queue.get(timeout=2) for _ in range(WORLD_SIZE))
    queue.close()
    queue.join_thread()
    return results


def _run_execute_disruption(
    tmp_path: Path,
    mode: str,
    *,
    ranks: tuple[int, ...] = (0, 1),
    timeout: float = 40.0,
):
    context = mp.get_context("spawn")
    queue = context.Queue()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.close()
    processes = [
        context.Process(
            target=_execute_worker,
            args=(rank, str(tmp_path), mode, port, queue),
        )
        for rank in ranks
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout)
        if process.is_alive():
            process.terminate()
            process.join(5)
            pytest.fail(f"{mode} execute worker {process.pid} did not terminate")
    results = [queue.get(timeout=2)]
    queue.close()
    queue.join_thread()
    return sorted(results), tuple(process.exitcode for process in processes)


def _placement(kind: PlacementKind, rank: int, *, direction_axis: int = 1) -> LogicalPlacement:
    shard_dim = (
        None
        if kind is PlacementKind.REPLICATED
        else (0 if kind is PlacementKind.COLUMN_WISE else 1)
    )
    global_shape = (4, 6) if direction_axis == 0 else (4, 4)
    shard_size = 0 if shard_dim is None else global_shape[shard_dim] // WORLD_SIZE
    start, end = (0, 0) if shard_dim is None else (rank * shard_size, (rank + 1) * shard_size)
    return LogicalPlacement(
        logical_name="model.layers.0.proj.weight",
        global_shape=global_shape,
        dtype="float64",
        kind=kind,
        rank=rank,
        world_size=WORLD_SIZE,
        direction_axis=direction_axis,
        shard_dim=shard_dim,
        shard_start=start,
        shard_end=end,
    )


def _full_inputs(transposed: bool = False) -> tuple[torch.Tensor, torch.Tensor]:
    shape = (4, 6) if transposed else (4, 4)
    element_count = shape[0] * shape[1]
    weight = torch.arange(1, element_count + 1, dtype=torch.float64).reshape(shape)
    weight = (weight - (element_count + 1) / 2) / 7.0
    return weight, torch.tensor((1.0, -2.0, 0.5, 3.0), dtype=torch.float64)


def _projection_payload(rank: int, mode: str) -> dict[str, Any]:
    transposed = mode.startswith("transposed")
    full_weight, direction = _full_inputs(transposed)
    if mode == "column":
        placement = _placement(PlacementKind.COLUMN_WISE, rank)
        local_weight = full_weight[rank * 2 : (rank + 1) * 2]
    elif mode == "row":
        placement = _placement(PlacementKind.ROW_WISE, rank)
        local_weight = full_weight[:, rank * 2 : (rank + 1) * 2]
    elif mode == "transposed_column":
        placement = _placement(PlacementKind.COLUMN_WISE, rank, direction_axis=0)
        local_weight = full_weight[rank * 2 : (rank + 1) * 2]
    elif mode == "transposed_row":
        placement = _placement(PlacementKind.ROW_WISE, rank, direction_axis=0)
        local_weight = full_weight[:, rank * 3 : (rank + 1) * 3]
    elif mode in {"nonfinite", "zero_direction", "zero_weight", "column_no_norm"}:
        placement = _placement(PlacementKind.COLUMN_WISE, rank)
        local_weight = full_weight[rank * 2 : (rank + 1) * 2].clone()
    elif mode == "replicated":
        placement = _placement(PlacementKind.REPLICATED, rank)
        local_weight = full_weight.clone()
    else:
        raise AssertionError(f"unknown projection mode {mode}")
    if mode == "nonfinite" and rank == 1:
        local_weight[0, 0] = float("nan")
    if mode == "zero_direction":
        direction = torch.zeros_like(direction)
    if mode == "zero_weight":
        local_weight.zero_()
    result = distributed_project_weight(
        local_weight,
        direction,
        placement,
        norm_preserve=mode != "column_no_norm",
        regularization=0.2,
        projection_row_fraction=0.5,
    )
    return {
        "weight": result.weight.tolist(),
        "projected": result.projected,
        "coefficient_norm_sq": result.coefficient_norm_sq,
        "layout": result.layout,
    }


def _validation_messages(rank: int) -> list[str]:
    placement = _placement(PlacementKind.COLUMN_WISE, rank)
    weight = _full_inputs()[0][rank * 2 : (rank + 1) * 2]
    direction = _full_inputs()[1]
    cases: tuple[tuple[torch.Tensor, object, dict[str, Any], str], ...] = (
        (weight[:1], direction, {}, "local weight shape"),
        (torch.ones_like(weight, dtype=torch.int64), direction, {}, "floating-point"),
        (weight.float(), direction, {}, "weight dtype"),
        (weight, object(), {}, "direction does not match"),
        (weight, direction[:3], {}, "direction does not match"),
        (weight, torch.ones(4, dtype=torch.int64), {}, "direction does not match"),
        (weight, direction, {"regularization": True}, "finite number"),
        (weight, direction, {"regularization": 2.0}, "in [0, 1]"),
        (weight, direction, {"projection_row_fraction": False}, "finite number"),
        (weight, direction, {"projection_row_fraction": 0.0}, "in (0, 1]"),
        (weight, direction, {"max_norm_ratio": True}, "positive and finite"),
    )
    messages = []
    for candidate_weight, candidate_direction, kwargs, expected in cases:
        try:
            distributed_project_weight(
                candidate_weight,
                candidate_direction,  # type: ignore[arg-type]
                placement,
                **kwargs,
            )
        except ContractError as exc:
            assert expected in str(exc)
            messages.append(str(exc))
        else:
            raise AssertionError(f"validation case unexpectedly passed: {expected}")
    return messages


def _worker(rank: int, init_file: str, mode: str, queue: mp.Queue) -> None:
    try:
        dist.init_process_group(
            "gloo",
            init_method=f"file://{init_file}",
            rank=rank,
            world_size=WORLD_SIZE,
            timeout=timedelta(seconds=5),
        )
        if mode == "success_matrix":
            records = gloo_all_gather_records({"rank": rank}, capacity=64)
            digest = hashlib.sha256(b"same").hexdigest()
            agreed = require_consensus_digest(digest)
            vote = unanimous_vote(3, True)
            payload: dict[str, Any] = {
                "records": ([item.decode() for item in records], agreed, vote),
                "vote_no": unanimous_vote(4, rank == 0),
            }
            for projection_mode in (
                "column",
                "row",
                "replicated",
                "transposed_column",
                "transposed_row",
                "nonfinite",
                "zero_direction",
                "zero_weight",
                "column_no_norm",
            ):
                payload[projection_mode] = _projection_payload(rank, projection_mode)
            payload["validation"] = _validation_messages(rank)
            queue.put((rank, "ok", payload))
        elif mode == "digest_mismatch":
            digest = hashlib.sha256(f"rank-{rank}".encode()).hexdigest()
            require_consensus_digest(digest)
            queue.put((rank, "unexpected", None))
        elif mode == "identity_mismatch":
            identity = RunIdentity(
                run_id="1" * 32,
                config_digest=str(rank + 1) * 64,
                source_digest="a" * 64,
                model_digest="b" * 64,
                tokenizer_digest="c" * 64,
                commit_sha="d" * 40,
                world_size=WORLD_SIZE,
            )
            require_record_consensus(identity)
            queue.put((rank, "unexpected", None))
        elif mode == "stale_sequence":
            unanimous_vote(rank, True)
            queue.put((rank, "unexpected", None))
        elif mode == "placement_disagreement":
            if rank == 0:
                placement = _placement(PlacementKind.COLUMN_WISE, rank)
                weight = _full_inputs()[0][:2]
            else:
                placement = _placement(PlacementKind.ROW_WISE, rank)
                weight = _full_inputs()[0][:, 2:]
            distributed_project_weight(weight, _full_inputs()[1], placement)
            queue.put((rank, "unexpected", None))
        elif mode == "placement_name_disagreement":
            placement = _placement(PlacementKind.COLUMN_WISE, rank)
            if rank == 1:
                placement = replace(placement, logical_name="model.layers.1.proj.weight")
            distributed_project_weight(
                _full_inputs()[0][rank * 2 : (rank + 1) * 2], _full_inputs()[1], placement
            )
            queue.put((rank, "unexpected", None))
        elif mode == "one_rank_error":
            if rank == 1:
                raise RuntimeError("injected rank error")
            gloo_all_gather_records({"rank": rank}, capacity=64)
            queue.put((rank, "unexpected", None))
        elif mode == "early_exit":
            if rank == 1:
                queue.put((rank, "exited", None))
                return
            gloo_all_gather_records({"rank": rank}, capacity=64)
            queue.put((rank, "unexpected", None))
        elif mode == "hang":
            if rank == 1:
                time.sleep(7)
            gloo_all_gather_records({"rank": rank}, capacity=64)
            queue.put((rank, "unexpected", None))
        elif mode == "preflight_success":
            config = _preflight_config(Path(init_file).parent)
            launch = TorchrunEnvironment(
                rank=rank,
                local_rank=0,
                world_size=2,
                local_world_size=1,
                group_rank=rank,
                role_rank=rank,
                role_world_size=2,
                master_endpoint_digest="8" * 64,
                run_id=config.run_id,
                rendezvous_id=config.rendezvous_id,
                network_interface=config.network_interface,
            )
            result = run_preflight(
                config,
                launch,
                probes=_FixedProbes(rank, config.software_versions),
            )
            queue.put(
                (
                    rank,
                    "ok",
                    {
                        "accepted": len(result.attestations),
                        "identity_digest": result.identity_digest,
                        "backend": result.topology.backend,
                    },
                )
            )
        else:
            raise AssertionError(f"unknown worker mode {mode}")
    except Exception as exc:
        queue.put((rank, "error", (type(exc).__name__, str(exc))))
    finally:
        if dist.is_available() and dist.is_initialized():
            dist.destroy_process_group()


def _run_workers(tmp_path: Path, mode: str, *, timeout: float = 30.0):
    context = mp.get_context("spawn")
    queue = context.Queue()
    init_file = tmp_path / f"{mode}.rendezvous"
    processes = [
        context.Process(target=_worker, args=(rank, str(init_file), mode, queue))
        for rank in range(WORLD_SIZE)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout)
        if process.is_alive():
            process.terminate()
            process.join(5)
            pytest.fail(f"{mode} worker {process.pid} did not terminate")
        assert process.exitcode == 0

    results = []
    for _ in range(WORLD_SIZE):
        try:
            results.append(queue.get(timeout=2))
        except Empty:
            pytest.fail(f"{mode} did not report one result per rank")
    queue.close()
    queue.join_thread()
    return sorted(results)


@pytest.fixture(scope="module")
def success_results(tmp_path_factory):
    return _run_workers(
        tmp_path_factory.mktemp("distributed-success"), "success_matrix", timeout=20.0
    )


def _case_results(success_results, key: str):
    return [(rank, status, payload[key]) for rank, status, payload in success_results]


def test_bounded_records_digest_and_unanimous_vote_succeed(success_results):
    results = _case_results(success_results, "records")
    assert [status for _rank, status, _payload in results] == ["ok", "ok"]
    expected_records = ['{"rank":0}', '{"rank":1}']
    for _rank, _status, payload in results:
        records, digest, vote = payload
        assert records == expected_records
        assert digest == hashlib.sha256(b"same").hexdigest()
        assert vote is True


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        ("digest_mismatch", "rank digests disagree"),
        ("identity_mismatch", "rank digests disagree"),
        ("stale_sequence", "rank vote sequences disagree"),
        ("placement_disagreement", "rank placement metadata disagrees"),
        ("placement_name_disagreement", "rank digests disagree"),
    ],
)
def test_rank_disagreement_fails_on_every_participant(tmp_path, mode, message):
    results = _run_workers(tmp_path, mode)
    assert [status for _rank, status, _payload in results] == ["error", "error"]
    assert all(message in payload[1] for _rank, _status, payload in results)


def test_one_negative_vote_aborts_unanimity_for_every_rank(success_results):
    results = _case_results(success_results, "vote_no")
    assert [payload for _rank, status, payload in results if status == "ok"] == [False, False]


@pytest.mark.parametrize("mode", ["one_rank_error", "early_exit", "hang"])
def test_rank_exit_or_timeout_terminates_and_reaps_the_worker_group(tmp_path, mode):
    results = _run_workers(tmp_path, mode)
    statuses = {rank: status for rank, status, _payload in results}
    assert statuses[0] == "error"
    assert statuses[1] in {"error", "exited"}


@pytest.mark.parametrize(
    ("mode", "concat_dim", "transposed"),
    [
        ("column", 0, False),
        ("row", 1, False),
        ("transposed_column", 0, True),
        ("transposed_row", 1, True),
    ],
)
def test_distributed_shards_match_complete_tensor_projection(
    success_results,
    mode,
    concat_dim,
    transposed,
):
    results = _case_results(success_results, mode)
    assert all(status == "ok" for _rank, status, _payload in results)
    shards = [
        torch.tensor(payload["weight"], dtype=torch.float64) for _rank, _status, payload in results
    ]
    actual = torch.cat(shards, dim=concat_dim)
    full_weight, direction = _full_inputs(transposed)
    expected = project_weight_against_direction(
        full_weight,
        direction,
        norm_preserve=True,
        regularization=0.2,
        projection_row_fraction=0.5,
    )
    torch.testing.assert_close(actual, expected.weight, rtol=1e-10, atol=1e-10)
    assert all(payload["projected"] is True for _rank, _status, payload in results)
    assert all(payload["layout"] == expected.layout for _rank, _status, payload in results)
    assert all(
        payload["coefficient_norm_sq"] == pytest.approx(expected.coefficient_norm_sq)
        for _rank, _status, payload in results
    )


def test_replicated_projection_is_identical_on_every_rank(success_results):
    results = _case_results(success_results, "replicated")
    weights = [
        torch.tensor(payload["weight"], dtype=torch.float64)
        for _rank, status, payload in results
        if status == "ok"
    ]
    assert len(weights) == WORLD_SIZE
    torch.testing.assert_close(weights[0], weights[1], rtol=0, atol=0)
    full_weight, direction = _full_inputs()
    expected = project_weight_against_direction(
        full_weight,
        direction,
        norm_preserve=True,
        regularization=0.2,
        projection_row_fraction=0.5,
    )
    torch.testing.assert_close(weights[0], expected.weight, rtol=1e-10, atol=1e-10)


def test_nonfinite_value_on_one_rank_prevents_mutation_everywhere(success_results):
    results = _case_results(success_results, "nonfinite")
    assert all(status == "ok" for _rank, status, _payload in results)
    assert all(payload["projected"] is False for _rank, _status, payload in results)


@pytest.mark.parametrize("mode", ["zero_direction", "zero_weight"])
def test_degenerate_global_inputs_are_deterministic(success_results, mode):
    results = _case_results(success_results, mode)
    assert all(status == "ok" for _rank, status, _payload in results)
    expected_projected = mode == "zero_weight"
    assert all(payload["projected"] is expected_projected for _rank, _status, payload in results)


def test_projection_without_norm_preservation_reports_no_global_norm(success_results):
    results = _case_results(success_results, "column_no_norm")
    assert all(status == "ok" for _rank, status, _payload in results)
    actual = torch.cat(
        [
            torch.tensor(payload["weight"], dtype=torch.float64)
            for _rank, _status, payload in results
        ],
        dim=0,
    )
    full_weight, direction = _full_inputs()
    expected = project_weight_against_direction(
        full_weight,
        direction,
        norm_preserve=False,
        regularization=0.2,
        projection_row_fraction=0.5,
    )
    torch.testing.assert_close(actual, expected.weight, rtol=1e-10, atol=1e-10)
    assert all(payload["coefficient_norm_sq"] == 0.0 for _rank, _status, payload in results)


def test_invalid_numerical_requests_fail_closed_on_both_ranks(success_results):
    results = _case_results(success_results, "validation")
    assert [status for _rank, status, _payload in results] == ["ok", "ok"]
    assert all(len(payload) == 11 for _rank, _status, payload in results)


def test_real_gloo_preflight_admits_the_complete_fixed_world(tmp_path):
    results = _run_workers(tmp_path, "preflight_success")
    assert [status for _rank, status, _payload in results] == ["ok", "ok"]
    assert {payload["accepted"] for _rank, _status, payload in results} == {2}
    assert len({payload["identity_digest"] for _rank, _status, payload in results}) == 1
    assert {payload["backend"] for _rank, _status, payload in results} == {"gloo"}


def test_execute_preflight_publishes_success_only_after_all_teardown_acknowledgements(
    tmp_path,
):
    results = _run_execute_workers(tmp_path, "success")
    assert [status for _rank, status, _payload in results] == ["ok", "ok"]
    assert {payload for _rank, _status, payload in results} == {("preflighted", None)}
    attempt = tmp_path / "staging" / ("1" * 32)
    prepared = read_stage_message(attempt / ".preflight.prepared.stage.json")
    assert prepared.stage is RuntimeStage.PREFLIGHTED
    assert prepared.vote is Vote.PREPARED
    assert not (attempt / ".preflight.prepared.json").exists()
    acknowledgements = tuple(
        read_stage_message(attempt / f".rank-{rank}.teardown.stage.json")
        for rank in range(WORLD_SIZE)
    )
    assert {item.rank for item in acknowledgements} == {0, 1}
    assert {item.vote for item in acknowledgements} == {Vote.COMMITTED}


@pytest.mark.parametrize(
    ("mode", "code"),
    [
        ("identity_failure", "LMS_IDENTITY_MISMATCH"),
        ("commit_failure", "LMS_IDENTITY_MISMATCH"),
        ("code_failure", "LMS_IDENTITY_MISMATCH"),
        ("storage_failure", "LMS_STORAGE_PROFILE_MISMATCH"),
        ("resource_failure", "LMS_RESOURCE_ADMISSION_DENIED"),
        ("stage_timeout", "LMS_STAGE_TIMEOUT"),
        ("cancelled", "LMS_ATTEMPT_CANCELLED"),
        ("native_stderr", "LMS_DIAGNOSTIC_REDACTION_FAILED"),
        ("evidence_failure", "LMS_EVIDENCE_UNAVAILABLE"),
        ("teardown_failure", "LMS_CLEANUP_INCOMPLETE"),
    ],
)
def test_execute_preflight_faults_never_report_success_and_reap_workers(
    tmp_path, mode, code, capfd
):
    results = _run_execute_workers(tmp_path, mode)
    assert [status for _rank, status, _payload in results] == ["error", "error"]
    assert {payload[0] for _rank, _status, payload in results} == {code}
    assert all("secret-bearing" not in payload[1] for _rank, _status, payload in results)
    assert "secret-bearing native child" not in capfd.readouterr().err
    if mode != "teardown_failure":
        attempt = tmp_path / "staging" / ("1" * 32)
        aborting = tuple(
            read_stage_message(attempt / f".rank-{rank}.aborting.stage.json")
            for rank in range(WORLD_SIZE)
        )
        terminal = tuple(
            read_stage_message(attempt / f".rank-{rank}.terminal.stage.json")
            for rank in range(WORLD_SIZE)
        )
        assert {item.stage for item in aborting} == {RuntimeStage.ABORTING}
        assert {item.stage for item in terminal} == {RuntimeStage.ABORTED}
        assert {item.vote for item in (*aborting, *terminal)} == {Vote.ABORT}


@pytest.mark.parametrize(
    ("mode", "ranks", "exit_codes"),
    [
        ("missing_rank", (0,), (0,)),
        ("execute_early_exit", (0, 1), (0, 17)),
    ],
)
def test_execute_preflight_missing_or_exited_rank_quarantines_and_reaps(
    tmp_path, mode, ranks, exit_codes, capfd
):
    results, observed_exit_codes = _run_execute_disruption(tmp_path, mode, ranks=ranks)
    assert observed_exit_codes == exit_codes
    assert len(results) == 1
    assert results[0][1] == "error"
    assert results[0][2][0] == "LMS_CLEANUP_INCOMPLETE"
    evidence = read_evidence(tmp_path / "staging" / ("1" * 32) / "preflight.json")
    assert evidence.result == "quarantined"
    assert evidence.error_code == "LMS_CLEANUP_INCOMPLETE"
    assert "secret-bearing" not in capfd.readouterr().err


@pytest.mark.parametrize("mode", ["rank_exception", "execute_hang"])
def test_execute_preflight_rank_error_or_hang_is_bounded_and_never_succeeds(tmp_path, mode, capfd):
    started = time.monotonic()
    results = _run_execute_workers(tmp_path, mode, timeout=20)
    elapsed = time.monotonic() - started
    assert [status for _rank, status, _payload in results] == ["error", "error"]
    evidence = read_evidence(tmp_path / "staging" / ("1" * 32) / "preflight.json")
    assert evidence.result != "preflighted"
    assert evidence.error_code is not None
    assert "secret-bearing" not in capfd.readouterr().err
    if mode == "execute_hang":
        assert elapsed < 20
