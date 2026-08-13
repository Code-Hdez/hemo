#!/usr/bin/env python3
"""Prototipo: verificación de soporte documental en cascada.

El patrón es el que recomienda la literatura de guardrails en producción:
una heurística barata decide la mayoría de los casos y un verificador caro
se consulta sólo cuando la barata no basta.  Aquí:

    1. el validador léxico actual, tal cual está en producción;
    2. si acepta, se acepta — no hay segundo escalón para lo que ya pasa;
    3. si rechaza, el veto de números y polaridad decide si el caso puede
       siquiera discutirse: una cifra que la fuente no dice o una polaridad
       invertida no las arregla ningún modelo, y son la señal real
       anti-invención;
    4. sólo lo que sobrevive al veto llega al modelo de NLI, que dictamina
       si la fuente implica la afirmación.

Colocar el veto *antes* del modelo, y no después, es lo que hace barata la
cascada: sobre el banco bilingüe reduce las consultas al modelo de 43 casos
(los que el léxico rechaza) a 18.

Medido con ``scripts/evaluate_support_bench.py --verifier
scripts.cascade_support_verifier:<entrada>`` sobre las 70 filas del banco,
con mDeBERTa-v3-base-xnli y umbral 0,5:

    verify              cascada mandatada          52/70   FA 12   FR  6
    verify_entailment   sólo el modelo             68/70   FA  2   FR  0
    verify_numeric_only veto de cifras + modelo    69/70   FA  1   FR  0  (0,7)

Las tres entradas existen para que ese contraste se pueda reproducir, no
porque haga falta elegir en tiempo de ejecución: el informe explica por qué
la cascada sale perdiendo frente a la última.
"""
from __future__ import annotations

import os
import re
import sys
from functools import lru_cache
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.llm_chat.application.services.structured_response import (  # noqa: E402
    ClaimType,
    EvidenceSpan,
    GeneratedClaim,
    StructuredResponseService,
)

# Mismo léxico de negación que usa `_proposition_supported`. Se repite aquí
# a propósito: el prototipo mide el veto *tal como está hoy*, sin corregirlo,
# para que el número de la cascada no se confunda con el de un veto mejorado.
_NEGATION = re.compile(r"\b(?:no|nunca|sin|not|never|without)\b")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")

# `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` entrena premisa
# e hipótesis en idiomas distintos, que es exactamente el caso de HemoVet:
# corpus en inglés, afirmación en español.
_MODEL = os.environ.get(
    "CASCADE_NLI_MODEL",
    "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7",
)
_THRESHOLD = float(os.environ.get("CASCADE_NLI_THRESHOLD", "0.5"))


def _claim(claim_es: str, source_sentence: str) -> GeneratedClaim:
    return GeneratedClaim(
        claim_id="claim_bench",
        text=claim_es,
        claim_type=ClaimType.DOCUMENTED_GENERAL_KNOWLEDGE,
        source_ids=["bench_source"],
        evidence_spans=[
            EvidenceSpan(source_id="bench_source", text=source_sentence)
        ],
    )


def lexical_stage(claim_es: str, source_sentence: str) -> bool:
    """Escalón 1: el validador de producción, sin tocar."""

    return StructuredResponseService().citation_is_verifiable(
        _claim(claim_es, source_sentence),
        retained_sources={"bench_source": source_sentence},
    )


def numeric_polarity_veto(claim_es: str, source_sentence: str) -> bool:
    """Las dos comprobaciones que ningún segundo escalón puede levantar.

    Es el mismo bucle de `_proposition_supported` con la cobertura léxica
    quitada: cada proposición necesita un contexto que contenga sus cifras y
    que coincida en polaridad.
    """

    contexts = StructuredResponseService._evidence_contexts(
        _claim(claim_es, source_sentence),
        retained_sources={"bench_source": source_sentence},
    )
    propositions = StructuredResponseService._propositions(claim_es)
    if not contexts or not propositions:
        return False
    for proposition in propositions:
        numbers = set(_NUMBER.findall(proposition))
        negative = bool(
            _NEGATION.search(StructuredResponseService._normalize(proposition))
        )
        if not any(
            numbers.issubset(set(_NUMBER.findall(context)))
            and negative
            == bool(
                _NEGATION.search(StructuredResponseService._normalize(context))
            )
            for context in contexts
        ):
            return False
    return True


@lru_cache(maxsize=1)
def _nli():
    import torch
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
    )

    tokenizer = AutoTokenizer.from_pretrained(_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(_MODEL)
    model.eval()
    torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
    entailment = next(
        index
        for index, label in model.config.id2label.items()
        if label.lower().startswith("entail")
    )
    return tokenizer, model, entailment


def entailment_probability(premise: str, hypothesis: str) -> float:
    import torch

    tokenizer, model, entailment = _nli()
    batch = tokenizer(
        premise, hypothesis, truncation=True, max_length=256, return_tensors="pt"
    )
    with torch.inference_mode():
        logits = model(**batch).logits[0]
    return float(torch.softmax(logits, dim=-1)[entailment])


def nli_stage(claim_es: str, source_sentence: str) -> bool:
    """Escalón 2: la fuente debe implicar la afirmación completa."""

    return entailment_probability(source_sentence, claim_es) >= _THRESHOLD


def numeric_veto(claim_es: str, source_sentence: str) -> bool:
    """El veto sin su mitad de polaridad.

    La comprobación de cifras es la única de las dos que resiste la medición:
    no rechaza ni una sola afirmación fiel del banco. La de polaridad sí — se
    lleva por delante 6 turnos correctos, porque su léxico de negación es una
    lista cerrada de seis palabras que no contiene `absent`, `cannot` ni
    `anucleate`, y porque compara una *proposición* contra una *oración*
    entera, de modo que "A aumenta el riesgo, pero no en todos" queda con una
    proposición afirmativa frente a una fuente que sí niega.
    """

    contexts = StructuredResponseService._evidence_contexts(
        _claim(claim_es, source_sentence),
        retained_sources={"bench_source": source_sentence},
    )
    propositions = StructuredResponseService._propositions(claim_es)
    if not contexts or not propositions:
        return False
    return all(
        any(
            set(_NUMBER.findall(proposition)).issubset(set(_NUMBER.findall(context)))
            for context in contexts
        )
        for proposition in propositions
    )


def verify(claim_es: str, source_sentence: str) -> bool:
    """La cascada tal como se pidió medirla."""

    if lexical_stage(claim_es, source_sentence):
        return True
    if not numeric_polarity_veto(claim_es, source_sentence):
        return False
    return nli_stage(claim_es, source_sentence)


def verify_entailment(claim_es: str, source_sentence: str) -> bool:
    """El segundo escalón solo, sin cascada: el término de comparación."""

    return nli_stage(claim_es, source_sentence)


def verify_numeric_only(claim_es: str, source_sentence: str) -> bool:
    """Lo que mejor midió: cifras como veto duro y el modelo para el resto."""

    return numeric_veto(claim_es, source_sentence) and nli_stage(
        claim_es, source_sentence
    )
