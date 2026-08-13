from __future__ import annotations

from collections.abc import AsyncIterator
import asyncio
import json
import logging
import time

import httpx

from app.modules.llm_chat.domain.entities import (
    ModelRequest,
    ModelResponse,
    ModelStreamChunk,
    TokenUsage,
    ToolCall,
)
from app.modules.llm_chat.domain.generation_config import EffectiveGenerationProfile
from app.modules.llm_chat.domain.provider_contract import (
    PROVIDER_CORRELATION_HEADER,
)
from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable

logger = logging.getLogger("uvicorn.error.hemovet.llm_chat")

RequestTimeout = float | httpx.Timeout
PROVIDER_HEALTH_REQUEST_TIMEOUT_SECONDS = 1.5


def _health_timeout(timeout: RequestTimeout) -> float:
    if isinstance(timeout, httpx.Timeout):
        candidates = (timeout.connect, timeout.read, timeout.pool)
        configured = [float(value) for value in candidates if value is not None]
        return (
            min([PROVIDER_HEALTH_REQUEST_TIMEOUT_SECONDS, *configured])
            if configured
            else PROVIDER_HEALTH_REQUEST_TIMEOUT_SECONDS
        )
    return min(float(timeout), PROVIDER_HEALTH_REQUEST_TIMEOUT_SECONDS)


def _generation_timeout(
    request: ModelRequest,
    configured: RequestTimeout,
) -> RequestTimeout:
    if not isinstance(configured, httpx.Timeout):
        return request.timeout_seconds
    return httpx.Timeout(
        request.timeout_seconds,
        connect=configured.connect,
        read=request.timeout_seconds,
        write=configured.write,
        pool=configured.pool,
    )


def _correlation_headers(request: ModelRequest) -> dict[str, str]:
    correlation_id = str(request.correlation_id or "").strip()
    if not correlation_id or len(correlation_id) > 128:
        return {}
    if any(character.isspace() or ord(character) < 33 for character in correlation_id):
        return {}
    return {PROVIDER_CORRELATION_HEADER: correlation_id}


class LLMRuntimeError(ChatRuntimeUnavailable):
    """The external generation runtime is unavailable or returned invalid data."""


class OpenAICompatibleLLMClient:
    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        base_url: str,
        model_name: str,
        timeout_seconds: RequestTimeout,
    ) -> None:
        self.http_client = http_client
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    async def generate(self, request: ModelRequest) -> ModelResponse:
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "repetition_penalty": request.repeat_penalty,
            "max_tokens": request.num_predict,
            "chat_template_kwargs": {"enable_thinking": request.thinking},
            "stream": False,
        }
        if not request.thinking:
            payload["reasoning_effort"] = "none"
            payload["reasoning"] = {"effort": "none"}
        if request.response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "hemovet_chat_response",
                    "strict": True,
                    "schema": request.response_schema,
                },
            }
        started = time.perf_counter()
        try:
            response = await self.http_client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=_correlation_headers(request),
                timeout=_generation_timeout(request, self.timeout_seconds),
            )
            response.raise_for_status()
            body = response.json()
            choice = body["choices"][0]
            text = str(choice["message"]["content"]).strip()
            finish_reason = choice.get("finish_reason")
            if not isinstance(finish_reason, str) or not finish_reason:
                raise ValueError("missing finish_reason")
        except httpx.ConnectTimeout as exc:
            self._log_failure("connect_timeout", started)
            raise LLMRuntimeError("provider_connect_timeout") from exc
        except httpx.TimeoutException as exc:
            self._log_failure("read_timeout", started)
            raise LLMRuntimeError("provider_read_timeout") from exc
        except httpx.HTTPStatusError as exc:
            self._log_failure(
                "http_status",
                started,
                status_code=exc.response.status_code,
            )
            code = (
                "provider_overloaded"
                if exc.response.status_code in {429, 502, 503, 504}
                else "provider_unavailable"
            )
            raise LLMRuntimeError(code) from exc
        except httpx.HTTPError as exc:
            self._log_failure("transport", started)
            raise LLMRuntimeError("provider_unavailable") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            self._log_failure("invalid_response", started)
            raise LLMRuntimeError("provider_invalid_response") from exc
        usage = body.get("usage") or {}
        return ModelResponse(
            text=text,
            model=str(body.get("model") or request.model),
            usage=TokenUsage(
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
            ),
            duration_ms=round((time.perf_counter() - started) * 1000),
            finish_reason=finish_reason,
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamChunk]:
        """Stream an OpenAI-compatible response without leaking provider details.

        vLLM and other compatible runtimes send Server-Sent Events whose `data`
        values contain chat-completion chunks.  The application still decides
        whether a route is safe to expose incrementally.
        """
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "repetition_penalty": request.repeat_penalty,
            "max_tokens": request.num_predict,
            "chat_template_kwargs": {"enable_thinking": request.thinking},
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if not request.thinking:
            payload["reasoning_effort"] = "none"
            payload["reasoning"] = {"effort": "none"}
        if request.response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "hemovet_chat_response",
                    "strict": True,
                    "schema": request.response_schema,
                },
            }
        started = time.perf_counter()
        usage = TokenUsage()
        finish_reason = "stop"
        model = request.model
        saw_terminal = False
        try:
            async with self.http_client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=_correlation_headers(request),
                timeout=_generation_timeout(request, self.timeout_seconds),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        saw_terminal = True
                        break
                    body = json.loads(raw)
                    model = str(body.get("model") or model)
                    raw_usage = body.get("usage") or {}
                    if raw_usage:
                        usage = TokenUsage(
                            prompt_tokens=int(raw_usage.get("prompt_tokens") or 0),
                            completion_tokens=int(
                                raw_usage.get("completion_tokens") or 0
                            ),
                        )
                    choices = body.get("choices") or []
                    if not choices:
                        continue
                    choice = choices[0]
                    if choice.get("finish_reason"):
                        finish_reason = str(choice["finish_reason"])
                        saw_terminal = True
                    delta = choice.get("delta") or {}
                    text = str(delta.get("content") or "")
                    if text:
                        yield ModelStreamChunk(text=text, model=model)
        except httpx.ConnectTimeout as exc:
            self._log_failure("connect_timeout", started)
            raise LLMRuntimeError("provider_connect_timeout") from exc
        except httpx.TimeoutException as exc:
            self._log_failure("read_timeout", started)
            raise LLMRuntimeError("provider_read_timeout") from exc
        except httpx.HTTPStatusError as exc:
            self._log_failure(
                "http_status", started, status_code=exc.response.status_code
            )
            code = (
                "provider_overloaded"
                if exc.response.status_code in {429, 502, 503, 504}
                else "provider_unavailable"
            )
            raise LLMRuntimeError(code) from exc
        except httpx.HTTPError as exc:
            self._log_failure("transport", started)
            raise LLMRuntimeError("provider_unavailable") from exc
        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            self._log_failure("invalid_response", started)
            raise LLMRuntimeError("provider_invalid_response") from exc
        if not saw_terminal:
            self._log_failure("missing_terminal_event", started)
            raise LLMRuntimeError("provider_invalid_response")
        yield ModelStreamChunk(
            done=True,
            model=model,
            usage=usage,
            duration_ms=round((time.perf_counter() - started) * 1000),
            finish_reason=finish_reason,
        )

    async def identity_status(self) -> dict[str, object]:
        response = await self.http_client.get(
            f"{self.base_url}/models",
            timeout=_health_timeout(self.timeout_seconds),
        )
        response.raise_for_status()
        body = response.json()
        models = body.get("data") if isinstance(body, dict) else None
        if not isinstance(models, list):
            raise ValueError("provider model inventory is invalid")
        installed = any(
            str(item.get("id") or "") == self.model_name
            for item in models
            if isinstance(item, dict)
        )
        return {
            "provider": "openai_compatible",
            "model": self.model_name,
            "installed": installed,
        }

    async def health(self) -> bool:
        try:
            return bool((await self.identity_status()).get("installed"))
        except (httpx.HTTPError, TypeError, ValueError):
            return False

    async def runtime_status(self) -> dict[str, object]:
        # The OpenAI-compatible boundary does not expose host accelerator data.
        # Report that explicitly instead of guessing from a model name.
        return {
            "provider": "openai_compatible",
            "model": self.model_name,
            "loaded": None,
            "gpu_active": None,
            "gpu_memory_bytes": None,
            "inference_device": "external_unknown",
        }

    def _log_failure(
        self,
        error_type: str,
        started: float,
        *,
        status_code: int | None = None,
    ) -> None:
        logger.info(
            "llm_chat.provider_error %s",
            json.dumps(
                {
                    "error_type": error_type,
                    "duration_ms": round((time.perf_counter() - started) * 1000),
                    "status_code": status_code,
                },
                sort_keys=True,
            ),
        )


class OllamaNativeLLMClient:
    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        base_url: str,
        model_name: str,
        timeout_seconds: RequestTimeout,
        warmup_profile: EffectiveGenerationProfile,
    ) -> None:
        self.http_client = http_client
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.warmup_profile = warmup_profile
        # VRAM del runner cuando estaba alineado con el perfil. La fija la
        # primera observación del poll y se refresca en cada rearmado; el warmup
        # no la toca, porque su único trabajo es cargar el modelo.
        self._warmed_vram: int | None = None
        self._runtime_snapshot: dict[str, object] = {
            "provider": "ollama",
            "model": self.model_name,
            "loaded": False,
            "gpu_active": None,
            "gpu_memory_bytes": None,
            "inference_device": "unknown",
        }

    async def generate(self, request: ModelRequest) -> ModelResponse:
        payload = self._payload(request, stream=False)
        started = time.perf_counter()
        try:
            response = await self.http_client.post(
                f"{self.base_url}/api/chat",
                json=payload,
                headers=_correlation_headers(request),
                timeout=_generation_timeout(request, self.timeout_seconds),
            )
            response.raise_for_status()
            body = response.json()
            message = body["message"]
            text = str(message.get("content") or "").strip()
            tool_calls = self._tool_calls(message)
            if body.get("done") is not True:
                raise ValueError("missing done marker")
            finish_reason = body.get("done_reason")
            if not isinstance(finish_reason, str) or not finish_reason:
                raise ValueError("missing done_reason")
            # A turn that asked for tools legitimately returns no prose. Only
            # a reply that is empty *and* asked for nothing is malformed.
            if not text and not tool_calls:
                raise ValueError("empty message")
        except httpx.ConnectTimeout as exc:
            self._log_failure("connect_timeout", started)
            raise LLMRuntimeError("ollama_connect_timeout") from exc
        except httpx.TimeoutException as exc:
            self._log_failure("read_timeout", started)
            raise LLMRuntimeError("ollama_read_timeout") from exc
        except httpx.HTTPStatusError as exc:
            self._log_failure(
                "http_status",
                started,
                status_code=exc.response.status_code,
            )
            code = (
                "ollama_overloaded"
                if exc.response.status_code in {429, 502, 503, 504}
                else "ollama_unavailable"
            )
            raise LLMRuntimeError(code) from exc
        except httpx.HTTPError as exc:
            self._log_failure("transport", started)
            raise LLMRuntimeError("ollama_unavailable") from exc
        except (KeyError, TypeError, ValueError) as exc:
            self._log_failure("invalid_response", started)
            raise LLMRuntimeError("ollama_invalid_response") from exc

        metrics = self._metrics(body)
        duration_ms = int(
            round(float(metrics.get("total_duration_ms", 0)))
            or round((time.perf_counter() - started) * 1000)
        )
        await self._refresh_runtime_after_generation_if_stale()
        self._log_metrics(metrics, duration_ms=duration_ms)
        return ModelResponse(
            text=text,
            model=str(body.get("model") or request.model),
            usage=self._usage(body),
            duration_ms=duration_ms,
            finish_reason=finish_reason,
            provider_metrics=metrics,
            tool_calls=tool_calls,
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamChunk]:
        payload = self._payload(request, stream=True)
        started = time.perf_counter()
        saw_terminal = False
        try:
            async with self.http_client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                headers=_correlation_headers(request),
                timeout=_generation_timeout(request, self.timeout_seconds),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    body = json.loads(line)
                    message = body.get("message") or {}
                    text = str(message.get("content") or "")
                    if text:
                        yield ModelStreamChunk(
                            text=text,
                            model=str(body.get("model") or request.model),
                        )
                    if body.get("done") is True:
                        saw_terminal = True
                        metrics = self._metrics(body)
                        duration_ms = int(
                            round(float(metrics.get("total_duration_ms", 0)))
                            or round((time.perf_counter() - started) * 1000)
                        )
                        await self._refresh_runtime_after_generation_if_stale()
                        self._log_metrics(metrics, duration_ms=duration_ms)
                        yield ModelStreamChunk(
                            done=True,
                            model=str(body.get("model") or request.model),
                            usage=self._usage(body),
                            duration_ms=duration_ms,
                            finish_reason=str(body.get("done_reason") or "stop"),
                            provider_metrics=metrics,
                        )
        except httpx.ConnectTimeout as exc:
            self._log_failure("connect_timeout", started)
            raise LLMRuntimeError("ollama_connect_timeout") from exc
        except httpx.TimeoutException as exc:
            self._log_failure("read_timeout", started)
            raise LLMRuntimeError("ollama_read_timeout") from exc
        except httpx.HTTPStatusError as exc:
            self._log_failure(
                "http_status",
                started,
                status_code=exc.response.status_code,
            )
            code = (
                "ollama_overloaded"
                if exc.response.status_code in {429, 502, 503, 504}
                else "ollama_unavailable"
            )
            raise LLMRuntimeError(code) from exc
        except httpx.HTTPError as exc:
            self._log_failure("transport", started)
            raise LLMRuntimeError("ollama_unavailable") from exc
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self._log_failure("invalid_response", started)
            raise LLMRuntimeError("ollama_invalid_response") from exc
        if not saw_terminal:
            self._log_failure("missing_terminal_event", started)
            raise LLMRuntimeError("ollama_invalid_response")

    async def identity_status(self) -> dict[str, object]:
        """Verify the installed artifact independently from VRAM residency."""

        timeout = _health_timeout(self.timeout_seconds)
        tags_response = await self.http_client.get(
            f"{self.base_url}/api/tags",
            timeout=timeout,
        )
        tags_response.raise_for_status()
        body = tags_response.json()
        models = body.get("models") if isinstance(body, dict) else None
        if not isinstance(models, list):
            raise ValueError("ollama model inventory is invalid")
        configured = self.model_name.removesuffix(":latest")
        selected = next(
            (
                item
                for item in models
                if isinstance(item, dict)
                and str(item.get("name") or item.get("model") or "").removesuffix(
                    ":latest"
                )
                == configured
            ),
            None,
        )
        if selected is None:
            return {
                "provider": "ollama",
                "model": self.model_name,
                "installed": False,
                "digest": None,
                "quantization": None,
            }
        show_response = await self.http_client.post(
            f"{self.base_url}/api/show",
            json={"model": self.model_name},
            timeout=timeout,
        )
        show_response.raise_for_status()
        show = show_response.json()
        if not isinstance(show, dict):
            raise ValueError("ollama model details are invalid")
        tag_details = selected.get("details")
        show_details = show.get("details")
        detail_mapping = (
            show_details
            if isinstance(show_details, dict)
            else tag_details
            if isinstance(tag_details, dict)
            else {}
        )
        return {
            "provider": "ollama",
            "model": self.model_name,
            "installed": True,
            "digest": str(selected.get("digest") or "") or None,
            "quantization": (
                str(detail_mapping.get("quantization_level") or "") or None
            ),
        }

    async def health(self) -> bool:
        try:
            return bool((await self.identity_status()).get("installed"))
        except (httpx.HTTPError, TypeError, ValueError):
            return False

    async def runtime_status(self) -> dict[str, object]:
        """Read Ollama residency without touching the generation hot path."""
        try:
            response = await self.http_client.get(
                f"{self.base_url}/api/ps",
                timeout=_health_timeout(self.timeout_seconds),
            )
            response.raise_for_status()
            body = response.json()
            models = body.get("models") if isinstance(body, dict) else None
            configured = self.model_name.removesuffix(":latest")
            selected = next(
                (
                    item
                    for item in (models or [])
                    if isinstance(item, dict)
                    and str(item.get("name") or item.get("model") or "").removesuffix(
                        ":latest"
                    )
                    == configured
                ),
                None,
            )
            vram = int((selected or {}).get("size_vram") or 0)
            size = int((selected or {}).get("size") or 0)
            ratio = round(vram / size, 4) if size > 0 else 0.0
            loaded = selected is not None
            if not loaded:
                inference_device = "not_loaded"
            elif ratio >= 0.98:
                inference_device = "full_gpu"
            elif vram > 0:
                inference_device = "mixed_cpu_gpu"
            else:
                inference_device = "cpu"
            details = (selected or {}).get("details")
            detail_mapping = details if isinstance(details, dict) else {}
            snapshot = {
                "provider": "ollama",
                "model": self.model_name,
                "loaded": loaded,
                "gpu_active": bool(vram > 0) if loaded else False,
                "gpu_memory_bytes": vram if loaded else 0,
                "model_size_bytes": size if loaded else 0,
                "gpu_residency_ratio": ratio if loaded else 0.0,
                "inference_device": inference_device,
                "digest": str((selected or {}).get("digest") or "") or None,
                "quantization": (
                    str(detail_mapping.get("quantization_level") or "") or None
                ),
            }
        except (httpx.HTTPError, TypeError, ValueError):
            snapshot = {
                **self._runtime_snapshot,
                "loaded": False,
                "gpu_active": None,
                "inference_device": "unknown",
            }
        self._runtime_snapshot = snapshot
        return dict(snapshot)

    async def _refresh_runtime_after_generation_if_stale(self) -> None:
        """Replace a transient pre-generation ``not_loaded`` observation.

        Ollama can briefly evict a resident chat model while another local job
        uses VRAM.  A successful generation proves that the model is loaded
        again, but a cached ``/api/ps`` observation would otherwise make that
        request's trace report a false CPU/not-loaded state.  Refresh only in
        that stale case, after the last provider token, so TTFT and the hot
        generation path are unaffected.
        """
        if not (
            self._runtime_snapshot.get("gpu_active") is False
            or self._runtime_snapshot.get("inference_device") == "not_loaded"
        ):
            return
        await self.runtime_status()

    # Fracción de desviación de `size_vram` que se considera «otro runner».
    # Medido contra la L4 de producción el 8-ago-2026: el mismo modelo cargado a
    # num_ctx 16384 ocupa 16 926 501 764 B y a 65536 ocupa 18 889 436 036 B —
    # 1,83 GiB de diferencia, un 11,6 % del valor base. Las dos lecturas a 16384
    # fueron idénticas al byte, así que la señal es limpia y el umbral se pone a
    # la mitad de la separación observada.
    RUNNER_VRAM_TOLERANCE = 0.05

    async def resident_runner_vram(self) -> int | None:
        """Bytes de VRAM del runner residente, o None si no hay ninguno.

        `/api/ps` no publica el `num_ctx` con el que se cargó el modelo, así que
        no se puede comparar el contexto directamente. Lo que sí publica es
        `size_vram`, y el tamaño de la caché KV escala con el contexto: es el
        único discriminador disponible desde fuera del runner.
        """

        try:
            response = await self.http_client.get(
                f"{self.base_url}/api/ps", timeout=self.timeout_seconds
            )
            response.raise_for_status()
            models = response.json().get("models")
        except (httpx.HTTPError, TypeError, ValueError):
            return None
        if not isinstance(models, list) or not models:
            return None
        vram = models[0].get("size_vram")
        return int(vram) if isinstance(vram, (int, float)) else None

    async def capture_runner_baseline(self) -> int | None:
        """Fija la referencia justo después de un warmup, cuando sabemos que vale.

        La primera versión dejaba que el poll adoptase como referencia *lo que
        se encontrase*. Eso es incorrecto: si la deriva ya había ocurrido cuando
        el poll mira por primera vez, adopta el estado malo como bueno y no
        rearma nunca. La referencia tiene que venir de un estado del que
        sabemos que está alineado, y el único momento en que lo sabemos es
        inmediatamente después de haber cargado el modelo nosotros.
        """

        self._warmed_vram = await self.resident_runner_vram()
        return self._warmed_vram

    async def realign_runner_if_drifted(self) -> bool:
        """Rearma el warmup cuando el runner residente no es el del perfil.

        **Por qué existe.** El warmup del backend pide el `num_ctx` correcto, pero
        corre una sola vez, al construir el contenedor. La VM de la GPU valida su
        arranque cargando el mismo modelo con *su* contexto
        (`deploy/gpu/validate-runtime.sh`), y cuando esa VM se reinicia el backend
        —que sigue vivo— no vuelve a hacer warmup nunca. El runner queda cargado
        con un contexto que no es el que producción pide, y **el primer turno real
        paga la recarga**: 101 s de mediana sobre cinco observaciones
        (96,3 · 100,8 · 101,0 · 101,3 · 101,7), frente a 0,55 s cuando coinciden.

        Comprobarlo después de generar no sirve: arreglaría el turno 2 y dejaría
        al primer usuario pagando, que es justo lo que esto evita. Por eso lo
        llama un poll en segundo plano y no un gancho de post-proceso.

        **La carrera con la VM, que es esperada y correcta.** Al arrancar la VM de
        la GPU habrá un vaivén en los logs: la validación carga a su contexto y
        este poll rearma al del perfil. Es un solo ciclo y nada en el sistema usa
        más de `num_ctx` tokens —`max_input_tokens` es 12 000—, así que el
        contexto grande es capacidad que nadie pide.
        """

        vram = await self.resident_runner_vram()
        if vram is None:
            # Sin runner residente el primer turno pagaría la carga entera.
            # Esta rama RECARGA el modelo, y hasta ahora se iba sin registrarlo:
            # desde fuera, «realineó sin avisar» y «no realineó» eran idénticos,
            # y eso dejó sin resolver quién devolvió el runner a 16384.
            rearmado = await self.warmup(timeout_seconds=self.timeout_seconds)
            await self.capture_runner_baseline()
            logger.info(
                "llm_chat.runner_realigned %s",
                json.dumps(
                    {
                        "motivo": "sin_runner_residente",
                        "size_vram_before": None,
                        "size_vram_after": self._warmed_vram,
                        "rearmed": rearmado,
                    },
                    sort_keys=True,
                ),
            )
            return rearmado
        if self._warmed_vram is None:
            # Sin referencia de un estado bueno no se puede decidir. No se adopta
            # la lectura actual: podría ser ya la derivada.
            return False
        desviacion = abs(vram - self._warmed_vram) / self._warmed_vram
        if desviacion <= self.RUNNER_VRAM_TOLERANCE:
            return False
        antes = vram
        rearmado = await self.warmup(timeout_seconds=self.timeout_seconds)
        # La referencia se refresca aquí y no dentro de `warmup`: ese método
        # tiene un solo trabajo —cargar el modelo con el perfil— y meterle una
        # lectura de `/api/ps` lo convertía en dos.
        await self.capture_runner_baseline()
        logger.info(
            "llm_chat.runner_realigned %s",
            json.dumps(
                {
                    "size_vram_before": antes,
                    "size_vram_after": self._warmed_vram,
                    "deviation": round(desviacion, 4),
                    "rearmed": rearmado,
                },
                sort_keys=True,
            ),
        )
        return rearmado

    async def warmup(self, *, timeout_seconds: float) -> bool:
        profile = self.warmup_profile
        payload = {
            "model": profile.model,
            "prompt": "",
            "stream": False,
            "keep_alive": profile.keep_alive,
            "options": {
                "temperature": profile.temperature,
                "num_predict": 1,
                "num_ctx": profile.num_ctx,
            },
        }
        started = time.perf_counter()
        try:
            response = await asyncio.wait_for(
                self.http_client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=timeout_seconds,
                ),
                timeout=timeout_seconds,
            )
            response.raise_for_status()
        except (asyncio.TimeoutError, httpx.HTTPError):
            self._log_failure("warmup_failed", started)
            return False
        logger.info(
            "llm_chat.warmup %s",
            json.dumps(
                {
                    "model": self.model_name,
                    "duration_ms": round((time.perf_counter() - started) * 1000),
                },
                sort_keys=True,
            ),
        )
        return True

    def _payload(self, request: ModelRequest, *, stream: bool) -> dict[str, object]:
        options: dict[str, object] = {
            "temperature": request.temperature,
            "num_predict": request.num_predict,
            "num_ctx": request.num_ctx,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "repeat_penalty": request.repeat_penalty,
        }
        messages: list[dict[str, object]] = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_prompt},
        ]
        # Replay what the model already asked for and what it got back, so the
        # next call sees its own tool use as conversation rather than being
        # asked the question again with the answers pasted in. Ollama's chat
        # API expects the assistant's tool_calls followed by one `tool`
        # message per result.
        for call, result in request.tool_exchanges:
            messages.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": call.name,
                                "arguments": call.arguments,
                            }
                        }
                    ],
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_name": result.name,
                    "content": result.error or result.content,
                }
            )
        payload: dict[str, object] = {
            "model": request.model,
            "messages": messages,
            "stream": stream,
            # For Qwen/Ollama, enabling the native thinking channel is a privacy
            # boundary: Ollama separates it into `message.thinking`, while this
            # adapter reads and streams only `message.content`. Sending false on
            # affected runtimes can place the private draft inside content.
            "think": request.thinking,
            "keep_alive": request.keep_alive,
            "options": options,
        }
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in request.tools
            ]
        # `format` and `tools` are mutually exclusive in practice: a grammar
        # that forces the answer envelope leaves no token sequence in which the
        # model could emit a tool call. The turn asks for tools first and for
        # the envelope on the call that answers, so both are never set at once.
        if request.response_schema is not None and not request.tools:
            payload["format"] = request.response_schema
        return payload

    @staticmethod
    def _tool_calls(message: dict[str, object]) -> tuple[ToolCall, ...]:
        raw_calls = message.get("tool_calls")
        if not isinstance(raw_calls, list):
            return ()
        calls: list[ToolCall] = []
        for index, raw in enumerate(raw_calls):
            if not isinstance(raw, dict):
                continue
            function = raw.get("function")
            if not isinstance(function, dict):
                continue
            name = str(function.get("name") or "").strip()
            if not name:
                continue
            arguments = function.get("arguments")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            calls.append(
                ToolCall(
                    name=name,
                    arguments=arguments if isinstance(arguments, dict) else {},
                    call_id=str(raw.get("id") or index),
                )
            )
        return tuple(calls)

    @staticmethod
    def _usage(body: dict[str, object]) -> TokenUsage:
        return TokenUsage(
            prompt_tokens=int(body.get("prompt_eval_count") or 0),
            completion_tokens=int(body.get("eval_count") or 0),
        )

    @classmethod
    def _metrics(cls, body: dict[str, object]) -> dict[str, object]:
        keys = (
            "total_duration",
            "load_duration",
            "prompt_eval_duration",
            "eval_duration",
        )
        metrics: dict[str, object] = {}
        for key in keys:
            value = body.get(key)
            if value is not None:
                metrics[f"{key}_ms"] = cls._nanoseconds_to_ms(value)
        for key in ("prompt_eval_count", "eval_count"):
            value = body.get(key)
            if value is not None:
                metrics[key] = int(value)
        return metrics

    @staticmethod
    def _nanoseconds_to_ms(value: object) -> float:
        return round(float(value) / 1_000_000, 3)

    def _log_metrics(self, metrics: dict[str, object], *, duration_ms: int) -> None:
        logger.info(
            "llm_chat.ollama_metrics %s",
            json.dumps(
                {
                    "duration_ms": duration_ms,
                    "total_duration_ms": metrics.get("total_duration_ms"),
                    "load_duration_ms": metrics.get("load_duration_ms"),
                    "prompt_eval_count": metrics.get("prompt_eval_count"),
                    "prompt_eval_duration_ms": metrics.get("prompt_eval_duration_ms"),
                    "eval_count": metrics.get("eval_count"),
                    "eval_duration_ms": metrics.get("eval_duration_ms"),
                    "gpu_active": self._runtime_snapshot.get("gpu_active"),
                    "gpu_memory_bytes": self._runtime_snapshot.get("gpu_memory_bytes"),
                    "inference_device": self._runtime_snapshot.get("inference_device"),
                },
                sort_keys=True,
            ),
        )

    def _log_failure(
        self,
        error_type: str,
        started: float,
        *,
        status_code: int | None = None,
    ) -> None:
        logger.info(
            "llm_chat.provider_error %s",
            json.dumps(
                {
                    "error_type": error_type,
                    "duration_ms": round((time.perf_counter() - started) * 1000),
                    "status_code": status_code,
                },
                sort_keys=True,
            ),
        )
