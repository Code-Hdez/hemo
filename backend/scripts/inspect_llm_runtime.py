#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

_CONTAINER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_MAX_HTTP_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class RuntimeInspectionError:
    component: str
    code: str


def classify_gpu_residency(size: object, size_vram: object) -> dict[str, object]:
    total = _nonnegative_int(size)
    vram = _nonnegative_int(size_vram)
    if total is None or total <= 0 or vram is None:
        return {"inference_device": "unknown", "vram_ratio": None}
    ratio = min(1.0, vram / total)
    device = "full_gpu" if ratio >= 0.98 else "mixed_cpu_gpu" if vram > 0 else "cpu"
    return {
        "inference_device": device,
        "vram_ratio": round(ratio, 4),
    }


def summarize_ollama(
    *,
    version: dict[str, Any] | None,
    tags: dict[str, Any] | None,
    processes: dict[str, Any] | None,
    show: dict[str, Any] | None = None,
    requested_model: str | None = None,
) -> dict[str, object]:
    installed = [
        _model_summary(item)
        for item in (tags or {}).get("models", [])
        if isinstance(item, dict)
    ]
    loaded: list[dict[str, object]] = []
    for item in (processes or {}).get("models", []):
        if not isinstance(item, dict):
            continue
        model = _model_summary(item)
        model.update(classify_gpu_residency(item.get("size"), item.get("size_vram")))
        model["size_vram"] = _nonnegative_int(item.get("size_vram"))
        model["context_length"] = _nonnegative_int(item.get("context_length"))
        model["expires_at"] = _safe_text(item.get("expires_at"))
        loaded.append(_without_none(model))

    selected_name = requested_model or (
        str(loaded[0].get("name") or "") if loaded else None
    )
    selected = next(
        (
            item
            for item in [*loaded, *installed]
            if selected_name and item.get("name") == selected_name
        ),
        None,
    )
    return _without_none(
        {
            "ollama_version": _safe_text((version or {}).get("version")),
            "requested_model": requested_model,
            "selected_model": selected,
            "loaded_models": loaded,
            "installed_models": installed,
            "model_metadata": _safe_show_metadata(show),
        }
    )


def collect_runtime(
    *,
    ollama_url: str,
    model: str | None,
    ollama_container: str | None,
    timeout_seconds: float,
    inspect_ollama: bool = True,
    inspect_gpu: bool = True,
) -> dict[str, object]:
    base_url = _validated_base_url(ollama_url)
    errors: list[RuntimeInspectionError] = []

    version = (
        _fetch_optional_json(
            urljoin(base_url, "api/version"),
            timeout_seconds,
            "ollama_version",
            errors,
        )
        if inspect_ollama
        else None
    )
    tags = (
        _fetch_optional_json(
            urljoin(base_url, "api/tags"),
            timeout_seconds,
            "ollama_tags",
            errors,
        )
        if inspect_ollama
        else None
    )
    processes = (
        _fetch_optional_json(
            urljoin(base_url, "api/ps"),
            timeout_seconds,
            "ollama_processes",
            errors,
        )
        if inspect_ollama
        else None
    )
    effective_model = model or _first_loaded_model(processes)
    show = (
        _fetch_optional_json(
            urljoin(base_url, "api/show"),
            timeout_seconds,
            "ollama_show",
            errors,
            body={"model": effective_model},
        )
        if effective_model and inspect_ollama
        else None
    )

    payload: dict[str, object] = {
        "schema_version": "hemovet-runtime-inspection-v1",
        "ollama": (
            summarize_ollama(
                version=version,
                tags=tags,
                processes=processes,
                show=show,
                requested_model=model,
            )
            if inspect_ollama
            else {"skipped": True}
        ),
        "gpu": _nvidia_smi(timeout_seconds, errors) if inspect_gpu else [],
    }
    if ollama_container:
        payload["container"] = _docker_stats(
            ollama_container,
            timeout_seconds,
            errors,
        )
    payload["errors"] = [
        {"component": error.component, "code": error.code} for error in errors
    ]
    return payload


def _fetch_optional_json(
    url: str,
    timeout_seconds: float,
    component: str,
    errors: list[RuntimeInspectionError],
    *,
    body: dict[str, object] | None = None,
) -> dict[str, Any] | None:
    try:
        return _http_json(url, timeout_seconds=timeout_seconds, body=body)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        errors.append(RuntimeInspectionError(component, type(exc).__name__))
        return None


def _http_json(
    url: str,
    *,
    timeout_seconds: float,
    body: dict[str, object] | None = None,
) -> dict[str, Any]:
    encoded = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(  # noqa: S310 - URL is operator supplied and validated.
        url,
        data=encoded,
        method="POST" if encoded is not None else "GET",
        headers={"Content-Type": "application/json"} if encoded is not None else {},
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        raw = response.read(_MAX_HTTP_BYTES + 1)
    if len(raw) > _MAX_HTTP_BYTES:
        raise ValueError("ollama_response_too_large")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("ollama_response_not_an_object")
    return payload


def _nvidia_smi(
    timeout_seconds: float,
    errors: list[RuntimeInspectionError],
) -> list[dict[str, object]]:
    command = [
        "nvidia-smi",
        "--query-gpu=index,name,uuid,driver_version,memory.total,memory.used,utilization.gpu,temperature.gpu,power.draw",
        "--format=csv,noheader,nounits",
    ]
    completed = _run_command(command, timeout_seconds, "nvidia_smi", errors)
    if completed is None:
        return []
    fields = (
        "index",
        "name",
        "uuid",
        "driver_version",
        "memory_total_mib",
        "memory_used_mib",
        "utilization_percent",
        "temperature_celsius",
        "power_draw_watts",
    )
    rows: list[dict[str, object]] = []
    for line in completed.stdout.splitlines():
        values = [item.strip() for item in line.split(",")]
        if len(values) != len(fields):
            continue
        rows.append(
            {
                key: _number_or_text(value)
                for key, value in zip(fields, values, strict=True)
            }
        )
    return rows


def _docker_stats(
    container: str,
    timeout_seconds: float,
    errors: list[RuntimeInspectionError],
) -> dict[str, object]:
    if not _CONTAINER_PATTERN.fullmatch(container):
        errors.append(RuntimeInspectionError("docker_stats", "invalid_container_name"))
        return {}
    completed = _run_command(
        ["docker", "stats", "--no-stream", "--format", "{{json .}}", container],
        timeout_seconds,
        "docker_stats",
        errors,
    )
    if completed is None:
        return {}
    try:
        raw = json.loads(completed.stdout.strip())
    except (TypeError, ValueError, json.JSONDecodeError):
        errors.append(RuntimeInspectionError("docker_stats", "invalid_json"))
        return {}
    if not isinstance(raw, dict):
        return {}
    return _without_none(
        {
            "name": _safe_text(raw.get("Name")),
            "cpu_percent": _safe_text(raw.get("CPUPerc")),
            "memory_usage": _safe_text(raw.get("MemUsage")),
            "memory_percent": _safe_text(raw.get("MemPerc")),
            "pids": _nonnegative_int(raw.get("PIDs")),
        }
    )


def _run_command(
    command: list[str],
    timeout_seconds: float,
    component: str,
    errors: list[RuntimeInspectionError],
) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(  # noqa: S603 - fixed executable and validated args.
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (FileNotFoundError, subprocess.SubprocessError, OSError) as exc:
        errors.append(RuntimeInspectionError(component, type(exc).__name__))
        return None


def _model_summary(value: dict[str, Any]) -> dict[str, object]:
    details = value.get("details")
    details = details if isinstance(details, dict) else {}
    return _without_none(
        {
            "name": _safe_text(value.get("name") or value.get("model")),
            "digest": _safe_text(value.get("digest")),
            "size": _nonnegative_int(value.get("size")),
            "format": _safe_text(details.get("format")),
            "family": _safe_text(details.get("family")),
            "parameter_size": _safe_text(details.get("parameter_size")),
            "quantization": _safe_text(details.get("quantization_level")),
        }
    )


def _safe_show_metadata(value: dict[str, Any] | None) -> dict[str, object] | None:
    if not value:
        return None
    details = value.get("details")
    details = details if isinstance(details, dict) else {}
    model_info = value.get("model_info")
    model_info = model_info if isinstance(model_info, dict) else {}
    allowed_suffixes = (
        ".architecture",
        ".context_length",
        ".embedding_length",
        ".parameter_count",
        ".file_type",
    )
    safe_info = {
        str(key): item
        for key, item in model_info.items()
        if any(str(key).endswith(suffix) for suffix in allowed_suffixes)
        and isinstance(item, str | int | float | bool)
    }
    return _without_none(
        {
            "format": _safe_text(details.get("format")),
            "family": _safe_text(details.get("family")),
            "parameter_size": _safe_text(details.get("parameter_size")),
            "quantization": _safe_text(details.get("quantization_level")),
            "model_info": safe_info or None,
        }
    )


def _first_loaded_model(processes: dict[str, Any] | None) -> str | None:
    models = (processes or {}).get("models")
    if not isinstance(models, list) or not models or not isinstance(models[0], dict):
        return None
    return _safe_text(models[0].get("name") or models[0].get("model"))


def _validated_base_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("invalid_ollama_url")
    return value.rstrip("/") + "/"


def _safe_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).split())
    return normalized[:256] if normalized else None


def _nonnegative_int(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _number_or_text(value: str) -> int | float | str | None:
    normalized = value.strip()
    if not normalized or normalized.casefold() in {"n/a", "[not supported]"}:
        return None
    try:
        parsed = float(normalized)
    except ValueError:
        return normalized[:256]
    return int(parsed) if parsed.is_integer() else parsed


def _without_none(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspecciona metadatos seguros de Ollama, GPU y contenedor.",
    )
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434/")
    parser.add_argument("--model")
    parser.add_argument("--ollama-container")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--skip-ollama", action="store_true")
    parser.add_argument("--skip-gpu", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.timeout_seconds <= 0 or args.timeout_seconds > 120:
        parser.error("--timeout-seconds debe estar entre 0 y 120")
    if args.skip_ollama and args.skip_gpu and not args.ollama_container:
        parser.error("no hay ningún componente seleccionado para inspección")
    try:
        result = collect_runtime(
            ollama_url=args.ollama_url,
            model=args.model,
            ollama_container=args.ollama_container,
            timeout_seconds=args.timeout_seconds,
            inspect_ollama=not args.skip_ollama,
            inspect_gpu=not args.skip_gpu,
        )
    except ValueError as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        sys.stdout.write(serialized + "\n")
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
