"""Consume fixed torchrun membership without launching or provisioning workers."""

from __future__ import annotations

import ipaddress
import os
import socket
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta

import psutil  # type: ignore[import-untyped]
import torch.distributed as dist

from obliteratus.distributed.config import DistributedPreflightConfig
from obliteratus.distributed.contracts import (
    ContractError,
    RuntimeContractError,
    contract_digest,
)


_REQUIRED_ENV = frozenset(
    {
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
    }
)
_SENSITIVE_ENV_PARTS = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "API_KEY",
    "ACCESS_KEY",
    "PRIVATE_KEY",
    "CREDENTIAL",
)
_SENSITIVE_ENV_PREFIXES = ("AWS_", "AZURE_", "GOOGLE_", "HF_", "OPENAI_", "ANTHROPIC_")
_PROXY_ENV = frozenset({"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"})
_BACKEND_DIAGNOSTIC_LOCK = threading.RLock()
_CLEANUP_TIMEOUT_EXIT_CODE = 70


def _sensitive_environment_key(name: str) -> bool:
    upper = name.upper()
    return (
        upper in _PROXY_ENV
        or upper.startswith(_SENSITIVE_ENV_PREFIXES)
        or any(part in upper for part in _SENSITIVE_ENV_PARTS)
    )


def _env_integer(environ: Mapping[str, str], name: str, minimum: int, maximum: int) -> int:
    value = environ[name]
    if not value or len(value) > 10 or not value.isascii() or not value.isdecimal():
        raise ContractError(f"{name.lower()} must be an unsigned decimal integer")
    parsed = int(value)
    if not minimum <= parsed <= maximum:
        raise ContractError(f"{name.lower()} is outside its allowed range")
    return parsed


def _private_allowlisted_address(address: str, cidrs: tuple[str, ...]) -> bool:
    try:
        candidate = ipaddress.ip_address(address)
    except ValueError:
        return False
    private_ranges = (
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("fc00::/7"),
    )
    if not any(candidate in item for item in private_ranges):
        return False
    return any(candidate in ipaddress.ip_network(item, strict=True) for item in cidrs)


def validate_network_interface(
    interface: str,
    allowed_cidrs: tuple[str, ...],
    master_addr: str,
    *,
    coordinator: bool,
) -> None:
    """Require an approved private address before opening a rendezvous socket."""

    interfaces = psutil.net_if_addrs()
    if interface not in interfaces:
        raise RuntimeContractError(
            "LMS_NETWORK_PROFILE_DENIED", "configured network interface is unavailable"
        )
    networks = tuple(ipaddress.ip_network(item, strict=True) for item in allowed_cidrs)
    addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for observed in interfaces[interface]:
        if observed.family not in {socket.AF_INET, socket.AF_INET6}:
            continue
        try:
            address = ipaddress.ip_address(observed.address.split("%", 1)[0])
        except ValueError:
            continue
        if any(address in network for network in networks if address.version == network.version):
            addresses.add(address)
    if not addresses:
        raise RuntimeContractError(
            "LMS_NETWORK_PROFILE_DENIED",
            "configured network interface has no private allowlisted address",
        )
    if coordinator and ipaddress.ip_address(master_addr) not in addresses:
        raise RuntimeContractError(
            "LMS_NETWORK_PROFILE_DENIED",
            "coordinator endpoint is not bound to the configured interface",
        )


@contextmanager
def _backend_diagnostic_guard() -> Iterator[None]:
    """Discard native fd-2 diagnostics and fail if the backend emits any bytes."""

    with _BACKEND_DIAGNOSTIC_LOCK:
        read_descriptor: int | None = None
        write_descriptor: int | None = None
        saved_stderr: int | None = None
        reader: threading.Thread | None = None
        observed = threading.Event()
        reader_failed = threading.Event()
        body_error: BaseException | None = None
        try:
            read_descriptor, write_descriptor = os.pipe()
            saved_stderr = os.dup(2)

            def discard() -> None:
                assert read_descriptor is not None
                try:
                    while chunk := os.read(read_descriptor, 8192):
                        observed.set()
                        del chunk
                except OSError:
                    reader_failed.set()
                finally:
                    os.close(read_descriptor)

            reader = threading.Thread(
                target=discard,
                daemon=True,
                name="obliteratus-backend-diagnostic-sink",
            )
            reader.start()
            os.dup2(write_descriptor, 2)
            os.close(write_descriptor)
            write_descriptor = None
            try:
                yield
            except BaseException as error:
                body_error = error
        except OSError as error:
            body_error = RuntimeContractError(
                "LMS_DIAGNOSTIC_REDACTION_FAILED",
                "backend diagnostic containment is unavailable",
            )
            del error
        finally:
            if saved_stderr is not None:
                try:
                    os.dup2(saved_stderr, 2)
                except OSError:
                    reader_failed.set()
                os.close(saved_stderr)
            if write_descriptor is not None:
                os.close(write_descriptor)
            if reader is not None:
                reader.join(1)
                if reader.is_alive():
                    reader_failed.set()
            elif read_descriptor is not None:
                os.close(read_descriptor)
        if (
            isinstance(body_error, RuntimeContractError)
            and body_error.code == "LMS_CLEANUP_INCOMPLETE"
        ):
            raise body_error.with_traceback(body_error.__traceback__)
        if observed.is_set() or reader_failed.is_set():
            raise RuntimeContractError(
                "LMS_DIAGNOSTIC_REDACTION_FAILED",
                "backend diagnostic output was suppressed",
            ) from None
        if body_error is not None:
            raise body_error.with_traceback(body_error.__traceback__)


@dataclass(frozen=True)
class TorchrunEnvironment:
    """One validated worker identity supplied by an external fixed scheduler."""

    rank: int
    local_rank: int
    world_size: int
    local_world_size: int
    group_rank: int
    role_rank: int
    role_world_size: int
    master_endpoint_digest: str
    run_id: str
    rendezvous_id: str
    network_interface: str

    @classmethod
    def from_environ(
        cls,
        environ: Mapping[str, str],
        config: DistributedPreflightConfig,
    ) -> "TorchrunEnvironment":
        if _REQUIRED_ENV - set(environ):
            raise RuntimeContractError(
                "LMS_LAUNCH_IDENTITY_INVALID",
                "required torchrun environment is incomplete",
            )
        if any(_sensitive_environment_key(name) for name in environ):
            raise RuntimeContractError(
                "LMS_SECRET_INPUT_REJECTED",
                "secret-bearing or proxy environment fields are forbidden",
            )
        allowed = _REQUIRED_ENV | set(config.allowed_environment_keys)
        if set(environ) - allowed:
            raise RuntimeContractError(
                "LMS_FORBIDDEN_RUNTIME_CAPABILITY",
                "environment contains fields outside the explicit allowlist",
            )
        rank = _env_integer(environ, "RANK", 0, 4095)
        local_rank = _env_integer(environ, "LOCAL_RANK", 0, 4095)
        world_size = _env_integer(environ, "WORLD_SIZE", 2, 4096)
        local_world_size = _env_integer(environ, "LOCAL_WORLD_SIZE", 1, 4096)
        group_rank = _env_integer(environ, "GROUP_RANK", 0, 4095)
        role_rank = _env_integer(environ, "ROLE_RANK", 0, 4095)
        role_world_size = _env_integer(environ, "ROLE_WORLD_SIZE", 1, 4096)
        master_port = _env_integer(environ, "MASTER_PORT", 1, 65535)
        restart_count = _env_integer(environ, "TORCHELASTIC_RESTART_COUNT", 0, 4096)
        max_restarts = _env_integer(environ, "TORCHELASTIC_MAX_RESTARTS", 0, 4096)

        if rank >= world_size:
            raise ContractError("rank must be smaller than world_size")
        if local_rank >= local_world_size:
            raise ContractError("local_rank must be smaller than local_world_size")
        if world_size != config.world_size:
            raise ContractError("world_size disagrees with the distributed profile")
        if local_world_size != config.local_world_size:
            raise ContractError("local_world_size disagrees with the distributed profile")
        expected_groups = world_size // local_world_size
        if group_rank >= expected_groups:
            raise ContractError("group_rank must be smaller than the fixed group count")
        if rank != group_rank * local_world_size + local_rank:
            raise ContractError("global, group, and local ranks disagree")
        if role_rank != rank or role_world_size != world_size:
            raise ContractError("role_world_size disagrees with fixed membership")
        if restart_count != 0 or max_restarts != 0:
            raise RuntimeContractError(
                "LMS_ELASTICITY_FORBIDDEN",
                "torchrun elasticity and restarts are forbidden",
            )
        if environ["OBLITERATUS_RUN_ID"] != config.run_id:
            raise ContractError("run_id disagrees with the distributed profile")
        if environ["TORCHELASTIC_RUN_ID"] != config.rendezvous_id:
            raise ContractError("rendezvous_id disagrees with the distributed profile")
        if environ["MASTER_ADDR"] != config.master_addr or master_port != config.master_port:
            raise ContractError("master endpoint disagrees with the distributed profile")
        if not _private_allowlisted_address(config.master_addr, config.allowed_master_cidrs):
            raise RuntimeContractError(
                "LMS_NETWORK_PROFILE_DENIED",
                "master endpoint must be a private allowlisted numeric address",
            )
        if (
            environ["GLOO_SOCKET_IFNAME"] != config.network_interface
            or environ["NCCL_SOCKET_IFNAME"] != config.network_interface
        ):
            raise ContractError("network interface disagrees with the distributed profile")
        return cls(
            rank=rank,
            local_rank=local_rank,
            world_size=world_size,
            local_world_size=local_world_size,
            group_rank=group_rank,
            role_rank=role_rank,
            role_world_size=role_world_size,
            master_endpoint_digest=contract_digest(
                {"address": config.master_addr, "port": config.master_port}
            ),
            run_id=config.run_id,
            rendezvous_id=config.rendezvous_id,
            network_interface=config.network_interface,
        )


@contextmanager
def control_group(
    config: DistributedPreflightConfig,
    launch: TorchrunEnvironment,
) -> Iterator[None]:
    """Own one bounded Gloo control group and always tear it down."""
    if not dist.is_available() or dist.is_initialized():
        raise ContractError("distributed control group is unavailable or already initialized")
    validate_network_interface(
        config.network_interface,
        config.allowed_master_cidrs,
        config.master_addr,
        coordinator=launch.rank == config.coordinator_rank,
    )

    def bounded_destroy() -> None:
        if not dist.is_initialized():
            return
        errors: list[BaseException] = []

        def destroy() -> None:
            try:
                dist.destroy_process_group()
            except BaseException as error:
                errors.append(error)

        thread = threading.Thread(target=destroy, daemon=True, name="obliteratus-gloo-teardown")
        thread.start()
        thread.join(config.teardown_timeout_seconds)
        if thread.is_alive():
            # A Python thread cannot be killed safely. Exiting this externally
            # launched worker while fd 2 is still guarded is the only bounded
            # way to prevent late native diagnostics or continued group use.
            os._exit(_CLEANUP_TIMEOUT_EXIT_CODE)
        if errors:
            raise RuntimeContractError(
                "LMS_CLEANUP_INCOMPLETE", "control group teardown failed"
            ) from None

    with _backend_diagnostic_guard():
        try:
            dist.init_process_group(
                backend="gloo",
                init_method="env://",
                rank=launch.rank,
                world_size=launch.world_size,
                timeout=timedelta(
                    seconds=min(
                        config.init_timeout_seconds,
                        config.collective_timeout_seconds,
                    )
                ),
            )
        except BaseException as error:
            bounded_destroy()
            if isinstance(error, TimeoutError) or type(error).__name__ == "DistStoreError":
                raise RuntimeContractError(
                    "LMS_MEMBERSHIP_TIMEOUT",
                    "fixed membership did not rendezvous within its bound",
                ) from None
            raise RuntimeContractError(
                "LMS_COLLECTIVE_FAILED", "control group initialization failed"
            ) from None
        try:
            yield
        finally:
            bounded_destroy()
