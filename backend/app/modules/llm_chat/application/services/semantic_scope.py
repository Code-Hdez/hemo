"""Is this question inside HemoVet's domain? Judged by meaning, not vocabulary.

Why this exists
---------------
``socratic-tutor`` gives that judgement to a small model with a prose policy
whose first line is *"Judge the requested outcome of the latest student
message in its conversation, not isolated words"*. Ours was a set of regular
expressions, and the failure mode is the one the audit named: measured on the
project's own case files, ordinary hematology was refused as off-topic —
"explícame el leucograma de estrés", "los agregados plaquetarios como
artefacto preanalítico" — because the words were absent from a list.

Three ways to buy that judgement were weighed against this hardware:

* a 4B on the GPU: ~1-2 s a turn, needs ``OLLAMA_MAX_LOADED_MODELS=2`` and
  competes for the 5.1 GB the 27B leaves free;
* a 4B on the production CPU: 7-13 s a turn on 8 vCPU with no GPU, which is a
  quarter of the whole latency budget spent deciding whether to answer;
* the multilingual NLI model this repository already vendors and measures at
  **123 ms on CPU** (``infrastructure/entailment.py``).

The third is two orders of magnitude cheaper than the second and needs no
deployment change at all, so it is the one used here. What it cannot do is
write prose — no ``STEER`` rewrite, no ``SHORT_CIRCUIT`` text. It does not need
to: the guard only ever needed the *verdict*.

The line this must not cross
----------------------------
It judges **scope**, never clinical safety. Scope is a semantic question and
the place where the closed lists actually fail. Whether a message asks for a
dose stays with the deterministic rules, and this classifier cannot unlock one:
it is consulted only to *rescue* a question refused as off-domain, never to
authorize a clinical action. Getting scope wrong shows an unhelpful answer;
getting a dose wrong is a different kind of mistake, and it does not get to be
made by a model whose threshold was fitted on a bench.
"""

from __future__ import annotations

from dataclasses import dataclass

from typing import Protocol


class ScorerPort(Protocol):
    """Returns how strongly a premise entails a hypothesis, or ``None``."""

    def score(self, *, premise: str, hypothesis: str) -> float | None: ...

# Hypotheses, not keywords. Each states an *outcome the user is asking for*,
# which is the thing the audit says to judge. Kept few and plainly worded: an
# NLI model reads them as sentences, and a long list is both slower and harder
# to reason about when one of them misfires.
IN_SCOPE_HYPOTHESES = (
    "La persona pregunta sobre un hemograma, un análisis de sangre o un "
    "parámetro hematológico.",
    "La persona pregunta sobre la salud, los cuidados o una enfermedad de un "
    "perro.",
    "La persona pregunta el significado, la causa o la interpretación de un "
    "valor de laboratorio.",
    "La persona pregunta qué es un término de hematología veterinaria.",
)

OUT_OF_SCOPE_HYPOTHESES = (
    "La persona pregunta por un tema ajeno a la veterinaria, como política, "
    "deportes, cocina, viajes o entretenimiento.",
    "La persona pide una tarea de informática, programación o matemáticas.",
    "La persona pregunta por el clima, una noticia o un dato de cultura "
    "general.",
)


@dataclass(frozen=True, slots=True)
class SemanticScopeClassifier:
    """A second opinion on scope, which may only ever widen what is answered.

    Compares hypotheses instead of testing them one at a time against a
    threshold. That distinction is not stylistic: measured on the held-out half
    of the bench, first-past-the-threshold called 23 of 23 off-domain questions
    in-domain — "cuéntame un chiste", "¿cuál es la capital de Bolivia?" — for
    the mechanical reason that the in-scope hypotheses were tried first and one
    always cleared 0.80. Every error pointed the same way, which is the signal
    that the formulation was wrong rather than the threshold.
    """

    entailment: ScorerPort
    # How much the winning reading must beat the losing one. Comparing raw
    # maxima makes the verdict turn on noise when both readings are weak; a
    # margin turns "the model slightly prefers one" into an abstention, and an
    # abstention costs nothing because the deterministic rule still stands.
    margin: float = 0.15

    def is_in_scope(self, question: str) -> bool | None:
        """``None`` when the model could not answer, and that is not a verdict.

        The verifier returns ``None`` while loading, when unavailable, or past
        its deadline. Reading that as "out of scope" would make an unavailable
        model refuse questions; reading it as "in scope" would make an
        unavailable model authorize them. It is neither: the caller keeps the
        deterministic verdict it already had.
        """

        text = str(question or "").strip()
        if not text:
            return None
        inside = self._best(text, IN_SCOPE_HYPOTHESES)
        outside = self._best(text, OUT_OF_SCOPE_HYPOTHESES)
        if inside is None or outside is None:
            return None
        if inside - outside >= self.margin:
            return True
        if outside - inside >= self.margin:
            return False
        # Recognising nothing is not evidence the question is off-domain; it is
        # evidence the hypotheses did not cover it. Abstaining leaves the
        # deterministic verdict standing, which is the conservative direction:
        # this classifier exists to rescue questions the rules refused, so
        # silence from it can only ever mean "no rescue", never "refuse".
        return None

    def _best(self, question: str, hypotheses: tuple[str, ...]) -> float | None:
        best: float | None = None
        for hypothesis in hypotheses:
            score = self.entailment.score(premise=question, hypothesis=hypothesis)
            if score is None:
                continue
            best = score if best is None else max(best, score)
        return best


__all__ = [
    "IN_SCOPE_HYPOTHESES",
    "OUT_OF_SCOPE_HYPOTHESES",
    "SemanticScopeClassifier",
]
