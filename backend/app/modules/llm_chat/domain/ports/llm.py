from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from app.modules.llm_chat.domain.entities import (
    ModelRequest,
    ModelResponse,
    ModelStreamChunk,
)


class LLMGenerationPort(Protocol):
    """Minimal generation capability consumed by chat use cases."""

    model_name: str

    async def generate(self, request: ModelRequest) -> ModelResponse: ...

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamChunk]: ...


@runtime_checkable
class LLMProvider(LLMGenerationPort, Protocol):
    """Full remote-provider boundary owned by runtime composition."""

    async def identity_status(self) -> dict[str, object]: ...

    async def health(self) -> bool: ...

    async def runtime_status(self) -> dict[str, object]: ...
