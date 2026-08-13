#!/usr/bin/env python3
"""Measure any documentary-support verifier against the bilingual bench.

The bench (``backend/tests/data/bilingual_support_bench.jsonl``) pairs a
verbatim corpus sentence with a Spanish claim that is either faithful to it or
unsafe in one specific way.  This runner reports the two error kinds that do
not cost the same: a *false accept* delivers an unsupported clinical statement
to the user, a *false reject* kills a correct turn — the failure the LLM audit
found returning HTTP 502.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
DEFAULT_BENCH = BACKEND_ROOT / "tests" / "data" / "bilingual_support_bench.jsonl"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

Verifier = Callable[[str, str], bool]
# Generous on purpose: the first run also downloads 1.1 GB from the Hub.
MODEL_LOAD_BUDGET_SECONDS = 900.0


class BenchError(RuntimeError):
    """El banco o el verificador no cumplen su contrato."""


@dataclass(frozen=True, slots=True)
class BenchCase:
    case_id: str
    source_ref: str
    source_lang: str
    source_sentence: str
    claim_es: str
    expected: bool
    category: str


@dataclass(frozen=True, slots=True)
class BenchResult:
    total: int
    correct: int
    false_accepts: tuple[BenchCase, ...]
    false_rejects: tuple[BenchCase, ...]


_REQUIRED_FIELDS = (
    "case_id",
    "source_ref",
    "source_lang",
    "source_sentence",
    "claim_es",
    "expected",
    "category",
)


def load_bench(path: Path) -> tuple[BenchCase, ...]:
    cases: list[BenchCase] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BenchError(f"Línea {number}: JSON inválido.") from exc
        missing = [field for field in _REQUIRED_FIELDS if field not in payload]
        if missing:
            raise BenchError(f"Línea {number}: faltan campos {missing}.")
        if not isinstance(payload["expected"], bool):
            raise BenchError(f"Línea {number}: `expected` debe ser booleano.")
        case = BenchCase(**{field: payload[field] for field in _REQUIRED_FIELDS})
        if case.case_id in seen:
            raise BenchError(f"Línea {number}: case_id duplicado {case.case_id}.")
        seen.add(case.case_id)
        cases.append(case)
    if not cases:
        raise BenchError("El banco está vacío.")
    return tuple(cases)


def verify_corpus(cases: tuple[BenchCase, ...]) -> tuple[BenchCase, ...]:
    """Cases whose source sentence is no longer verbatim in the corpus.

    The bench is only worth what its sources are worth: a claim measured
    against an invented sentence measures nothing.  Whitespace is collapsed
    because the corpus keeps the line wrapping of the original PDF export.
    """

    missing: list[BenchCase] = []
    corpus: dict[str, str] = {}
    for case in cases:
        if case.source_ref not in corpus:
            document = REPO_ROOT / case.source_ref
            if not document.is_file():
                missing.append(case)
                continue
            corpus[case.source_ref] = " ".join(
                document.read_text(encoding="utf-8").split()
            )
        if " ".join(case.source_sentence.split()) not in corpus[case.source_ref]:
            missing.append(case)
    return tuple(missing)


def _service_validator(service: object) -> Verifier:
    """Measure a StructuredResponseService through its public door.

    Building a real ``GeneratedClaim`` whose only evidence span is the whole
    source sentence keeps the measurement on the same code path a chat turn
    takes, including the sentence expansion in ``_evidence_contexts``.
    """

    from app.modules.llm_chat.application.services.structured_response import (
        ClaimType,
        EvidenceSpan,
        GeneratedClaim,
    )

    def verify(claim_es: str, source_sentence: str) -> bool:
        claim = GeneratedClaim(
            claim_id="claim_bench",
            text=claim_es,
            claim_type=ClaimType.DOCUMENTED_GENERAL_KNOWLEDGE,
            source_ids=["bench_source"],
            evidence_spans=[
                EvidenceSpan(source_id="bench_source", text=source_sentence)
            ],
        )
        return service.citation_is_verifiable(  # type: ignore[attr-defined]
            claim,
            retained_sources={"bench_source": source_sentence},
        )

    return verify


def current_validator() -> Verifier:
    """Documentary support as it is decided with the feature switched off."""

    from app.modules.llm_chat.application.services.structured_response import (
        StructuredResponseService,
    )

    return _service_validator(StructuredResponseService())


def entailment_validator() -> Verifier:
    """The same validator with CHAT_CLAIM_ENTAILMENT_ENABLED turned on.

    Built from the settings themselves rather than from a hand-made verifier,
    so what the bench scores is the wiring production would get, threshold and
    timeout included.
    """

    from app.core.config import Settings
    from app.modules.llm_chat.application.services.structured_response import (
        StructuredResponseService,
    )
    from app.modules.llm_chat.composition import build_claim_entailment_verifier

    settings = Settings(  # type: ignore[call-arg]
        CHAT_CLAIM_ENTAILMENT_ENABLED=True,
    )
    verifier = build_claim_entailment_verifier(settings)
    assert verifier is not None
    # Loading the weights takes around eleven seconds and a chat turn is not
    # allowed to wait for it, so every claim asked meanwhile falls back to the
    # lexical rule. A bench that started measuring right away would score that
    # fallback and report it as this verifier's result.
    if not verifier.wait_until_ready(MODEL_LOAD_BUDGET_SECONDS):
        raise BenchError(
            "El modelo de entrañamiento no llegó a cargarse; sin él la medición "
            "sería la del validador léxico."
        )
    return _service_validator(
        StructuredResponseService(claim_entailment=verifier)
    )


def resolve_verifier(reference: str) -> Verifier:
    if reference == "current":
        return current_validator()
    if reference == "entailment":
        return entailment_validator()
    module_name, _, attribute = reference.partition(":")
    if not module_name or not attribute:
        raise BenchError(
            "El verificador debe indicarse como `modulo:funcion`, `current` o "
            "`entailment`."
        )
    module = importlib.import_module(module_name)
    verifier = getattr(module, attribute, None)
    if not callable(verifier):
        raise BenchError(f"{reference} no es invocable.")
    return verifier


def evaluate(cases: tuple[BenchCase, ...], verifier: Verifier) -> BenchResult:
    correct = 0
    false_accepts: list[BenchCase] = []
    false_rejects: list[BenchCase] = []
    for case in cases:
        accepted = bool(verifier(case.claim_es, case.source_sentence))
        if accepted == case.expected:
            correct += 1
        elif accepted:
            false_accepts.append(case)
        else:
            false_rejects.append(case)
    return BenchResult(
        total=len(cases),
        correct=correct,
        false_accepts=tuple(false_accepts),
        false_rejects=tuple(false_rejects),
    )


def _report(cases: tuple[BenchCase, ...], result: BenchResult, verbose: bool) -> None:
    print(f"casos            : {result.total}")
    print(
        f"aciertos         : {result.correct} "
        f"({result.correct / result.total:.1%})"
    )
    print(
        f"falsos positivos : {len(result.false_accepts)} "
        "(acepta una afirmación insegura)"
    )
    print(
        f"falsos negativos : {len(result.false_rejects)} "
        "(rechaza una afirmación fiel)"
    )
    totals = Counter(case.category for case in cases)
    errors = Counter(
        case.category for case in result.false_accepts + result.false_rejects
    )
    print("\npor categoría (aciertos/casos):")
    for category in sorted(totals):
        hits = totals[category] - errors[category]
        print(f"  {category:<12} {hits:>3}/{totals[category]:<3}")
    if not verbose:
        return
    for label, failures in (
        ("falsos positivos", result.false_accepts),
        ("falsos negativos", result.false_rejects),
    ):
        if not failures:
            continue
        print(f"\n{label}:")
        for case in failures:
            print(f"  {case.case_id} [{case.category}] {case.claim_es}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench", type=Path, default=DEFAULT_BENCH)
    parser.add_argument(
        "--verifier",
        default="current",
        help=(
            "`current`, `entailment` o `modulo:funcion` con firma "
            "(claim_es, source_sentence) -> bool"
        ),
    )
    parser.add_argument(
        "--verify-corpus",
        action="store_true",
        help="comprueba que cada oración fuente sigue estando literal en el corpus",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    try:
        cases = load_bench(args.bench)
        if args.verify_corpus:
            missing = verify_corpus(cases)
            if missing:
                for case in missing:
                    print(
                        f"ERROR: {case.case_id} no se encuentra literal en "
                        f"{case.source_ref}",
                        file=sys.stderr,
                    )
                return 2
            print(f"corpus           : {len(cases)} oraciones fuente verificadas\n")
        result = evaluate(cases, resolve_verifier(args.verifier))
    except BenchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    _report(cases, result, args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
