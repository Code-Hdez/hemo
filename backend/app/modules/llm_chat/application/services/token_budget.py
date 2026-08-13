from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


class TokenizerUnavailableError(RuntimeError):
    """Raised when configuration explicitly requests a tokenizer that is unavailable.

    Distinct from "no tokenizer configured at all" (a supported, honestly
    labeled heuristic mode): this is raised only when a specific asset or
    requirement was named and could not be satisfied, so a broken request
    never silently falls back to a different counting formula.
    """


# Public, documented ChatML wire format (`<|im_start|>{role}\n{content}<|im_end|>\n`)
# applied server-side by Qwen-family chat templates. This is metadata about a
# wire protocol, not a downloadable model/tokenizer artifact, so hardcoding it
# lets the counter render "the same template, roles and separators" the
# provider will apply without ever contacting it or fetching anything.
_ROLE_OPEN = "<|im_start|>"
_ROLE_CLOSE = "<|im_end|>\n"


def render_chat_template(*, system_prompt: str, user_prompt: str) -> str:
    """Render the request exactly as the ChatML-templated provider will see it.

    Used for counting only. The literal payload sent to the provider is still
    the plain ``system_prompt``/``user_prompt`` pair (the provider applies its
    own template server-side) — this rendering exists so the token count
    reflects role markers and separators instead of two isolated counts glued
    together with a flat fudge factor.
    """
    return (
        f"{_ROLE_OPEN}system\n{system_prompt}{_ROLE_CLOSE}"
        f"{_ROLE_OPEN}user\n{user_prompt}{_ROLE_CLOSE}"
        f"{_ROLE_OPEN}assistant\n"
    )


class TokenCounter:
    """Count prompt tokens with an optional provider-matching tokenizer.

    Production can point ``tokenizer_path`` at the tokenizer JSON that belongs
    to the deployed model runtime. Environments without that asset use a
    conservative UTF-8/lexical estimate, never a raw character limit — and
    ``exact`` always reports honestly which mode produced a given count, so
    callers never label a heuristic as an exact count.
    """

    def __init__(
        self,
        tokenizer_path: str | Path | None = None,
        *,
        model_id: str = "",
        required: bool = False,
        expected_sha256: str | None = None,
    ) -> None:
        self._tokenizer = None
        self._model_id = model_id
        self._artifact_sha256: str | None = None
        if tokenizer_path:
            path = Path(tokenizer_path)
            if expected_sha256:
                # Identity by filename alone proves nothing: a wrong or
                # tampered file can carry the configured name. Hashing the
                # bytes actually loaded ties the counter to a specific,
                # operator-verified artifact instead.
                try:
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                except OSError as exc:
                    raise TokenizerUnavailableError(
                        f"configured tokenizer at {tokenizer_path!r} could not "
                        f"be read to verify its digest: {exc}"
                    ) from exc
                if digest.casefold() != expected_sha256.strip().casefold():
                    raise TokenizerUnavailableError(
                        f"configured tokenizer at {tokenizer_path!r} does not "
                        "match CHAT_TOKENIZER_SHA256"
                    )
                self._artifact_sha256 = digest
            try:
                from tokenizers import Tokenizer

                self._tokenizer = Tokenizer.from_file(str(path))
            except Exception as exc:
                # An explicitly configured tokenizer that fails to load must
                # never fall back to the heuristic silently: that would send
                # a request whose size was never actually verified against
                # the model that will receive it.
                raise TokenizerUnavailableError(
                    f"configured tokenizer at {tokenizer_path!r} could not be "
                    f"loaded: {exc}"
                ) from exc
        elif required:
            raise TokenizerUnavailableError(
                "an exact tokenizer is required by configuration "
                "(CHAT_TOKENIZER_REQUIRED) but no tokenizer_path was provided "
                "(CHAT_TOKENIZER_JSON)"
            )

    @property
    def exact(self) -> bool:
        return self._tokenizer is not None

    @property
    def identity(self) -> str:
        """Safe-for-logs identity of the active counting mode, never content."""
        if self._tokenizer is not None:
            suffix = (
                f":sha256-{self._artifact_sha256[:12]}"
                if self._artifact_sha256
                else ""
            )
            return f"exact:{self._model_id or 'tokenizer'}{suffix}"
        return "heuristic:utf8-lexical-chatml-v1"

    def count(self, text: str) -> int:
        value = str(text or "")
        if not value:
            return 0
        if self._tokenizer is not None:
            return len(self._tokenizer.encode(value).ids)
        lexical = len(re.findall(r"\w+|[^\w\s]", value, flags=re.UNICODE))
        utf8_estimate = math.ceil(len(value.encode("utf-8")) / 3)
        return max(lexical, utf8_estimate)

    def count_request(self, *, system_prompt: str, user_prompt: str) -> int:
        """Count one complete provider request using the real chat template.

        This is the canonical way to price a system/user pair: it renders the
        same ChatML wire form the provider applies server-side and counts it
        as a single string, folding in role markers and separators instead of
        summing two isolated counts plus an unrelated fixed constant.
        """
        return self.count(
            render_chat_template(system_prompt=system_prompt, user_prompt=user_prompt)
        )

    def count_schema(self, schema: dict[str, Any] | None) -> int:
        """Count the exact JSON Schema serialization sent via ``format``/``response_format``.

        Uses the same compact, no-whitespace separators the provider clients
        (``openai_compatible_client.py``) send, so this matches the schema's
        real wire cost instead of a pretty-printed approximation.
        """
        if not schema:
            return 0
        return self.count(json.dumps(schema, ensure_ascii=False, separators=(",", ":")))


def input_token_budget(
    *,
    num_ctx: int,
    num_predict: int,
    reserve_tokens: int,
    max_input_tokens: int,
) -> int:
    if max_input_tokens < 1:
        raise ValueError("max_input_tokens must be positive")
    if max_input_tokens + num_predict + reserve_tokens > num_ctx:
        raise ValueError("the configured input budget does not fit the context")
    return int(max_input_tokens)


__all__ = [
    "TokenCounter",
    "TokenizerUnavailableError",
    "input_token_budget",
    "render_chat_template",
]
