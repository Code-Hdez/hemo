#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ComposeTopologyError(ValueError):
    """A rendered Compose topology violates an infrastructure boundary."""


@dataclass(frozen=True, slots=True)
class ComposeTarget:
    files: tuple[str, ...]
    env_file: str
    services: frozenset[str]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APPLICATION_SERVICES = frozenset({"backend", "frontend", "db", "chroma", "rag_ingest"})
LOCAL_LLM_SERVICES = frozenset({"ollama", "ollama_setup"})
PRODUCTION_AUXILIARY_SERVICES = frozenset({"caddy", "volume_permissions"})
PINNED_IMAGE_PATTERN = re.compile(r"^[^\s@]+@sha256:[0-9a-f]{64}$")

TARGETS = {
    "local": ComposeTarget(
        files=("docker-compose.yml", "docker-compose.local.yml"),
        env_file=".env.example",
        services=APPLICATION_SERVICES | LOCAL_LLM_SERVICES,
    ),
    "production": ComposeTarget(
        files=("docker-compose.yml", "docker-compose.prod.yml"),
        env_file=".env.production.example",
        services=APPLICATION_SERVICES | PRODUCTION_AUXILIARY_SERVICES,
    ),
    "gpu": ComposeTarget(
        files=("docker-compose.gpu.yml",),
        env_file="deploy/gpu/compose.env.example",
        services=LOCAL_LLM_SERVICES,
    ),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ComposeTopologyError(message)


def _is_digest_reference(value: object) -> bool:
    return isinstance(value, str) and PINNED_IMAGE_PATTERN.fullmatch(value) is not None


def _validate_dependencies(services: dict[str, Any]) -> None:
    service_names = set(services)
    for service_name, service in services.items():
        dependencies = service.get("depends_on", {})
        _require(
            isinstance(dependencies, dict),
            f"{service_name}: depends_on must render as an object",
        )
        unknown = set(dependencies) - service_names
        _require(
            not unknown,
            f"{service_name}: external Compose dependencies are forbidden: {sorted(unknown)}",
        )


def _validate_images(services: dict[str, Any], target: str) -> None:
    locally_built = APPLICATION_SERVICES - {"db", "chroma"}
    for service_name, service in services.items():
        if target == "local" and service_name in locally_built:
            _require("build" in service, f"{service_name}: local service must remain buildable")
            continue

        image = service.get("image")
        _require(
            _is_digest_reference(image),
            f"{service_name}: image must use a canonical @sha256 reference",
        )
        _require(":latest" not in str(image), f"{service_name}: latest is forbidden")
        if target in {"production", "gpu"}:
            _require("build" not in service, f"{service_name}: target may not build in place")

    if target == "production":
        backend_image = services["backend"].get("image")
        _require(
            backend_image == services["rag_ingest"].get("image"),
            "production: backend and rag_ingest must use the same immutable image",
        )
        _require(
            "/hemovet-images/backend@sha256:" in str(backend_image),
            "production: backend package identity is invalid",
        )
        _require(
            "/hemovet-images/frontend@sha256:" in str(services["frontend"].get("image")),
            "production: frontend package identity is invalid",
        )

    if target == "gpu":
        runtime_image = services["ollama"].get("image")
        _require(
            runtime_image == services["ollama_setup"].get("image"),
            "gpu: Ollama and bootstrap must use the same immutable runtime",
        )
        _require(
            "/hemovet-images/ollama-runtime@sha256:" in str(runtime_image),
            "gpu: runtime package identity is invalid",
        )


def _port_target(port: dict[str, Any]) -> int:
    try:
        return int(port.get("target"))
    except (TypeError, ValueError) as exc:
        raise ComposeTopologyError("port target must be numeric") from exc


def _validate_no_ollama_publication(services: dict[str, Any], target: str) -> None:
    for service_name, service in services.items():
        for port in service.get("ports", []):
            _require(isinstance(port, dict), f"{service_name}: port must use long syntax")
            _require(
                _port_target(port) != 11434,
                f"{target}: port 11434 may only be published by the isolated GPU target",
            )


def _validate_gpu(services: dict[str, Any]) -> None:
    ollama = services["ollama"]
    setup = services["ollama_setup"]
    ports = ollama.get("ports", [])
    _require(len(ports) == 1, "gpu: Ollama must expose exactly one private host binding")
    port = ports[0]
    _require(isinstance(port, dict), "gpu: Ollama port must use long syntax")
    _require(_port_target(port) == 11434, "gpu: Ollama target port must be 11434")
    _require(int(port.get("published", 0)) == 11434, "gpu: published port must be 11434")

    host_ip = str(port.get("host_ip", ""))
    try:
        address = ipaddress.ip_address(host_ip)
    except ValueError as exc:
        raise ComposeTopologyError("gpu: OLLAMA_BIND_ADDRESS must be an IP literal") from exc
    _require(address.is_private, "gpu: Ollama must bind to a private address")
    _require(not address.is_loopback, "gpu: loopback would prevent production access")
    _require(not address.is_unspecified, "gpu: wildcard address is forbidden")

    for service_name, service in services.items():
        environment = service.get("environment", {})
        forbidden = {
            "DATABASE_URL",
            "SECRET_KEY",
            "POSTGRES_DB",
            "POSTGRES_PASSWORD",
            "RAG_COLLECTION_NAME",
            "CHROMA_HOST",
        }
        _require(
            not (set(environment) & forbidden),
            f"gpu: {service_name} contains application or clinical configuration",
        )
        _require(
            service.get("restart") in {"no", "unless-stopped"},
            f"gpu: {service_name} has no bounded restart policy",
        )

    dependencies = set(setup.get("depends_on", {}))
    _require(dependencies == {"ollama"}, "gpu: bootstrap may depend only on Ollama")
    _require("healthcheck" in ollama, "gpu: runtime healthcheck is required")

    volumes = ollama.get("volumes", [])
    model_mounts = [
        volume
        for volume in volumes
        if isinstance(volume, dict) and volume.get("target") == "/root/.ollama"
    ]
    _require(len(model_mounts) == 1, "gpu: exactly one persistent model mount is required")
    _require(model_mounts[0].get("type") == "volume", "gpu: models must use a named volume")

    devices = (
        ollama.get("deploy", {})
        .get("resources", {})
        .get("reservations", {})
        .get("devices", [])
    )
    _require(len(devices) == 1, "gpu: exactly one NVIDIA reservation is required")
    _require(devices[0].get("driver") == "nvidia", "gpu: NVIDIA driver is required")
    _require("gpu" in devices[0].get("capabilities", []), "gpu: GPU capability is required")


def validate_compose_config(config: dict[str, Any], target: str) -> None:
    """Validate a fully rendered Compose config for one supported target."""

    if target not in TARGETS:
        raise ComposeTopologyError(f"unknown target: {target}")
    services = config.get("services")
    _require(isinstance(services, dict), f"{target}: rendered services are missing")
    assert isinstance(services, dict)

    actual_services = frozenset(services)
    expected_services = TARGETS[target].services
    _require(
        actual_services == expected_services,
        f"{target}: services differ; expected={sorted(expected_services)} actual={sorted(actual_services)}",
    )
    _validate_dependencies(services)
    _validate_images(services, target)

    if target == "production":
        backend_dependencies = set(services["backend"].get("depends_on", {}))
        _require(
            not (backend_dependencies & LOCAL_LLM_SERVICES),
            "production: backend must not depend on Ollama bootstrap",
        )
        _validate_no_ollama_publication(services, target)
    elif target == "local":
        _require(
            set(services["backend"].get("depends_on", {})) >= {"ollama_setup"},
            "local: backend must wait for the optional local model bootstrap",
        )
        _validate_no_ollama_publication(services, target)
    else:
        _validate_gpu(services)


def render_compose_target(target: str, *, project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Render one target deterministically without printing its environment."""

    spec = TARGETS[target]
    command = [
        "docker",
        "compose",
        "--project-directory",
        str(project_root),
        "--env-file",
        str(project_root / spec.env_file),
    ]
    for compose_file in spec.files:
        command.extend(("-f", str(project_root / compose_file)))
    command.extend(("config", "--format", "json"))

    allowed_environment = {
        key: value
        for key in ("PATH", "HOME", "DOCKER_CONFIG", "XDG_RUNTIME_DIR")
        if (value := os.environ.get(key)) is not None
    }
    try:
        completed = subprocess.run(
            command,
            cwd=project_root,
            env=allowed_environment,
            check=True,
            capture_output=True,
            text=True,
        )
        rendered = json.loads(completed.stdout)
    except FileNotFoundError as exc:
        raise ComposeTopologyError("docker compose is not available") from exc
    except subprocess.CalledProcessError as exc:
        raise ComposeTopologyError(f"{target}: docker compose config failed") from exc
    except json.JSONDecodeError as exc:
        raise ComposeTopologyError(f"{target}: Compose returned invalid JSON") from exc

    _require(isinstance(rendered, dict), f"{target}: Compose output is not an object")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Renderiza y valida las fronteras local, producción y GPU."
    )
    parser.add_argument(
        "targets",
        nargs="*",
        default=None,
        metavar="{local,production,gpu}",
    )
    args = parser.parse_args()
    targets = args.targets or tuple(TARGETS)
    unknown_targets = sorted(set(targets) - set(TARGETS))
    if unknown_targets:
        parser.error(f"invalid target(s): {', '.join(unknown_targets)}")

    try:
        for target in targets:
            config = render_compose_target(target)
            validate_compose_config(config, target)
            services = ",".join(sorted(config["services"]))
            print(f"valid {target}: {services}")
    except ComposeTopologyError as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
