from __future__ import annotations

import random
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .records import ContextMode, Source, Turn, group_by_mode


# El mismo modelo, la misma revisión y el mismo pooling que usa el recuperador
# en producción (`RAG_EMBEDDING_MODEL` en backend/app/core/config.py). Medir con
# otro embebedor daría una cifra que no describe a este sistema.
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_CACHE_DIR = Path(".cache/fastembed")
_MISMATCHED_PAIRS_PER_TURN = 5
_WINDOW_WORDS = 90
_WINDOW_STEP = 60
_WINDOWS_PER_DOCUMENT = 8


@dataclass(frozen=True, slots=True)
class RelevanceScore:
    """Relevancia de la respuesta y su línea base de pares desajustados."""

    turns: int
    own_mean: float
    mismatched_mean: float
    win_rate: float


@dataclass(frozen=True, slots=True)
class GroundingCalibration:
    """Evidencia de si el anclaje semántico respuesta↔pasaje es medible aquí."""

    turns: int
    own_mean: float
    rival_mean: float
    win_rate: float


class EmbeddingUnavailableError(RuntimeError):
    """fastembed no está instalado o su modelo no está en la caché local."""


def measure_relevance(
    turns: Iterable[Turn],
    *,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    sample_size: int = 150,
    seed: int = 20260806,
) -> dict[ContextMode | str, RelevanceScore]:
    """Similitud pregunta↔respuesta por modo, con su línea base interpretable."""
    materialized = [turn for turn in turns if turn.explanatory and turn.question]
    embed = _load_embedder(model_name, cache_dir)
    rng = random.Random(seed)
    results: dict[ContextMode | str, RelevanceScore] = {}
    groups = [*group_by_mode(materialized).items(), ("total", materialized)]
    for group, subset in groups:
        sample = _sample(subset, sample_size, rng)
        if len(sample) < 2:
            continue
        questions = embed([turn.question for turn in sample])
        answers = embed([turn.answer for turn in sample])
        own = [_dot(questions[i], answers[i]) for i in range(len(sample))]
        mismatched: list[float] = []
        wins = 0
        for i in range(len(sample)):
            others = [j for j in range(len(sample)) if j != i]
            for j in rng.sample(others, min(_MISMATCHED_PAIRS_PER_TURN, len(others))):
                similarity = _dot(questions[i], answers[j])
                mismatched.append(similarity)
                wins += own[i] > similarity
        results[group] = RelevanceScore(
            turns=len(sample),
            own_mean=statistics.fmean(own),
            mismatched_mean=statistics.fmean(mismatched),
            win_rate=wins / len(mismatched),
        )
    return results


def calibrate_grounding(
    turns: Iterable[Turn],
    knowledge_dir: Path,
    *,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    sample_size: int = 60,
    seed: int = 20260806,
) -> GroundingCalibration:
    """Mide si la respuesta se parece más a su pasaje que a otro cualquiera.

    Es la prueba que decide si tiene sentido publicar una métrica de anclaje
    semántico: si la respuesta no se distingue de un pasaje ajeno del mismo
    corpus, la cifra no soportaría una afirmación de tesis.
    """
    rng = random.Random(seed)
    candidates = [
        turn
        for turn in turns
        if turn.sources and turn.explanatory and len(turn.answer.strip()) > 120
    ]
    sample = _sample(candidates, sample_size, rng)
    documents = [_read_windows(knowledge_dir, turn.sources[0]) for turn in sample]
    usable = [(turn, windows) for turn, windows in zip(sample, documents) if windows]
    if len(usable) < 2:
        raise EmbeddingUnavailableError(
            "No se pudo resolver el texto de los pasajes recuperados en "
            f"{knowledge_dir}. Revisa --knowledge-dir."
        )
    embed = _load_embedder(model_name, cache_dir)
    answers = embed([turn.answer for turn, _ in usable])
    flattened: list[str] = []
    owners: list[int] = []
    for index, (_, windows) in enumerate(usable):
        flattened.extend(windows)
        owners.extend([index] * len(windows))
    passages = embed(flattened)
    own_scores: list[float] = []
    rival_scores: list[float] = []
    wins = 0
    for index in range(len(usable)):
        own = _best_similarity(answers[index], passages, owners, index)
        own_scores.append(own)
        others = [other for other in range(len(usable)) if other != index]
        for rival_index in rng.sample(others, min(5, len(others))):
            rival = _best_similarity(answers[index], passages, owners, rival_index)
            rival_scores.append(rival)
            wins += own > rival
    return GroundingCalibration(
        turns=len(usable),
        own_mean=statistics.fmean(own_scores),
        rival_mean=statistics.fmean(rival_scores),
        win_rate=wins / len(rival_scores),
    )


def _load_embedder(model_name: str, cache_dir: Path):
    try:
        import numpy as np
        from fastembed import TextEmbedding
    except ImportError as exc:  # pragma: no cover - depende del entorno.
        raise EmbeddingUnavailableError(
            "Las métricas semánticas necesitan `fastembed` (ya es dependencia del "
            "backend). Instálalo o ejecuta el evaluador sin --semantic."
        ) from exc

    model = TextEmbedding(model_name, cache_dir=str(cache_dir))

    def embed(texts: Sequence[str]):
        vectors = np.asarray(list(model.embed(list(texts))), dtype="float32")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.clip(norms, 1e-9, None)

    return embed


def _read_windows(knowledge_dir: Path, source: Source) -> list[str]:
    """Reconstruye ventanas del documento aprobado que originó el pasaje.

    El JSONL guarda la procedencia del pasaje, no su texto, así que el chunk
    exacto que vio el modelo no es recuperable: se aproxima con ventanas del
    tamaño de troceo (`RAG_CHUNK_SIZE_WORDS`).
    """
    document = knowledge_dir / source.path if source.path else None
    if document is None or not document.is_file():
        matches = sorted(knowledge_dir.rglob(f"{source.identifier}*.md"))
        if not matches:
            return []
        document = matches[0]
    body = _strip_front_matter(document.read_text(encoding="utf-8"))
    words = body.split()
    windows = [
        " ".join(words[start : start + _WINDOW_WORDS])
        for start in range(0, max(1, len(words) - _WINDOW_WORDS + 1), _WINDOW_STEP)
    ]
    return windows[:_WINDOWS_PER_DOCUMENT] or ([body] if body else [])


def _strip_front_matter(text: str) -> str:
    if not text.startswith("---"):
        return text.strip()
    parts = text.split("---", 2)
    return parts[2].strip() if len(parts) > 2 else text.strip()


def _best_similarity(vector, passages, owners: list[int], owner: int) -> float:
    scores = [_dot(vector, passages[index]) for index, value in enumerate(owners) if value == owner]
    return max(scores) if scores else 0.0


def _dot(left, right) -> float:
    return float(left @ right)


def _sample(turns: list[Turn], sample_size: int, rng: random.Random) -> list[Turn]:
    if sample_size <= 0 or len(turns) <= sample_size:
        return list(turns)
    return rng.sample(turns, sample_size)
