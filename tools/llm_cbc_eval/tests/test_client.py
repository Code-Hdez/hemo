from __future__ import annotations

from uuid import UUID

from tools.llm_cbc_eval.src.client import ChatEvalClient
from tools.llm_cbc_eval.src.models import EvalConfig


def test_client_generates_browser_session_header() -> None:
    with ChatEvalClient(EvalConfig.from_mapping({})) as client:
        header = client._client.headers["X-HemoVet-Browser-Session-ID"]
        assert header == client.browser_session_id
        assert UUID(header).version == 4


def test_client_uses_configured_browser_session_header() -> None:
    browser_session_id = "01234567-89ab-4def-8123-456789abcdef"
    config = EvalConfig.from_mapping(
        {"context": {"browser_session_id": browser_session_id}}
    )
    with ChatEvalClient(config) as client:
        assert (
            client._client.headers["X-HemoVet-Browser-Session-ID"]
            == browser_session_id
        )
