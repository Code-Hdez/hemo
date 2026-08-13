from __future__ import annotations

import json
import logging
import math
from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any

logger = logging.getLogger("uvicorn.error.hemovet.llm_chat")

# The corpus sentence and the claim are one sentence each; 256 pieces cover
# the whole pair without truncating any of the 70 bench cases.
MAX_LENGTH = 256
# fp32, not the int8 export. Quantizing pays a third of the disk but erases
# the margin between classes on the bench — the weakest faithful claim falls
# to 0.216 while the strongest unsafe one climbs to 0.879, so the two overlap
# and no clean threshold survives.
MODEL_FILE = "onnx/model.onnx"


class OnnxClaimEntailmentVerifier:
    """Cross-lingual entailment over ONNX Runtime, deadline-bounded.

    Everything here exists so a failure of this model can only ever *lose* the
    entailment opinion, never grant support: the loading and the inference run
    in a worker thread the caller waits on with a timeout, every exception is
    swallowed into a ``None`` verdict, and the caller reads ``None`` as "use
    the lexical rule".
    """

    def __init__(
        self,
        *,
        model_repo: str,
        threshold: float,
        timeout_seconds: float,
        cache_dir: Path | str | None = None,
        intra_op_threads: int = 2,
        max_consecutive_timeouts: int = 3,
        session_factory: Callable[[], tuple[Any, Any, int]] | None = None,
    ) -> None:
        self._model_repo = model_repo
        self._threshold = threshold
        self._timeout_seconds = timeout_seconds
        self._cache_dir = str(cache_dir) if cache_dir is not None else None
        self._intra_op_threads = intra_op_threads
        self._max_consecutive_timeouts = max_consecutive_timeouts
        self._session_factory = session_factory or self._load_session
        # A single worker: the ONNX session parallelizes inside one inference
        # already, and serializing keeps a slow call from being multiplied by
        # every claim of the turn arriving at once.
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="claim-entailment",
        )
        self._session: tuple[Any, Any, int] | None = None
        self._loading = False
        self._unavailable = False
        self._consecutive_timeouts = 0
        # A turn validates the same claim twice — once when unprovable
        # citations are downgraded, once when support is validated — and a
        # repair attempt re-validates the claims it kept. The cache is what
        # keeps that from costing a second inference each time.
        self._verdicts: OrderedDict[tuple[str, str], bool] = OrderedDict()
        self._cache_size = 256

    def warmup(self) -> None:
        """Start loading the model without blocking the caller.

        Composition calls this at startup so the first chat turn does not have
        to spend its deadline downloading and initializing 1.1 GB of weights.
        """

        self._loading = True
        self._executor.submit(self._ensure_session)

    def wait_until_ready(self, timeout_seconds: float) -> bool:
        """Block until the weights are in memory. Never call this from a turn.

        It exists for scripts and probes that must measure the verifier rather
        than the fallback: without it, everything asked during the eleven
        seconds the load takes comes back undecided, and a bench would quietly
        score the lexical rule while believing it scored this one.
        """

        try:
            self._executor.submit(self._ensure_session).result(
                timeout=timeout_seconds
            )
        except Exception:
            return False
        return True

    def entails(self, *, premise: str, hypothesis: str) -> bool | None:
        if self._unavailable:
            return None
        # Loading measured 11 s, far beyond one claim's deadline. Queueing
        # claims behind it would be worse than useless: they would all miss
        # their deadline anyway, and the worker would then grind through
        # inferences nobody is waiting for while the next real claim queues
        # behind *those* — enough consecutive misses to disable a verifier
        # that was working. Whoever arrives while the weights load gets no
        # verdict and no work is created for them.
        if self._session is None and self._loading:
            return None
        key = (premise, hypothesis)
        cached = self._verdicts.get(key)
        if cached is not None:
            self._verdicts.move_to_end(key)
            return cached
        # Reaching here with no session means no warmup ran and this caller is
        # the one paying for the load; from now on the rest are turned away
        # until the weights are in memory.
        self._loading = self._session is None
        future = self._executor.submit(
            self._entailment_probability,
            premise,
            hypothesis,
        )
        try:
            probability = future.result(timeout=self._timeout_seconds)
        except FutureTimeoutError:
            future.cancel()
            # A deadline missed while the weights are still loading says
            # nothing about the model: the first turns after a restart are
            # expected to arrive before the session exists and simply fall
            # back to the lexical rule.
            if self._session is not None:
                self._consecutive_timeouts += 1
                # Cada caída al léxico queda medida (§8.1 de la jornada: sin
                # esto no se podía saber si las citas en ~0 eran veredictos
                # negativos o timeouts silenciosos).
                logger.info(
                    "llm_chat.claim_entailment_timeout timeout_seconds=%s "
                    "consecutive=%s",
                    self._timeout_seconds,
                    self._consecutive_timeouts,
                )
                # A response envelope may carry up to 48 claims; paying the
                # deadline on each of them would add minutes to a turn that
                # is already budgeted at CHAT_TOTAL_TIMEOUT_SECONDS, so a
                # verifier that keeps missing it steps aside for good.
                if self._consecutive_timeouts >= self._max_consecutive_timeouts:
                    self._unavailable = True
                    logger.warning(
                        "llm_chat.claim_entailment_disabled reason=timeout "
                        "timeout_seconds=%s",
                        self._timeout_seconds,
                    )
            return None
        except Exception as exc:
            # Anything raised here is structural — missing weights, no network
            # on first use, an export whose inputs do not match — and would
            # raise again on the next claim.
            self._unavailable = True
            logger.warning(
                "llm_chat.claim_entailment_disabled reason=error code=%s",
                type(exc).__name__,
            )
            return None
        self._consecutive_timeouts = 0
        verdict = probability >= self._threshold
        # El veredicto con su score, para distinguir «opina y rechaza» de
        # «nunca llegó a opinar» en los logs de producción (§8.1).
        logger.info(
            "llm_chat.claim_entailment_verdict probability=%.3f threshold=%.2f "
            "verdict=%s",
            probability,
            self._threshold,
            "entails" if verdict else "rejects",
        )
        self._verdicts[key] = verdict
        if len(self._verdicts) > self._cache_size:
            self._verdicts.popitem(last=False)
        return verdict

    def score(self, *, premise: str, hypothesis: str) -> float | None:
        """The entailment probability, for callers that compare hypotheses.

        ``entails`` answers "does this pass the threshold", which is the right
        question when a claim must be supported by one specific sentence. It is
        the wrong question when several mutually exclusive hypotheses are
        offered and the winner is wanted: measured on the held-out half of the
        scope bench, first-past-the-threshold classified 23 of 23 off-domain
        questions as in-domain, because the in-scope hypotheses were tried
        first and one of them always cleared 0.80. Comparing probabilities asks
        which reading the model actually prefers.

        Shares the same deadline, cache and fail-closed behaviour: ``None``
        means no answer, never a low score.
        """

        if self._unavailable:
            return None
        if self._session is None and self._loading:
            return None
        self._loading = self._session is None
        future = self._executor.submit(
            self._entailment_probability,
            premise,
            hypothesis,
        )
        try:
            return future.result(timeout=self._timeout_seconds)
        except FutureTimeoutError:
            future.cancel()
            if self._session is not None:
                self._consecutive_timeouts += 1
                if self._consecutive_timeouts >= self._max_consecutive_timeouts:
                    self._unavailable = True
                    logger.warning(
                        "llm_chat.claim_entailment_disabled reason=timeout "
                        "timeout_seconds=%s",
                        self._timeout_seconds,
                    )
            return None
        except Exception as exc:
            self._unavailable = True
            logger.warning(
                "llm_chat.claim_entailment_disabled reason=error code=%s",
                type(exc).__name__,
            )
            return None

    def _entailment_probability(self, premise: str, hypothesis: str) -> float:
        import numpy as np

        tokenizer, session, entailment = self._ensure_session()
        encoded = tokenizer.encode(premise, hypothesis)
        logits = session.run(
            None,
            {
                "input_ids": np.array([encoded.ids], dtype=np.int64),
                "attention_mask": np.array([encoded.attention_mask], dtype=np.int64),
            },
        )[0][0]
        largest = max(float(value) for value in logits)
        exponentials = [math.exp(float(value) - largest) for value in logits]
        return exponentials[entailment] / sum(exponentials)

    def _ensure_session(self) -> tuple[Any, Any, int]:
        if self._session is None:
            try:
                self._session = self._session_factory()
            except Exception as exc:
                # Recorded here as well as in `entails` because a warmup has
                # nobody waiting on its result: without this, a model that
                # cannot be fetched would leave the verifier silently
                # answering nothing for the life of the process.
                self._unavailable = True
                logger.warning(
                    "llm_chat.claim_entailment_disabled reason=load code=%s",
                    type(exc).__name__,
                )
                raise
        return self._session

    def _load_session(self) -> tuple[Any, Any, int]:
        """Tokenizer, ONNX session, and the index of the `entailment` class.

        The class index is looked up by name instead of being pinned to 0:
        XNLI checkpoints do not agree on label order, and getting it wrong
        turns the verifier into its own opposite without ever failing.
        """

        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        def download(filename: str) -> str:
            return hf_hub_download(
                self._model_repo,
                filename,
                cache_dir=self._cache_dir,
            )

        tokenizer = Tokenizer.from_file(download("tokenizer.json"))
        tokenizer.enable_truncation(max_length=MAX_LENGTH)
        options = ort.SessionOptions()
        options.intra_op_num_threads = self._intra_op_threads
        session = ort.InferenceSession(
            download(MODEL_FILE),
            options,
            # Explicitly CPU-only: the L4 in hemovet-prod belongs to the
            # conversational model, and a support check must never queue
            # behind — or in front of — a generation on it.
            providers=["CPUExecutionProvider"],
        )
        config = json.loads(
            Path(download("config.json")).read_text(encoding="utf-8")
        )
        entailment = next(
            int(index)
            for index, label in config["id2label"].items()
            if label.lower().startswith("entail")
        )
        logger.info(
            "llm_chat.claim_entailment_ready model=%s threshold=%s",
            self._model_repo,
            self._threshold,
        )
        return tokenizer, session, entailment
