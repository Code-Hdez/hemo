from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.modules.llm_chat.domain.entities import ModelRequest
from app.modules.llm_chat.domain.generation_config import EffectiveGenerationProfile
from app.modules.llm_chat.domain.provider_contract import PROVIDER_CORRELATION_HEADER
from app.modules.llm_chat.infrastructure.llm.openai_compatible_client import (
    LLMRuntimeError,
    OllamaNativeLLMClient,
    OpenAICompatibleLLMClient,
    _health_timeout,
)


def _profile(
    *,
    model: str = "qwen3:4b",
    provider: str = "ollama",
    num_predict: int = 220,
    num_ctx: int = 4096,
    temperature: float = 0.1,
    top_p: float = 0.9,
    top_k: int = 40,
    repeat_penalty: float = 1.1,
    thinking: bool = False,
    timeout_seconds: float = 30,
    keep_alive: int | str = "30m",
) -> EffectiveGenerationProfile:
    return EffectiveGenerationProfile(
        name="test_profile",
        kind="main",
        provider=provider,
        model=model,
        num_ctx=num_ctx,
        max_input_tokens=1,
        context_reserve_tokens=1,
        num_predict=num_predict,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        repeat_penalty=repeat_penalty,
        thinking=thinking,
        timeout_seconds=timeout_seconds,
        keep_alive=keep_alive,
    )


def _request(
    profile: EffectiveGenerationProfile,
    *,
    system_prompt: str = "sistema",
    user_prompt: str = "pregunta",
    **overrides: object,
) -> ModelRequest:
    fields: dict[str, object] = {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "thinking": profile.thinking,
        "model": profile.model,
        "profile_name": profile.name,
        "profile_kind": profile.kind,
        "num_predict": profile.num_predict,
        "num_ctx": profile.num_ctx,
        "max_input_tokens": profile.max_input_tokens,
        "context_reserve_tokens": profile.context_reserve_tokens,
        "temperature": profile.temperature,
        "top_p": profile.top_p,
        "top_k": profile.top_k,
        "repeat_penalty": profile.repeat_penalty,
        "timeout_seconds": profile.timeout_seconds,
        "keep_alive": profile.keep_alive,
    }
    fields.update(overrides)
    return ModelRequest(**fields)


def _ollama_client(
    http: httpx.AsyncClient,
    *,
    base_url: str = "http://ollama:11434/",
    model_name: str = "qwen3:4b",
    timeout_seconds: float = 30,
    warmup_profile: EffectiveGenerationProfile | None = None,
) -> OllamaNativeLLMClient:
    return OllamaNativeLLMClient(
        http_client=http,
        base_url=base_url,
        model_name=model_name,
        timeout_seconds=timeout_seconds,
        warmup_profile=warmup_profile
        or _profile(model=model_name, timeout_seconds=timeout_seconds),
    )


def _openai_client(
    http: httpx.AsyncClient,
    *,
    base_url: str,
    model_name: str,
    timeout_seconds: float,
) -> OpenAICompatibleLLMClient:
    return OpenAICompatibleLLMClient(
        http_client=http,
        base_url=base_url,
        model_name=model_name,
        timeout_seconds=timeout_seconds,
    )


def test_generate_signals_no_reasoning_effort_when_the_request_disables_thinking() -> None:
    """``generate`` no longer overrides the request: the reasoning-effort
    override is sent exactly when ``request.thinking`` is ``False`` (see
    ``if not request.thinking:`` in the client), not unconditionally. Whether
    a profile runs with thinking enabled is decided upstream, when
    ``GenerationProfileSettings``/``PromptBuilder`` build the request.
    """
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "choices": [
                    {
                        "message": {
                            "content": "Respuesta segura [S1].",
                            "reasoning": "razonamiento privado",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 25, "completion_tokens": 8},
            },
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = _openai_client(
        http,
        base_url="http://ollama:11434/v1",
        model_name="qwen3:4b",
        timeout_seconds=30,
    )

    result = asyncio.run(
        client.generate(
            _request(
                _profile(model="qwen3:4b", num_predict=512, timeout_seconds=30),
                user_prompt="pregunta [S1]",
                thinking=False,
            )
        )
    )
    asyncio.run(http.aclose())

    assert captured["reasoning_effort"] == "none"
    assert captured["reasoning"] == {"effort": "none"}
    assert captured["stream"] is False
    assert result.text == "Respuesta segura [S1]."
    assert "razonamiento" not in result.text
    assert result.usage.prompt_tokens == 25


def test_provider_request_propagates_correlation_header_outside_the_prompt() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["correlation_id"] = request.headers[PROVIDER_CORRELATION_HEADER]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "choices": [
                    {
                        "message": {"content": "Respuesta segura."},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = _openai_client(
        http,
        base_url="http://runtime:8000/v1",
        model_name="qwen3:4b",
        timeout_seconds=5,
    )
    asyncio.run(
        client.generate(
            _request(
                _profile(model="qwen3:4b", num_predict=128, timeout_seconds=5),
                thinking=False,
                correlation_id="request-123",
            )
        )
    )
    asyncio.run(http.aclose())

    assert captured["correlation_id"] == "request-123"
    assert "request-123" not in json.dumps(captured["payload"])


def test_openai_compatible_generate_forwards_strict_json_schema() -> None:
    captured: dict[str, object] = {}
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "choices": [
                    {
                        "message": {"content": '{"answer":"Hola"}'},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = _openai_client(
        http,
        base_url="http://runtime:8000/v1",
        model_name="qwen3:4b",
        timeout_seconds=5,
    )
    result = asyncio.run(
        client.generate(
            _request(
                _profile(model="qwen3:4b", num_predict=128, timeout_seconds=5),
                thinking=False,
                response_schema=schema,
            )
        )
    )
    asyncio.run(http.aclose())

    assert captured["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "hemovet_chat_response",
            "strict": True,
            "schema": schema,
        },
    }
    assert result.text == '{"answer":"Hola"}'


def test_health_returns_false_on_runtime_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "down"})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = _openai_client(
        http,
        base_url="http://ollama:11434/v1",
        model_name="qwen3:4b",
        timeout_seconds=1,
    )

    assert asyncio.run(client.health()) is False
    asyncio.run(http.aclose())


def test_provider_health_timeout_fits_inside_container_health_deadline() -> None:
    assert _health_timeout(90) == 1.5
    assert _health_timeout(httpx.Timeout(30, connect=5, pool=5)) == 1.5
    assert _health_timeout(0.75) == 0.75


def test_ollama_runtime_status_reports_real_gpu_residency() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/ps"
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "qwen3:4b",
                        "model": "qwen3:4b",
                        "size": 2_900_000_000,
                        "size_vram": 2_862_000_000,
                    }
                ]
            },
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = _ollama_client(
        http,
        base_url="http://ollama:11434",
        model_name="qwen3:4b",
        timeout_seconds=30,
        warmup_profile=_profile(model="qwen3:4b", keep_alive=-1, timeout_seconds=30),
    )

    status = asyncio.run(client.runtime_status())
    asyncio.run(http.aclose())

    assert status == {
        "provider": "ollama",
        "model": "qwen3:4b",
        "loaded": True,
        "gpu_active": True,
        "gpu_memory_bytes": 2_862_000_000,
        "model_size_bytes": 2_900_000_000,
        "gpu_residency_ratio": 0.9869,
        "inference_device": "full_gpu",
        "digest": None,
        "quantization": None,
    }


def test_ollama_identity_uses_installed_artifact_not_vram_residency() -> None:
    digest = "0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "qwen3:4b",
                            "digest": digest,
                            "details": {"quantization_level": "Q4_K_M"},
                        }
                    ]
                },
            )
        if request.url.path == "/api/show":
            assert json.loads(request.content) == {"model": "qwen3:4b"}
            return httpx.Response(
                200,
                json={"details": {"quantization_level": "Q4_K_M"}},
            )
        if request.url.path == "/api/ps":
            return httpx.Response(200, json={"models": []})
        raise AssertionError(request.url.path)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = _ollama_client(
        http,
        base_url="http://ollama:11434",
        model_name="qwen3:4b",
        timeout_seconds=30,
        warmup_profile=_profile(model="qwen3:4b", keep_alive=-1, timeout_seconds=30),
    )

    identity = asyncio.run(client.identity_status())
    residency = asyncio.run(client.runtime_status())
    asyncio.run(http.aclose())

    assert identity == {
        "provider": "ollama",
        "model": "qwen3:4b",
        "installed": True,
        "digest": digest,
        "quantization": "Q4_K_M",
    }
    assert residency["loaded"] is False
    assert residency["inference_device"] == "not_loaded"


def test_health_requires_the_configured_openai_compatible_model() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        return httpx.Response(200, json={"data": [{"id": "qwen3:8b"}]})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = _openai_client(
        http,
        base_url="http://runtime:8000/v1",
        model_name="qwen3:8b",
        timeout_seconds=5,
    )

    assert asyncio.run(client.health()) is True
    asyncio.run(http.aclose())


def test_openai_compatible_stream_yields_content_usage_and_done() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["stream"] is True
        return httpx.Response(
            200,
            content=(
                b'data: {"model":"qwen3:8b","choices":[{"delta":{"content":"Hola "},"finish_reason":null}]}\n\n'
                b'data: {"model":"qwen3:8b","choices":[{"delta":{"content":"Luna."},"finish_reason":"stop"}]}\n\n'
                b'data: {"choices":[],"usage":{"prompt_tokens":10,"completion_tokens":3}}\n\n'
                b"data: [DONE]\n\n"
            ),
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = _openai_client(
        http,
        base_url="http://runtime:8000/v1",
        model_name="qwen3:8b",
        timeout_seconds=5,
    )

    async def collect():
        return [
            chunk
            async for chunk in client.stream(
                _request(
                    _profile(model="qwen3:8b", num_predict=384, timeout_seconds=5),
                    thinking=False,
                )
            )
        ]

    chunks = asyncio.run(collect())
    asyncio.run(http.aclose())
    assert [chunk.text for chunk in chunks if chunk.text] == ["Hola ", "Luna."]
    assert chunks[-1].done is True
    assert chunks[-1].usage.prompt_tokens == 10
    assert chunks[-1].usage.completion_tokens == 3


def test_openai_compatible_stream_rejects_eof_without_terminal_marker() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=(
                b'data: {"model":"qwen3:8b","choices":[{"delta":{"content":"Texto parcial."},"finish_reason":null}]}\n\n'
            ),
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = _openai_client(
        http,
        base_url="http://runtime:8000/v1",
        model_name="qwen3:8b",
        timeout_seconds=5,
    )

    async def collect():
        return [
            chunk
            async for chunk in client.stream(
                _request(
                    _profile(model="qwen3:8b", num_predict=384, timeout_seconds=5),
                    thinking=False,
                )
            )
        ]

    with pytest.raises(LLMRuntimeError, match="provider_invalid_response"):
        asyncio.run(collect())
    asyncio.run(http.aclose())


def test_generate_logs_timeout_type_without_prompt_content(caplog) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    caplog.set_level("INFO", logger="uvicorn.error.hemovet.llm_chat")
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = _openai_client(
        http,
        base_url="http://ollama:11434/v1",
        model_name="qwen3:4b",
        timeout_seconds=180,
    )

    with pytest.raises(LLMRuntimeError):
        asyncio.run(
            client.generate(
                _request(
                    _profile(model="qwen3:4b", num_predict=384, timeout_seconds=180),
                    system_prompt="prompt privado",
                    user_prompt="pregunta privada",
                    thinking=False,
                )
            )
        )
    asyncio.run(http.aclose())

    assert '"error_type": "read_timeout"' in caplog.text
    assert "prompt privado" not in caplog.text
    assert "pregunta privada" not in caplog.text


def test_ollama_native_generate_records_native_metrics_and_keep_alive() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {"role": "assistant", "content": "Respuesta segura [S1]."},
                "done": True,
                "done_reason": "stop",
                "total_duration": 2_000_000_000,
                "load_duration": 100_000_000,
                "prompt_eval_count": 40,
                "prompt_eval_duration": 800_000_000,
                "eval_count": 12,
                "eval_duration": 1_100_000_000,
            },
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    profile = _profile(
        model="qwen3:4b", num_predict=220, timeout_seconds=30, keep_alive="30m"
    )
    client = _ollama_client(
        http,
        base_url="http://ollama:11434/",
        model_name="qwen3:4b",
        timeout_seconds=30,
        warmup_profile=profile,
    )

    result = asyncio.run(
        client.generate(
            _request(profile, user_prompt="pregunta [S1]", thinking=True)
        )
    )
    asyncio.run(http.aclose())

    assert captured["path"] == "/api/chat"
    assert captured["stream"] is False
    assert captured["think"] is True
    assert captured["keep_alive"] == "30m"
    assert captured["options"] == {
        "temperature": 0.1,
        "num_predict": 220,
        "num_ctx": 4096,
        "top_p": 0.9,
        "top_k": 40,
        "repeat_penalty": 1.1,
    }
    assert result.text == "Respuesta segura [S1]."
    assert result.usage.prompt_tokens == 40
    assert result.usage.completion_tokens == 12
    assert result.provider_metrics["load_duration_ms"] == 100.0
    assert result.provider_metrics["prompt_eval_duration_ms"] == 800.0
    assert result.provider_metrics["eval_duration_ms"] == 1100.0


def test_ollama_native_generate_forwards_json_schema_as_format() -> None:
    captured: dict[str, object] = {}
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {"role": "assistant", "content": '{"answer":"Hola"}'},
                "done": True,
                "done_reason": "stop",
            },
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    profile = _profile(model="qwen3:4b", num_predict=128, timeout_seconds=5, keep_alive="30m")
    client = _ollama_client(
        http,
        base_url="http://ollama:11434",
        model_name="qwen3:4b",
        timeout_seconds=5,
        warmup_profile=profile,
    )
    result = asyncio.run(
        client.generate(
            _request(profile, thinking=False, response_schema=schema)
        )
    )
    asyncio.run(http.aclose())

    assert captured["format"] == schema
    assert result.text == '{"answer":"Hola"}'


def test_ollama_native_generate_prefers_request_profile_options() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "llama3.2:3b",
                "message": {"role": "assistant", "content": "Respuesta segura [S1]."},
                "done": True,
                "done_reason": "stop",
                "total_duration": 1_000_000_000,
                "prompt_eval_count": 30,
                "eval_count": 8,
            },
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    profile = _profile(
        model="llama3.2:3b",
        num_predict=160,
        num_ctx=3072,
        timeout_seconds=30,
        keep_alive="30m",
    )
    client = _ollama_client(
        http,
        base_url="http://ollama:11434/",
        model_name="llama3.2:3b",
        timeout_seconds=30,
        warmup_profile=profile,
    )

    result = asyncio.run(
        client.generate(
            _request(
                profile,
                user_prompt="pregunta [S1]",
                thinking=False,
                profile_name="definition",
            )
        )
    )
    asyncio.run(http.aclose())

    assert captured["model"] == "llama3.2:3b"
    assert captured["options"] == {
        "temperature": 0.1,
        "num_predict": 160,
        "num_ctx": 3072,
        "top_p": 0.9,
        "top_k": 40,
        "repeat_penalty": 1.1,
    }
    assert result.model == "llama3.2:3b"


def test_ollama_native_generate_forwards_thinking_and_num_predict_from_the_request() -> None:
    """The client no longer owns a privacy override: the thinking flag and every
    generation option come from ``ModelRequest`` verbatim (``_payload`` reads
    ``request.thinking``/``request.num_predict`` directly, nothing from the
    client). Whether a profile is safe to run with thinking enabled is decided
    upstream, when ``GenerationProfileSettings``/``PromptBuilder`` build the
    request.
    """
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {
                    "role": "assistant",
                    "content": "No soy una persona; soy la IA de HemoVet.",
                    "thinking": "private draft that must never be returned",
                },
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 20,
                "eval_count": 12,
            },
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    profile = _profile(model="qwen3:4b", num_predict=384, timeout_seconds=30, keep_alive="30m")
    client = _ollama_client(
        http,
        base_url="http://ollama:11434/",
        model_name="qwen3:4b",
        timeout_seconds=30,
        warmup_profile=profile,
    )

    result = asyncio.run(
        client.generate(
            _request(profile, thinking=False, num_predict=120)
        )
    )
    asyncio.run(http.aclose())

    assert captured["think"] is False
    assert captured["options"]["num_predict"] == 120
    assert result.text == "No soy una persona; soy la IA de HemoVet."
    assert "private draft" not in result.text


def test_ollama_native_warmup_uses_generate_endpoint_without_blocking_chat() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"done": True})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = _ollama_client(
        http,
        base_url="http://ollama:11434/",
        model_name="llama3.2:3b",
        timeout_seconds=30,
        warmup_profile=_profile(
            model="llama3.2:3b", num_predict=220, timeout_seconds=30, keep_alive="30m"
        ),
    )

    warmed = asyncio.run(client.warmup(timeout_seconds=5))
    asyncio.run(http.aclose())

    assert warmed is True
    assert captured["path"] == "/api/generate"
    assert captured["model"] == "llama3.2:3b"
    assert captured["prompt"] == ""
    assert captured["keep_alive"] == "30m"
    assert captured["options"]["num_predict"] == 1


@pytest.mark.parametrize("keep_alive", ["-1", "0"])
def test_ollama_native_keep_alive_sentinels_are_numeric(keep_alive: str) -> None:
    payloads: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payloads.append(json.loads(request.content))
        if request.url.path == "/api/generate":
            return httpx.Response(200, json={"done": True})
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {"role": "assistant", "content": "Respuesta."},
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 4,
                "eval_count": 2,
            },
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    profile = _profile(
        model="qwen3:4b", num_predict=220, timeout_seconds=30, keep_alive=int(keep_alive)
    )
    client = _ollama_client(
        http,
        base_url="http://ollama:11434/",
        model_name="qwen3:4b",
        timeout_seconds=30,
        warmup_profile=profile,
    )

    asyncio.run(
        client.generate(_request(profile, thinking=False))
    )
    assert asyncio.run(client.warmup(timeout_seconds=5)) is True
    asyncio.run(http.aclose())

    expected = int(keep_alive)
    assert payloads[0]["keep_alive"] == expected
    assert payloads[1]["keep_alive"] == expected


def test_ollama_native_stream_yields_deltas_and_final_metrics() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert payload["stream"] is True
        return httpx.Response(
            200,
            content=(
                b'{"message":{"content":"Respuesta "},"done":false}\n'
                b'{"message":{"content":"segura [S1]."},"done":false}\n'
                b'{"model":"qwen3:4b","done":true,"done_reason":"stop",'
                b'"total_duration":2000000000,"load_duration":0,'
                b'"prompt_eval_count":40,"prompt_eval_duration":800000000,'
                b'"eval_count":12,"eval_duration":1100000000}\n'
            ),
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    profile = _profile(model="qwen3:4b", num_predict=220, timeout_seconds=30, keep_alive="30m")
    client = _ollama_client(
        http,
        base_url="http://ollama:11434/",
        model_name="qwen3:4b",
        timeout_seconds=30,
        warmup_profile=profile,
    )

    async def collect():
        return [
            chunk
            async for chunk in client.stream(
                _request(profile, user_prompt="pregunta [S1]", thinking=False)
            )
        ]

    chunks = asyncio.run(collect())
    asyncio.run(http.aclose())

    assert [chunk.text for chunk in chunks if chunk.text] == [
        "Respuesta ",
        "segura [S1].",
    ]
    assert chunks[-1].done is True
    assert chunks[-1].usage.prompt_tokens == 40
    assert chunks[-1].usage.completion_tokens == 12
    assert chunks[-1].provider_metrics["total_duration_ms"] == 2000.0


def test_ollama_native_stream_rejects_eof_without_done_marker() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b'{"message":{"content":"Respuesta parcial."},"done":false}\n',
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    profile = _profile(model="qwen3:4b", num_predict=220, timeout_seconds=30, keep_alive="30m")
    client = _ollama_client(
        http,
        base_url="http://ollama:11434/",
        model_name="qwen3:4b",
        timeout_seconds=30,
        warmup_profile=profile,
    )

    async def collect():
        return [
            chunk
            async for chunk in client.stream(_request(profile, thinking=False))
        ]

    with pytest.raises(LLMRuntimeError, match="ollama_invalid_response"):
        asyncio.run(collect())
    asyncio.run(http.aclose())


def test_ollama_native_stream_refreshes_stale_gpu_residency_after_generation() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path == "/api/ps":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "qwen3:4b",
                            "model": "qwen3:4b",
                            "size_vram": 2_862_000_000,
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            content=(
                b'{"message":{"content":"Respuesta segura."},"done":false}\n'
                b'{"model":"qwen3:4b","done":true,"done_reason":"stop",'
                b'"prompt_eval_count":10,"eval_count":3}\n'
            ),
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    profile = _profile(model="qwen3:4b", num_predict=220, timeout_seconds=30, keep_alive=-1)
    client = _ollama_client(
        http,
        base_url="http://ollama:11434/",
        model_name="qwen3:4b",
        timeout_seconds=30,
        warmup_profile=profile,
    )
    client._runtime_snapshot.update(
        {"loaded": False, "gpu_active": False, "inference_device": "not_loaded"}
    )

    async def collect():
        return [
            chunk
            async for chunk in client.stream(_request(profile, thinking=False))
        ]

    chunks = asyncio.run(collect())
    asyncio.run(http.aclose())

    assert chunks[-1].done is True
    assert paths == ["/api/chat", "/api/ps"]
    assert client._runtime_snapshot["gpu_active"] is True
    # Without Ollama's total model size the client must not claim full GPU
    # residency merely because ``size_vram`` is non-zero.
    assert client._runtime_snapshot["inference_device"] == "mixed_cpu_gpu"
