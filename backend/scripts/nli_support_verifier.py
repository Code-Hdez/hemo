#!/usr/bin/env python3
"""Prototipo: soporte documental verificado por entrañamiento (NLI).

La hipótesis que este prototipo comprueba nace de una medición previa: la
similitud por embeddings multilingües es casi ciega a la negación — "los
eritrocitos NO transportan oxígeno" obtuvo coseno 0.802 contra la fuente
afirmativa.  Un clasificador NLI, en cambio, tiene una clase para eso: el
mismo par recibe aquí contradicción 0.960 y entrañamiento 0.018.

La pregunta que responde el modelo es exactamente la que hace falta: *¿la
oración del corpus implica la afirmación en español?*  Se acepta sólo cuando
la implica; la neutralidad — el caso del cambio de tema, "los linfocitos
tienen núcleos reniformes" contra una fuente sobre monocitos — se rechaza
igual que la contradicción.

Corre sobre ONNX Runtime y `tokenizers`, no sobre torch: los dos ya entran en
la imagen del backend como dependencias de `fastembed`, el cliente de
embeddings del RAG.  Adoptarlo no añadiría una pila de inferencia nueva, sólo
el peso del modelo (1.1 GB en fp32, 339 MB cuantizado a int8).

Se mide con ``scripts/evaluate_support_bench.py --verifier
scripts.nli_support_verifier:verify``.  Ejecutado directamente, este módulo
reporta la latencia por caso sobre el mismo banco.
"""
from __future__ import annotations

import json
import os
import sys
import time
from functools import lru_cache
from pathlib import Path

import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCH = BACKEND_ROOT / "tests" / "data" / "bilingual_support_bench.jsonl"

# mDeBERTa-v3-base-XNLI entrena pares cuya premisa e hipótesis pueden estar en
# idiomas distintos, que es literalmente el caso de HemoVet: corpus en inglés,
# afirmación en español.  Se probó también `multilingual-MiniLMv2-L6-mnli-xnli`
# (5x más rápido) y no sirve: su mejor umbral deja 55/70 con 11 aceptaciones
# inseguras, las mismas que el validador léxico que ya está en producción.
MODEL_REPO = os.environ.get(
    "NLI_SUPPORT_MODEL",
    "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7",
)

# El export cuantizado pesa un tercio; `NLI_SUPPORT_QUANTIZED=1` lo selecciona.
# Se midió y no compensa: int8 borra el margen entre clases — el positivo más
# débil cae a 0.216 y el negativo más fuerte sube a 0.879, así que se solapan
# y no queda umbral limpio.  Su mejor corte deja 67/70 con 2 aceptaciones
# inseguras, contra 69/70 con 1 en fp32.
MODEL_FILE = (
    "onnx/model_quantized.onnx"
    if os.environ.get("NLI_SUPPORT_QUANTIZED") == "1"
    else "onnx/model.onnx"
)

# Umbral calibrado sobre el banco bilingüe.  La separación medida es amplia:
# el positivo más débil entraña a 0.916 y todos los negativos salvo uno se
# quedan en 0.685 o menos, así que cualquier corte entre 0.69 y 0.91 da el
# mismo resultado.  0.80 se elige por estar en el centro de esa meseta, no en
# su borde, para que el número no dependa de la cifra decimal de un caso.
THRESHOLD = float(os.environ.get("NLI_SUPPORT_THRESHOLD", "0.80"))

# Las oraciones del corpus y las afirmaciones del chat son de una frase; 256
# piezas cubren el par entero sin truncar ninguno de los 70 casos del banco.
MAX_LENGTH = 256


@lru_cache(maxsize=1)
def _session():
    """Tokenizador, sesión ONNX e índice de la clase `entailment`.

    El índice se busca por nombre en `id2label` en vez de fijarlo a 0: los
    checkpoints XNLI no comparten el mismo orden de etiquetas y equivocarlo
    convierte el verificador en su contrario sin fallar nunca.
    """

    import onnxruntime as ort
    from huggingface_hub import hf_hub_download
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(hf_hub_download(MODEL_REPO, "tokenizer.json"))
    tokenizer.enable_truncation(max_length=MAX_LENGTH)
    options = ort.SessionOptions()
    options.intra_op_num_threads = max(1, (os.cpu_count() or 2) // 2)
    session = ort.InferenceSession(
        hf_hub_download(MODEL_REPO, MODEL_FILE),
        options,
        providers=["CPUExecutionProvider"],
    )
    config = json.loads(
        Path(hf_hub_download(MODEL_REPO, "config.json")).read_text(encoding="utf-8")
    )
    entailment = next(
        int(index)
        for index, label in config["id2label"].items()
        if label.lower().startswith("entail")
    )
    return tokenizer, session, entailment


def entailment_probability(premise: str, hypothesis: str) -> float:
    """Probabilidad de que `premise` implique `hypothesis`."""

    tokenizer, session, entailment = _session()
    encoded = tokenizer.encode(premise, hypothesis)
    logits = session.run(
        None,
        {
            "input_ids": np.array([encoded.ids], dtype=np.int64),
            "attention_mask": np.array([encoded.attention_mask], dtype=np.int64),
        },
    )[0][0]
    exponentials = np.exp(logits - logits.max())
    return float(exponentials[entailment] / exponentials.sum())


def verify(claim_es: str, source_sentence: str) -> bool:
    """La fuente debe implicar la afirmación; no basta con no contradecirla.

    Se mide una sola dirección a propósito.  La comprobación bidireccional
    (exigir además que la afirmación implique la fuente) se midió y empeora:
    hunde 7 positivos legítimos — la fuente casi siempre dice más que la
    afirmación que se apoya en ella — y ni siquiera atrapa el falso positivo
    que queda, porque el modelo también lo entraña al revés a 0.744.
    """

    return entailment_probability(source_sentence, claim_es) >= THRESHOLD


def _measure(bench: Path) -> None:
    """Latencia por caso sobre el banco, ya con el modelo cargado.

    La primera inferencia paga la inicialización del grafo de ONNX Runtime y
    no representa el coste de un turno de chat, así que se descarta.
    """

    cases = [
        json.loads(line)
        for line in bench.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    verify(cases[0]["claim_es"], cases[0]["source_sentence"])
    started = time.perf_counter()
    for case in cases:
        verify(case["claim_es"], case["source_sentence"])
    elapsed = (time.perf_counter() - started) / len(cases) * 1000
    print(f"modelo           : {MODEL_REPO} ({MODEL_FILE})")
    print(f"umbral           : {THRESHOLD}")
    print(f"latencia         : {elapsed:.1f} ms/caso ({len(cases)} casos, CPU)")


if __name__ == "__main__":
    _measure(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BENCH)
