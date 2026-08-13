from __future__ import annotations

import threading
import time

import pytest

from app.core.config import Settings
from app.modules.llm_chat import composition
from app.modules.llm_chat.application.services.structured_response import (
    ClaimType,
    EvidenceSpan,
    GeneratedClaim,
    GeneratedResponseEnvelope,
    StructuredResponseError,
    StructuredResponseService,
)
from app.modules.llm_chat.composition import build_claim_entailment_verifier
from app.modules.llm_chat.infrastructure.entailment import (
    OnnxClaimEntailmentVerifier,
)

# Every pair below is a case of the bilingual bench
# (backend/tests/data/bilingual_support_bench.jsonl), so what these tests
# exercise is what was measured there: S01 for the vetoes, S21 for a faithful
# paraphrase the lexical rule rejects, S13 for an unsafe one it accepts.
SOURCE = (
    "Hb concentration provides the most direct indication of oxygen transport "
    "capacity of the blood and should be approximately one-third the Hct if "
    "erythrocytes are of normal size."
)
# A faithful translation with barely a token in common with its source: no
# figures and no negation, so only the lexical overlap stands between it and
# acceptance, and the lexicon refuses it.
FAITHFUL = (
    "Los monocitos tienen núcleos reniformes u ovalados y un citoplasma azul "
    "grisáceo pálido en los frotis de sangre periférica."
)
FAITHFUL_SOURCE = (
    "Monocytes have reniform to oval - shaped nuclei with pale, blue - gray "
    "cytoplasm on peripheral blood smears."
)
NEGATED = (
    "La concentración de hemoglobina no indica la capacidad de transporte de "
    "oxígeno de la sangre."
)
INVENTED_FIGURE = (
    "La concentración de hemoglobina debería ser aproximadamente 2 veces el "
    "hematocrito."
)
# Same shape, different subject: the source talks about erythrocytes, the claim
# about platelets. The lexical rule accepts it — it is the kind of unsafe
# acceptance the entailment verifier exists to refuse.
OFF_TOPIC = "El RDW describe la variabilidad del tamaño de las plaquetas."
OFF_TOPIC_SOURCE = "The RDW describes the variability in erythrocyte size."


class _Verdict:
    """A verifier that answers whatever the test needs, and counts the asks."""

    def __init__(self, answer: bool | None) -> None:
        self.answer = answer
        self.calls: list[tuple[str, str]] = []

    def entails(self, *, premise: str, hypothesis: str) -> bool | None:
        self.calls.append((premise, hypothesis))
        return self.answer


class _Raising:
    def entails(self, *, premise: str, hypothesis: str) -> bool | None:
        raise RuntimeError("modelo roto")


def _claim(text: str, source: str) -> GeneratedClaim:
    return GeneratedClaim(
        claim_id="claim_doc",
        text=text,
        claim_type=ClaimType.DOCUMENTED_GENERAL_KNOWLEDGE,
        source_ids=["source_1"],
        evidence_spans=[EvidenceSpan(source_id="source_1", text=source)],
    )


def _verifiable(service: StructuredResponseService, text: str, source: str) -> bool:
    return service.citation_is_verifiable(
        _claim(text, source),
        retained_sources={"source_1": source},
    )


def test_without_verifier_support_is_decided_exactly_as_before() -> None:
    service = StructuredResponseService()

    assert _verifiable(service, FAITHFUL, FAITHFUL_SOURCE) is False
    assert _verifiable(service, OFF_TOPIC, OFF_TOPIC_SOURCE) is True


def test_verifier_replaces_the_lexical_decision_in_both_directions() -> None:
    accepting = _Verdict(True)
    refusing = _Verdict(False)

    # What the lexicon rejected, the entailment verifier can accept...
    assert _verifiable(
        StructuredResponseService(claim_entailment=accepting),
        FAITHFUL,
        FAITHFUL_SOURCE,
    )
    # ...and what it accepted, the verifier can refuse. This direction is the
    # whole point: a check that only ran after a lexical acceptance would
    # inherit all 11 unsafe acceptances the lexicon makes on the bench.
    assert not _verifiable(
        StructuredResponseService(claim_entailment=refusing),
        OFF_TOPIC,
        OFF_TOPIC_SOURCE,
    )


def test_verifier_reads_the_source_sentence_untouched() -> None:
    verifier = _Verdict(True)

    _verifiable(
        StructuredResponseService(claim_entailment=verifier),
        FAITHFUL,
        FAITHFUL_SOURCE,
    )

    # Accents and capitalization survive: feeding the model the normalized text
    # the lexical rule works on costs two bench cases and collapses the margin
    # the threshold sits in (weakest faithful claim 0.916 -> 0.275).
    assert verifier.calls == [(FAITHFUL_SOURCE, FAITHFUL)]


def test_a_quoted_fragment_is_widened_to_its_sentence_in_the_corpus() -> None:
    verifier = _Verdict(True)
    service = StructuredResponseService(claim_entailment=verifier)
    # The corpus keeps the line wrapping of the original PDF export while a
    # model quoting from it writes one line, so whitespace is collapsed on
    # both sides before the fragment is located.
    retained = (
        "Platelets are small.\nMonocytes have reniform to oval - shaped\n"
        "nuclei with pale, blue - gray cytoplasm on peripheral blood smears."
    )
    claim = GeneratedClaim(
        claim_id="claim_doc",
        text=FAITHFUL,
        claim_type=ClaimType.DOCUMENTED_GENERAL_KNOWLEDGE,
        source_ids=["source_1"],
        evidence_spans=[EvidenceSpan(source_id="source_1", text="reniform to oval")],
    )

    service.citation_is_verifiable(claim, retained_sources={"source_1": retained})

    # The premise is the whole sentence, not the four quoted words, and the
    # neighbouring sentence about platelets is not part of it.
    assert verifier.calls == [(FAITHFUL_SOURCE, FAITHFUL)]


@pytest.mark.parametrize("verdict", [True, None])
def test_invented_figures_are_refused_whatever_the_verifier_says(
    verdict: bool | None,
) -> None:
    service = StructuredResponseService(claim_entailment=_Verdict(verdict))

    assert not _verifiable(service, INVENTED_FIGURE, SOURCE)


@pytest.mark.parametrize("verdict", [True, None])
def test_negated_claims_are_refused_whatever_the_verifier_says(
    verdict: bool | None,
) -> None:
    service = StructuredResponseService(claim_entailment=_Verdict(verdict))

    assert not _verifiable(service, NEGATED, SOURCE)


def test_a_verifier_without_a_verdict_falls_back_to_the_lexical_rule() -> None:
    silent = StructuredResponseService(claim_entailment=_Verdict(None))

    assert _verifiable(silent, FAITHFUL, FAITHFUL_SOURCE) is False
    assert _verifiable(silent, OFF_TOPIC, OFF_TOPIC_SOURCE) is True


def test_a_verifier_that_raises_falls_back_to_the_lexical_rule() -> None:
    broken = StructuredResponseService(claim_entailment=_Raising())

    assert _verifiable(broken, FAITHFUL, FAITHFUL_SOURCE) is False
    assert _verifiable(broken, OFF_TOPIC, OFF_TOPIC_SOURCE) is True


def _support_failure(
    service: StructuredResponseService,
    text: str,
    source: str,
) -> StructuredResponseError:
    envelope = GeneratedResponseEnvelope.model_validate(
        {
            "schema_version": "hemovet-response-v2",
            "response_type": "documented_general_explanation",
            "intent": "GENERAL_EDUCATION",
            "claims": [_claim(text, source).model_dump()],
            "safety": {
                "contains_diagnosis_confirmation": False,
                "contains_medication_recommendation": False,
                "contains_dose": False,
                "contains_frequency": False,
                "contains_treatment_duration": False,
                "contains_personalized_treatment": False,
                "requires_urgent_referral": False,
            },
        }
    )
    with pytest.raises(StructuredResponseError) as captured:
        service.validate_support(
            envelope,
            expected_intent="GENERAL_EDUCATION",
            allowed_fact_ids=(),
            retained_sources={"source_1": source},
            allowed_policy_rule_ids=(),
        )
    return captured.value


def test_an_entailment_refusal_names_itself_in_the_failure_detail() -> None:
    refused = _support_failure(
        StructuredResponseService(claim_entailment=_Verdict(False)),
        OFF_TOPIC,
        OFF_TOPIC_SOURCE,
    )

    assert refused.code == "evidence_claim_mismatch"
    # Reporting the lexical overlap arithmetic here would describe a rule that
    # did not decide this claim.
    assert refused.detail_code == "claim_entailment_rejected"
    assert "plaquetas" not in str(refused.detail_code)


def test_without_a_verdict_the_failure_detail_stays_the_lexical_arithmetic() -> None:
    for service in (
        StructuredResponseService(),
        StructuredResponseService(claim_entailment=_Verdict(None)),
    ):
        failure = _support_failure(service, FAITHFUL, FAITHFUL_SOURCE)

        assert failure.detail_code is not None
        assert failure.detail_code.startswith("proposition_")
        assert ":overlap_" in failure.detail_code


def _verifier(factory, **overrides: object) -> OnnxClaimEntailmentVerifier:
    options: dict[str, object] = {
        "model_repo": "test/model",
        "threshold": 0.80,
        "timeout_seconds": 0.5,
        "session_factory": factory,
    }
    options.update(overrides)
    return OnnxClaimEntailmentVerifier(**options)  # type: ignore[arg-type]


class _Session:
    """Stands in for tokenizer + ONNX session, returning fixed logits."""

    def __init__(self, logits: list[float]) -> None:
        self.logits = logits
        self.inferences = 0

    def encode(self, premise: str, hypothesis: str) -> "_Session":
        return self

    @property
    def ids(self) -> list[int]:
        return [1, 2, 3]

    @property
    def attention_mask(self) -> list[int]:
        return [1, 1, 1]

    def run(self, outputs: object, feeds: dict[str, object]) -> list[list[list[float]]]:
        self.inferences += 1
        return [[self.logits]]


def _loaded(logits: list[float]) -> tuple[_Session, object]:
    session = _Session(logits)
    return session, (lambda: (session, session, 0))


def test_probability_above_the_threshold_is_an_entailment() -> None:
    session, factory = _loaded([4.0, 0.0, 0.0])

    assert _verifier(factory).entails(premise=SOURCE, hypothesis=FAITHFUL) is True
    assert session.inferences == 1


def test_probability_below_the_threshold_is_a_refusal() -> None:
    _, factory = _loaded([1.0, 0.9, 0.9])

    assert _verifier(factory).entails(premise=SOURCE, hypothesis=FAITHFUL) is False


def test_the_entailment_class_is_read_from_the_checkpoint_labels() -> None:
    # XNLI checkpoints do not agree on label order; pinning the index would
    # turn the verifier into its own opposite without ever failing.
    session = _Session([4.0, 0.0, 0.0])
    contradiction_first = _verifier(lambda: (session, session, 2))

    assert contradiction_first.entails(premise=SOURCE, hypothesis=FAITHFUL) is False


def test_a_repeated_pair_is_answered_from_the_cache() -> None:
    session, factory = _loaded([4.0, 0.0, 0.0])
    verifier = _verifier(factory)

    verifier.entails(premise=SOURCE, hypothesis=FAITHFUL)
    verifier.entails(premise=SOURCE, hypothesis=FAITHFUL)

    # A turn validates the same claim twice — once when unprovable citations
    # are downgraded, once when support is validated.
    assert session.inferences == 1


def test_a_model_that_cannot_load_yields_no_verdict_and_steps_aside() -> None:
    attempts: list[int] = []

    def factory() -> tuple[object, object, int]:
        attempts.append(1)
        raise OSError("no hay pesos")

    verifier = _verifier(factory)

    assert verifier.entails(premise=SOURCE, hypothesis=FAITHFUL) is None
    assert verifier.entails(premise=SOURCE, hypothesis=FAITHFUL) is None
    assert len(attempts) == 1


def test_an_inference_over_its_deadline_yields_no_verdict() -> None:
    release = threading.Event()

    class _Slow(_Session):
        def run(
            self,
            outputs: object,
            feeds: dict[str, object],
        ) -> list[list[list[float]]]:
            release.wait(5)
            return super().run(outputs, feeds)

    slow = _Slow([4.0, 0.0, 0.0])
    verifier = _verifier(lambda: (slow, slow, 0), timeout_seconds=0.05)
    try:
        assert verifier.entails(premise=SOURCE, hypothesis=FAITHFUL) is None
    finally:
        release.set()


def test_repeated_deadline_misses_disable_the_verifier() -> None:
    release = threading.Event()

    class _Slow(_Session):
        def run(
            self,
            outputs: object,
            feeds: dict[str, object],
        ) -> list[list[list[float]]]:
            release.wait(5)
            return super().run(outputs, feeds)

    slow = _Slow([4.0, 0.0, 0.0])
    verifier = _verifier(
        lambda: (slow, slow, 0),
        timeout_seconds=0.05,
        max_consecutive_timeouts=2,
    )
    try:
        # A response envelope may carry up to 48 claims: a verifier that keeps
        # missing its deadline would add minutes to a turn that already has a
        # total budget.
        for index in range(3):
            assert (
                verifier.entails(premise=SOURCE, hypothesis=f"{FAITHFUL} {index}")
                is None
            )
        assert verifier._unavailable is True
    finally:
        release.set()


def test_claims_arriving_while_the_weights_load_create_no_backlog() -> None:
    release = threading.Event()
    session = _Session([4.0, 0.0, 0.0])

    def factory() -> tuple[object, object, int]:
        release.wait(5)
        return session, session, 0

    verifier = _verifier(factory, timeout_seconds=5)
    verifier.warmup()

    started = time.perf_counter()
    # Loading measured 11 s. Queueing claims behind it would make them all
    # miss their deadline and leave the worker computing verdicts nobody
    # waits for, which is what disables a verifier that was working.
    assert verifier.entails(premise=SOURCE, hypothesis=FAITHFUL) is None
    assert time.perf_counter() - started < 1

    release.set()
    for _ in range(50):
        if verifier.entails(premise=SOURCE, hypothesis=FAITHFUL) is True:
            break
        time.sleep(0.05)
    else:
        pytest.fail("el verificador nunca quedó listo")
    assert session.inferences == 1


def test_waiting_for_readiness_reports_whether_the_model_loaded() -> None:
    session, factory = _loaded([4.0, 0.0, 0.0])

    def broken() -> tuple[object, object, int]:
        raise OSError("no hay pesos")

    ready = _verifier(factory)
    assert ready.wait_until_ready(5) is True
    assert ready.entails(premise=SOURCE, hypothesis=FAITHFUL) is True

    # A measurement that cannot tell a loaded model from an absent one would
    # score the lexical fallback and report it as this verifier's result.
    assert _verifier(broken).wait_until_ready(5) is False


def test_warmup_loads_the_model_off_the_calling_thread() -> None:
    loaded = threading.Event()
    session = _Session([4.0, 0.0, 0.0])

    def factory() -> tuple[object, object, int]:
        loaded.set()
        return session, session, 0

    _verifier(factory).warmup()

    assert loaded.wait(5)


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "APP_ENV": "test",
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "SECRET_KEY": "test-secret",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_composition_wires_no_verifier_by_default() -> None:
    assert build_claim_entailment_verifier(_settings()) is None


def test_composition_passes_the_configured_runtime_and_warms_it_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built: dict[str, object] = {}

    class _Recorder:
        def __init__(self, **options: object) -> None:
            built.update(options)
            self.warmed = False

        def warmup(self) -> None:
            self.warmed = True

    monkeypatch.setattr(composition, "OnnxClaimEntailmentVerifier", _Recorder)

    verifier = build_claim_entailment_verifier(
        _settings(
            CHAT_CLAIM_ENTAILMENT_ENABLED=True,
            CHAT_CLAIM_ENTAILMENT_THRESHOLD=0.9,
            CHAT_CLAIM_ENTAILMENT_TIMEOUT_SECONDS=1.5,
            CHAT_CLAIM_ENTAILMENT_THREADS=3,
        )
    )

    assert built["threshold"] == 0.9
    assert built["timeout_seconds"] == 1.5
    assert built["intra_op_threads"] == 3
    # The weights are not downloaded by the caller: startup only asks for them.
    assert verifier.warmed is True  # type: ignore[union-attr]


def test_enabling_the_verifier_without_a_model_is_refused_at_startup() -> None:
    with pytest.raises(ValueError, match="CHAT_CLAIM_ENTAILMENT_MODEL"):
        _settings(
            CHAT_CLAIM_ENTAILMENT_ENABLED=True,
            CHAT_CLAIM_ENTAILMENT_MODEL="   ",
        )


def test_the_cache_directory_is_resolved_against_the_project_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    built: dict[str, object] = {}

    class _Recorder:
        def __init__(self, **options: object) -> None:
            built.update(options)

        def warmup(self) -> None:
            return None

    monkeypatch.setattr(composition, "OnnxClaimEntailmentVerifier", _Recorder)

    build_claim_entailment_verifier(
        _settings(
            CHAT_CLAIM_ENTAILMENT_ENABLED=True,
            CHAT_CLAIM_ENTAILMENT_CACHE_DIR=".cache/entailment",
            HEMOVET_PROJECT_ROOT=tmp_path,
        )
    )

    # 1.1 GB has to land where the deployment mounts a volume, never on a
    # relative path that depends on the process working directory.
    assert built["cache_dir"] == tmp_path / ".cache" / "entailment"


def test_a_slow_verifier_does_not_stall_the_turn_forever() -> None:
    release = threading.Event()

    class _Slow(_Session):
        def run(
            self,
            outputs: object,
            feeds: dict[str, object],
        ) -> list[list[list[float]]]:
            release.wait(5)
            return super().run(outputs, feeds)

    slow = _Slow([4.0, 0.0, 0.0])
    service = StructuredResponseService(
        claim_entailment=_verifier(lambda: (slow, slow, 0), timeout_seconds=0.05),
    )
    started = time.perf_counter()
    try:
        # The lexical rule decides instead, and it decides quickly.
        assert _verifiable(service, OFF_TOPIC, OFF_TOPIC_SOURCE) is True
    finally:
        release.set()
    assert time.perf_counter() - started < 2
