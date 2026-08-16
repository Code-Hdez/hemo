"""Registro de llamadas al proveedor de generación — instrumentación de Fase 0.

Por qué existe
--------------
El objetivo del rediseño es que un turno haga **exactamente una** llamada al
modelo. Para poder afirmarlo hace falta contarlas donde de verdad ocurren: en el
adaptador, justo antes del ``POST``. Deducir la cuenta de ``generation_attempts``
o del resultado final no vale, porque hoy existen cuatro rutas de generación
(principal, reparación, reconducción y último recurso) y una quinta por
herramientas, y ninguna de ellas se refleja en un único contador.

Qué NO cuenta como llamada de generación
----------------------------------------
El calentamiento (``/api/generate`` con ``num_predict=1``), los sondeos de salud,
``/api/show``, ``/api/ps``, ``/api/tags``, la recuperación RAG y los embeddings.
Solo se registra el ``POST`` que pide prosa al modelo dentro de un turno de
usuario.

Este módulo **no cambia el comportamiento**: cuenta y describe. La aserción de
`provider_calls > 1` se registra; convertirla en excepción es trabajo de la
Fase 4, cuando el contrato ya esté simplificado y las regeneraciones eliminadas.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from app.modules.llm_chat.domain.entities import GENERATION_ROUTES

# El vocabulario de rutas vive en el dominio (``domain/entities.py``): describe
# el flujo del turno, no el transporte. Aquí solo se usa como lista blanca para
# que un typo no cree una ruta fantasma que luego parezca una vía de generación
# desconocida.
KNOWN_ROUTES = GENERATION_ROUTES


@dataclass(frozen=True, slots=True)
class ProviderCall:
    """Una petición de generación efectivamente enviada al proveedor."""

    index: int
    route: str
    num_ctx: int
    num_predict: int
    profile_name: str
    structured: bool
    started_monotonic: float


@dataclass(slots=True)
class ProviderCallLedger:
    """Cuenta las llamadas de generación de UN turno.

    Vive en un ``ContextVar``, así que cada turno tiene la suya aunque varios
    corran a la vez en el mismo proceso.
    """

    calls: list[ProviderCall] = field(default_factory=list)
    # Por que se rechazo la PRIMERA generacion. Sin esto, un turno que gasta
    # tres llamadas solo dice "gasto tres": no dice que comprobacion lo mando a
    # reparar, que es justo lo que hace falta para corregir el prompt sin ir a
    # ciegas.
    primera_validacion: str | None = None
    # El parametro que la pregunta nombraba y que el paciente NO tiene.
    #
    # Vive AQUI y no en `clinical_context_payload` por una razon medida: ese
    # payload alimenta `clinical_context_json`, que es el PRIMER bloque de
    # `rag_es.txt`. Meter ahi un campo que varia por turno cambiaria el prompt
    # —lo que el modelo lee— y ademas rompería el prefijo cacheable en el
    # bloque 1, que es justo el problema que el Bloque F esta midiendo.
    #
    # El ledger no toca el prompt: solo viaja al `route_trace` del contrato, que
    # es donde el arnes lo puede registrar. Telemetria, no entrada del modelo.
    parametro_pedido_ausente: str | None = None

    def record(
        self,
        *,
        route: str,
        num_ctx: int,
        num_predict: int,
        profile_name: str,
        structured: bool,
    ) -> int:
        """Registra una llamada y devuelve su índice 1-based.

        Se llama **antes** del ``POST``: una petición que sale y falla por red
        sigue siendo una llamada consumida, y contarla solo cuando responde
        ocultaría justo el caso que interesa vigilar.
        """
        call = ProviderCall(
            index=len(self.calls) + 1,
            route=route if route in KNOWN_ROUTES else f"unknown:{route}",
            num_ctx=num_ctx,
            num_predict=num_predict,
            profile_name=profile_name,
            structured=structured,
            started_monotonic=time.perf_counter(),
        )
        self.calls.append(call)
        return call.index

    @property
    def count(self) -> int:
        return len(self.calls)

    @property
    def exceeded_single_call(self) -> bool:
        """El invariante objetivo: nunca más de una llamada por turno."""
        return self.count > 1

    def summary(self) -> dict[str, object]:
        routes: dict[str, int] = {}
        for call in self.calls:
            routes[call.route] = routes.get(call.route, 0) + 1
        return {
            "provider_calls": self.count,
            "first_validation_reason": self.primera_validacion,
            "requested_parameter_absent": self.parametro_pedido_ausente,
            "provider_call_routes": routes,
            "provider_call_sequence": [call.route for call in self.calls],
            "single_call_invariant_held": not self.exceeded_single_call,
        }


_LEDGER: ContextVar[ProviderCallLedger | None] = ContextVar(
    "hemovet_provider_call_ledger",
    default=None,
)


@contextmanager
def turn_ledger() -> Iterator[ProviderCallLedger]:
    """Abre el registro de un turno y lo cierra restaurando el anterior."""
    ledger = ProviderCallLedger()
    token = _LEDGER.set(ledger)
    try:
        yield ledger
    finally:
        _LEDGER.reset(token)


def current_ledger() -> ProviderCallLedger | None:
    """El registro del turno en curso, o ``None`` fuera de un turno.

    Devuelve ``None`` en lugar de crear uno: las llamadas de calentamiento y de
    salud ocurren fuera de un turno y no deben inventarse un contador propio.
    """
    return _LEDGER.get()


def record_provider_call(
    *,
    route: str,
    num_ctx: int,
    num_predict: int,
    profile_name: str,
    structured: bool,
) -> int | None:
    """Anota una llamada en el registro activo, si lo hay.

    Devuelve el índice 1-based de la llamada dentro del turno, o ``None`` si la
    llamada ocurre fuera de un turno de usuario.
    """
    ledger = current_ledger()
    if ledger is None:
        return None
    return ledger.record(
        route=route,
        num_ctx=num_ctx,
        num_predict=num_predict,
        profile_name=profile_name,
        structured=structured,
    )
