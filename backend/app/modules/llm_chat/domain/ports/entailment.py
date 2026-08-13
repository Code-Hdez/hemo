from __future__ import annotations

from typing import Protocol


class ClaimEntailmentPort(Protocol):
    """Does a corpus sentence *imply* the Spanish claim that cites it?

    The three-valued answer is the whole point of the boundary. ``True`` and
    ``False`` are verdicts; ``None`` means the verifier could not produce one
    (model still loading, unavailable, or over its deadline) and the caller
    must fall back to the lexical rule that shipped before it. A verifier that
    cannot answer never grants support on its own.
    """

    def entails(self, *, premise: str, hypothesis: str) -> bool | None: ...
