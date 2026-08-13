from __future__ import annotations

from copy import deepcopy
import sys
from typing import Any

import pytest

from scripts import validate_compose_topology as topology
from scripts.validate_compose_topology import (
    ComposeTopologyError,
    TARGETS,
    validate_compose_config,
)


REGISTRY = (
    "us-central1-docker.pkg.dev/"
    "project-5b36701c-f44f-4c03-a12/hemovet-images"
)


def _reference(package: str, character: str) -> str:
    return f"{REGISTRY}/{package}@sha256:{character * 64}"


def _dependencies(*names: str) -> dict[str, dict[str, str]]:
    return {name: {"condition": "service_started"} for name in names}


def _valid_local() -> dict[str, Any]:
    return {
        "services": {
            "db": {"image": f"postgres@sha256:{'1' * 64}", "depends_on": {}},
            "chroma": {
                "image": f"chroma@sha256:{'2' * 64}",
                "depends_on": {},
            },
            "rag_ingest": {"build": {"context": "."}, "depends_on": {}},
            "backend": {
                "build": {"context": "."},
                "depends_on": _dependencies("ollama_setup"),
            },
            "frontend": {"build": {"context": "."}, "depends_on": {}},
            "ollama": {
                "image": f"ollama@sha256:{'3' * 64}",
                "depends_on": {},
            },
            "ollama_setup": {
                "image": f"ollama@sha256:{'3' * 64}",
                "depends_on": _dependencies("ollama"),
            },
        }
    }


def _valid_production() -> dict[str, Any]:
    backend_image = _reference("backend", "a")
    return {
        "services": {
            "db": {"image": f"postgres@sha256:{'1' * 64}", "depends_on": {}},
            "chroma": {
                "image": f"chroma@sha256:{'2' * 64}",
                "depends_on": {},
            },
            "rag_ingest": {"image": backend_image, "depends_on": {}},
            "backend": {"image": backend_image, "depends_on": _dependencies("db")},
            "frontend": {
                "image": _reference("frontend", "b"),
                "depends_on": _dependencies("backend"),
            },
            "caddy": {
                "image": f"caddy@sha256:{'4' * 64}",
                "depends_on": _dependencies("frontend", "backend"),
                "ports": [
                    {"target": 80, "published": "80"},
                    {"target": 443, "published": "443"},
                ],
            },
            "volume_permissions": {
                "image": f"alpine@sha256:{'5' * 64}",
                "depends_on": {},
            },
        }
    }


def _valid_gpu() -> dict[str, Any]:
    runtime = _reference("ollama-runtime", "c")
    return {
        "services": {
            "ollama": {
                "image": runtime,
                "restart": "unless-stopped",
                "environment": {"OLLAMA_HOST": "0.0.0.0:11434"},
                "depends_on": {},
                "ports": [
                    {
                        "target": 11434,
                        "published": "11434",
                        "host_ip": "10.128.0.3",
                    }
                ],
                "volumes": [
                    {
                        "type": "volume",
                        "source": "hemovet_gpu_ollama_models",
                        "target": "/root/.ollama",
                    }
                ],
                "healthcheck": {"test": ["CMD", "ollama", "list"]},
                "deploy": {
                    "resources": {
                        "reservations": {
                            "devices": [
                                {
                                    "driver": "nvidia",
                                    "count": 1,
                                    "capabilities": ["gpu"],
                                }
                            ]
                        }
                    }
                },
            },
            "ollama_setup": {
                "image": runtime,
                "restart": "no",
                "environment": {"OLLAMA_MODEL": "qwen3:4b-instruct-2507-q4_K_M"},
                "depends_on": _dependencies("ollama"),
            },
        }
    }


@pytest.mark.parametrize(
    ("target", "factory"),
    [
        ("local", _valid_local),
        ("production", _valid_production),
        ("gpu", _valid_gpu),
    ],
)
def test_valid_topology_contracts_pass(target: str, factory: Any) -> None:
    validate_compose_config(factory(), target)


def test_gpu_is_a_standalone_compose_target() -> None:
    assert TARGETS["gpu"].files == ("docker-compose.gpu.yml",)
    assert TARGETS["local"].files == (
        "docker-compose.yml",
        "docker-compose.local.yml",
    )
    assert TARGETS["production"].files == (
        "docker-compose.yml",
        "docker-compose.prod.yml",
    )


def test_cli_without_arguments_validates_all_supported_targets(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rendered = {
        "local": _valid_local(),
        "production": _valid_production(),
        "gpu": _valid_gpu(),
    }
    calls: list[str] = []

    def fake_render(target: str) -> dict[str, Any]:
        calls.append(target)
        return rendered[target]

    monkeypatch.setattr(topology, "render_compose_target", fake_render)
    monkeypatch.setattr(sys, "argv", ["validate_compose_topology.py"])

    assert topology.main() == 0
    assert calls == ["local", "production", "gpu"]
    assert capsys.readouterr().out.count("valid ") == 3


def test_gpu_rejects_application_services_and_configuration() -> None:
    with_application = deepcopy(_valid_gpu())
    with_application["services"]["backend"] = {
        "image": _reference("backend", "a"),
        "depends_on": {},
    }
    with pytest.raises(ComposeTopologyError, match="services differ"):
        validate_compose_config(with_application, "gpu")

    with_secret = deepcopy(_valid_gpu())
    with_secret["services"]["ollama"]["environment"]["DATABASE_URL"] = (
        "postgresql://forbidden"
    )
    with pytest.raises(ComposeTopologyError, match="clinical configuration"):
        validate_compose_config(with_secret, "gpu")


@pytest.mark.parametrize("host_ip", ["0.0.0.0", "::", "127.0.0.1", "8.8.8.8"])
def test_gpu_rejects_non_private_or_unreachable_bindings(host_ip: str) -> None:
    config = deepcopy(_valid_gpu())
    config["services"]["ollama"]["ports"][0]["host_ip"] = host_ip

    with pytest.raises(ComposeTopologyError, match="gpu:"):
        validate_compose_config(config, "gpu")


def test_production_rejects_local_ollama_and_mutable_images() -> None:
    with_ollama = deepcopy(_valid_production())
    with_ollama["services"]["ollama"] = {
        "image": f"ollama@sha256:{'3' * 64}",
        "depends_on": {},
    }
    with pytest.raises(ComposeTopologyError, match="services differ"):
        validate_compose_config(with_ollama, "production")

    mutable = deepcopy(_valid_production())
    mutable["services"]["backend"]["image"] = f"{REGISTRY}/backend:latest"
    with pytest.raises(ComposeTopologyError, match="@sha256"):
        validate_compose_config(mutable, "production")


def test_external_compose_dependencies_fail_closed() -> None:
    config = _valid_local()
    config["services"]["backend"]["depends_on"]["remote-gpu"] = {
        "condition": "service_started"
    }

    with pytest.raises(ComposeTopologyError, match="external Compose dependencies"):
        validate_compose_config(config, "local")
