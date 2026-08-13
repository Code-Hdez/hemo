from __future__ import annotations

import re


ASSISTANT_NAME = "HemoVet"
EDUCATIONAL_WARNING = (
    "La respuesta es educativa y no sustituye una evaluación veterinaria"
)

_ASSISTANT_NAME_VARIANT = re.compile(
    r"\bHemo(?:[\s_-]+)?(?:Vet|Vin)\b",
    flags=re.IGNORECASE,
)


def enforce_assistant_identity(text: str) -> str:
    """Normalize the protected product name without authoring the response.

    User-visible conversational wording is produced by the configured LLM. This
    post-processing guard only prevents spelling variants of the product name
    from escaping into the response or restored history.
    """

    return _ASSISTANT_NAME_VARIANT.sub(ASSISTANT_NAME, str(text or ""))
