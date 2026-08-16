"""Fase 0 — el contador de llamadas al proveedor.

El invariante del rediseño es «una llamada al modelo por turno». Antes de poder
eliminarlas hay que poder contarlas, y contarlas donde de verdad ocurren: en el
adaptador, justo antes del POST. Estos tests demuestran que el contador ve lo
que pasa y no lo deduce.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.modules.llm_chat.domain.entities import (
    GENERATION_ROUTE_LAST_RESORT,
    GENERATION_ROUTE_MAIN,
    GENERATION_ROUTE_REPAIR,
    GENERATION_ROUTE_STEER,
    GENERATION_ROUTES,
    ModelRequest,
)
from app.modules.llm_chat.domain.generation_config import EffectiveGenerationProfile
from app.modules.llm_chat.domain.provider_call_ledger import (
    current_ledger,
    record_provider_call,
    turn_ledger,
)
from app.modules.llm_chat.infrastructure.llm.openai_compatible_client import (
    OllamaNativeLLMClient,
)


def _profile(
    *, num_ctx: int = 4096, num_predict: int = 220
) -> EffectiveGenerationProfile:
    return EffectiveGenerationProfile(
        name="test_profile",
        kind="main",
        provider="ollama",
        model="qwen3:4b",
        num_ctx=num_ctx,
        max_input_tokens=1,
        context_reserve_tokens=1,
        num_predict=num_predict,
        temperature=0.1,
        top_p=0.9,
        top_k=40,
        repeat_penalty=1.0,
        thinking=False,
        timeout_seconds=30,
        keep_alive="30m",
    )


def _request(profile: EffectiveGenerationProfile, **overrides: object) -> ModelRequest:
    fields: dict[str, object] = {
        "system_prompt": "sistema",
        "user_prompt": "pregunta",
        "thinking": profile.thinking,
        "model": profile.model,
        "profile_name": profile.name,
        "profile_kind": profile.kind,
        "num_predict": profile.num_predict,
        "num_ctx": profile.num_ctx,
        "max_input_tokens": profile.max_input_tokens,
        "context_reserve_tokens": profile.context_reserve_tokens,
        "temperature": profile.temperature,
        "top_p": profile.top_p,
        "top_k": profile.top_k,
        "repeat_penalty": profile.repeat_penalty,
        "timeout_seconds": profile.timeout_seconds,
        "keep_alive": profile.keep_alive,
    }
    fields.update(overrides)
    return ModelRequest(**fields)


def _ollama_body(*, done_reason: str = "stop") -> dict[str, object]:
    return {
        "message": {"content": "respuesta"},
        "done": True,
        "done_reason": done_reason,
        "total_duration": 5_000_000_000,
        "load_duration": 1_000_000_000,
        "prompt_eval_duration": 500_000_000,
        "prompt_eval_count": 120,
        "eval_duration": 3_000_000_000,
        "eval_count": 60,
    }


def _client(handler) -> OllamaNativeLLMClient:
    return OllamaNativeLLMClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        base_url="http://ollama:11434/",
        model_name="qwen3:4b",
        timeout_seconds=30,
        warmup_profile=_profile(),
    )


# ── El contador ve la llamada ───────────────────────────────────────────────


def test_una_generacion_cuenta_exactamente_una_llamada() -> None:
    profile = _profile()
    client = _client(lambda _r: httpx.Response(200, json=_ollama_body()))

    async def run() -> int:
        with turn_ledger() as ledger:
            await client.generate(_request(profile))
            return ledger.count

    assert asyncio.run(run()) == 1


def test_el_default_de_la_peticion_es_la_ruta_principal() -> None:
    assert _request(_profile()).generation_route == GENERATION_ROUTE_MAIN


def test_cada_ruta_se_cuenta_por_separado() -> None:
    profile = _profile()
    client = _client(lambda _r: httpx.Response(200, json=_ollama_body()))
    rutas = (
        GENERATION_ROUTE_MAIN,
        GENERATION_ROUTE_REPAIR,
        GENERATION_ROUTE_STEER,
        GENERATION_ROUTE_LAST_RESORT,
    )

    async def run() -> dict[str, object]:
        with turn_ledger() as ledger:
            for ruta in rutas:
                await client.generate(_request(profile, generation_route=ruta))
            return ledger.summary()

    resumen = asyncio.run(run())
    assert resumen["provider_calls"] == 4
    assert resumen["provider_call_sequence"] == list(rutas)
    assert resumen["provider_call_routes"] == {ruta: 1 for ruta in rutas}
    # Cuatro llamadas es exactamente lo que el rediseño va a eliminar.
    assert resumen["single_call_invariant_held"] is False


def test_la_llamada_se_cuenta_aunque_el_proveedor_falle() -> None:
    """Una petición que sale y muere consumió su llamada igual.

    Contar solo las que responden ocultaría justo el caso que hay que vigilar.
    """
    profile = _profile()
    client = _client(lambda _r: httpx.Response(503, json={"error": "sin sitio"}))

    async def run() -> int:
        with turn_ledger() as ledger:
            with pytest.raises(Exception):
                await client.generate(_request(profile))
            return ledger.count

    assert asyncio.run(run()) == 1


# ── El contador NO ve lo que no debe ────────────────────────────────────────


def test_fuera_de_un_turno_no_hay_registro() -> None:
    """El calentamiento y los sondeos de salud no son llamadas de un turno."""
    assert current_ledger() is None
    assert (
        record_provider_call(
            route=GENERATION_ROUTE_MAIN,
            num_ctx=4096,
            num_predict=220,
            profile_name="p",
            structured=False,
        )
        is None
    )


def test_el_calentamiento_no_cuenta_como_llamada_de_turno() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/generate"
        return httpx.Response(200, json={"response": "OK", "done": True})

    client = _client(handler)

    async def run() -> int:
        with turn_ledger() as ledger:
            await client.warmup(timeout_seconds=5)
            return ledger.count

    assert asyncio.run(run()) == 0


def test_el_registro_de_un_turno_no_se_filtra_al_siguiente() -> None:
    profile = _profile()
    client = _client(lambda _r: httpx.Response(200, json=_ollama_body()))

    async def run() -> tuple[int, int]:
        with turn_ledger() as primero:
            await client.generate(_request(profile))
            uno = primero.count
        with turn_ledger() as segundo:
            await client.generate(_request(profile))
            dos = segundo.count
        return uno, dos

    assert asyncio.run(run()) == (1, 1)


# ── Lo que el registro anota de cada llamada ────────────────────────────────


def test_el_registro_anota_contexto_y_presupuesto_de_cada_llamada() -> None:
    profile = _profile(num_ctx=16384, num_predict=1280)
    client = _client(lambda _r: httpx.Response(200, json=_ollama_body()))

    async def run():
        with turn_ledger() as ledger:
            await client.generate(_request(profile, response_schema={"type": "object"}))
            return ledger.calls[0]

    call = asyncio.run(run())
    assert call.index == 1
    assert call.num_ctx == 16384
    assert call.num_predict == 1280
    assert call.structured is True
    assert call.profile_name == "test_profile"


def test_una_ruta_desconocida_se_marca_en_vez_de_confundirse_con_main() -> None:
    async def run() -> str:
        with turn_ledger() as ledger:
            ledger.record(
                route="inventada",
                num_ctx=1,
                num_predict=1,
                profile_name="p",
                structured=False,
            )
            return ledger.calls[0].route

    assert asyncio.run(run()) == "unknown:inventada"


def test_el_vocabulario_de_rutas_cubre_las_cinco_vias_actuales() -> None:
    assert GENERATION_ROUTES == {
        "main",
        "repair",
        "steer",
        "last_resort",
        "tool",
    }


# ── Métricas nuevas del adaptador ───────────────────────────────────────────


def test_las_metricas_traen_done_reason_y_el_residuo() -> None:
    """El residuo = total − (carga + prefill + decode).

    Sin él, un turno lento parece inexplicable aunque las tres fases sumen poco.
    """
    profile = _profile()
    client = _client(
        lambda _r: httpx.Response(200, json=_ollama_body(done_reason="length"))
    )

    async def run():
        with turn_ledger():
            return await client.generate(_request(profile))

    response = asyncio.run(run())
    metrics = response.provider_metrics
    assert metrics["done_reason"] == "length"
    # 5000 − (1000 + 500 + 3000) = 500 ms fuera de las tres fases desglosadas.
    assert metrics["residual_duration_ms"] == pytest.approx(500.0)


def test_el_log_segrega_por_ruta_y_por_indice_de_llamada(caplog) -> None:
    profile = _profile()
    client = _client(lambda _r: httpx.Response(200, json=_ollama_body()))

    async def run() -> None:
        with turn_ledger():
            await client.generate(
                _request(profile, generation_route=GENERATION_ROUTE_REPAIR)
            )

    with caplog.at_level("INFO", logger="uvicorn.error.hemovet.llm_chat"):
        asyncio.run(run())

    linea = next(m for m in caplog.messages if m.startswith("llm_chat.ollama_metrics "))
    registro = json.loads(linea.split(" ", 1)[1])
    assert registro["generation_route"] == GENERATION_ROUTE_REPAIR
    assert registro["provider_call_index"] == 1
    assert registro["num_ctx_requested"] == profile.num_ctx
    assert registro["num_predict_requested"] == profile.num_predict
    assert registro["done_reason"] == "stop"
    assert registro["residual_duration_ms"] == pytest.approx(500.0)


# ── El contrato público ─────────────────────────────────────────────────────


def test_el_contador_viaja_al_contrato_publico() -> None:
    """La Puerta 0 se puntúa desde el cliente, no leyendo logs por SSH."""
    from app.modules.llm_chat.api.schemas import PUBLIC_ROUTE_TRACE_KEYS

    assert "provider_calls" in PUBLIC_ROUTE_TRACE_KEYS
    assert "provider_call_routes" in PUBLIC_ROUTE_TRACE_KEYS


def test_la_traza_del_turno_resume_cuenta_y_rutas() -> None:
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        SendChatMessageUseCase,
    )

    trace = SendChatMessageUseCase._provider_call_trace

    async def run() -> dict[str, object]:
        with turn_ledger() as ledger:
            ledger.record(
                route=GENERATION_ROUTE_MAIN,
                num_ctx=1,
                num_predict=1,
                profile_name="p",
                structured=False,
            )
            ledger.record(
                route=GENERATION_ROUTE_REPAIR,
                num_ctx=1,
                num_predict=1,
                profile_name="p",
                structured=False,
            )
            return trace()

    assert asyncio.run(run()) == {
        "provider_calls": 2,
        "provider_call_routes": [GENERATION_ROUTE_MAIN, GENERATION_ROUTE_REPAIR],
        # None fuera del caso de uso: solo este anota por que se rechazo la
        # primera generacion.
        "first_validation_reason": None,
        # Anadido con el Bloque G.2 y por eso se ADAPTA este test en vez de
        # borrarlo: la regla de decision de G.2 revierte el cambio si el
        # selector deja fuera un parametro que la pregunta nombraba en mas del
        # 2 % de los turnos, y ese caso no dejaba ningun rastro.
        #
        # Va en el ledger —y no en `clinical_context_payload`— porque ese
        # payload alimenta `clinical_context_json`, el PRIMER bloque del prompt:
        # meterlo ahi cambiaria lo que el modelo lee y romperia el prefijo
        # cacheable en el bloque 1.
        #
        # None fuera del caso de uso, por la misma razon que el motivo de
        # validacion: aqui no hay seleccion clinica que resumir.
        "requested_parameter_absent": None,
    }


def test_fuera_de_un_turno_la_traza_va_vacia_en_vez_de_inventar_un_cero() -> None:
    """No es lo mismo «no se llamó al proveedor» que «no hay registro»."""
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        SendChatMessageUseCase,
    )

    assert SendChatMessageUseCase._provider_call_trace() == {}


def test_done_reason_solo_admite_el_vocabulario_conocido() -> None:
    """El campo viaja al público: no se reenvía lo que diga el proveedor."""
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _PUBLIC_DONE_REASONS,
    )

    assert "length" in _PUBLIC_DONE_REASONS
    assert "stop" in _PUBLIC_DONE_REASONS
    assert "<script>" not in _PUBLIC_DONE_REASONS


# ── El error terminal conserva el motivo ────────────────────────────────────


def test_el_error_terminal_conserva_que_comprobacion_lo_rechazo() -> None:
    """Los turnos que mueren de forma terminal son los más difíciles del corpus.

    El `code` público colapsa todo rechazo del validador en
    `invalid_model_output`, y eso dejaba sin nombre justo a los turnos que hay
    que arreglar: en `puerta3j`, 6 de los 10 fallos de contrato llegaron sin
    motivo. El motivo se recupera del código crudo, que ya lo llevaba.
    """
    from app.modules.llm_chat.api.router import (
        _runtime_code,
        _terminal_validation_reason,
    )
    from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable

    exc = ChatRuntimeUnavailable("invalid_output_indirect_treatment_recommendation")
    # El contrato público no cambia.
    assert _runtime_code(exc) == "invalid_model_output"
    # Pero el motivo deja de perderse.
    assert _terminal_validation_reason(exc) == "indirect_treatment_recommendation"


def test_el_motivo_terminal_se_sanea_contra_un_patron_cerrado() -> None:
    """El que publica no confía en el que produce, aunque sea el servidor."""
    from app.modules.llm_chat.api.router import _terminal_validation_reason
    from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable

    assert (
        _terminal_validation_reason(ChatRuntimeUnavailable("invalid_output_")) is None
    )
    assert (
        _terminal_validation_reason(
            ChatRuntimeUnavailable("invalid_output_<script>alert(1)</script>")
        )
        is None
    )
    # Y un error que no es de validación no inventa un motivo.
    assert (
        _terminal_validation_reason(ChatRuntimeUnavailable("chat_total_timeout"))
        is None
    )


def test_el_sobre_de_error_expone_el_motivo_terminal() -> None:
    from app.modules.llm_chat.api.schemas import ChatErrorEnvelope

    assert "first_validation_reason" in ChatErrorEnvelope.model_fields
    # Opcional: los errores que no son de validación no lo llevan.
    assert ChatErrorEnvelope.model_fields["first_validation_reason"].default is None


# ── La atribución de fuentes deja de contar dos causas como una ─────────────


def test_el_marcador_ausente_se_distingue_del_marcador_declarado() -> None:
    """`missing_evidence_attribution` escondía dos problemas con dos arreglos.

    Fue 6 de los 48 fallos de contrato de la campaña del 14-ago y su detalle era
    una constante, así que no se podía saber si el modelo se había olvidado del
    marcador —recuperable por el servidor, que sí sabe qué retuvo— o si lo había
    declarado mal —y respetarlo es una decisión deliberada—.
    """
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _evidence_attribution_detail,
    )

    assert (
        _evidence_attribution_detail(
            evidence_marker_found=False, declared_source_ids=()
        )
        == "marker_absent"
    )
    assert (
        _evidence_attribution_detail(evidence_marker_found=True, declared_source_ids=())
        == "marker_declared_but_empty"
    )
    assert (
        _evidence_attribution_detail(
            evidence_marker_found=True, declared_source_ids=("S9",)
        )
        == "marker_declared_unresolvable"
    )


def test_el_detalle_de_atribucion_viaja_a_la_telemetria() -> None:
    """Antes se perdía: la clase no estaba en la lista de proyección y salía `-`."""
    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidation,
    )
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _validation_detail_code,
    )

    for detalle in (
        "marker_absent",
        "marker_declared_but_empty",
        "marker_declared_unresolvable",
    ):
        proyectado = _validation_detail_code(
            OutputValidation(
                is_safe=False,
                text="",
                reason="missing_evidence_attribution",
                detail=detalle,
            )
        )
        assert proyectado == detalle


def test_el_detalle_de_atribucion_es_vocabulario_CERRADO() -> None:
    """Telemetría, no texto libre: el proveedor no puede inyectar por aquí."""
    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidation,
    )
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _validation_detail_code,
    )

    assert (
        _validation_detail_code(
            OutputValidation(
                is_safe=False,
                text="",
                reason="missing_evidence_attribution",
                detail="<script>alert(1)</script>",
            )
        )
        is None
    )


# ── indirect_treatment_recommendation deja de ser una clase ciega ───────────


def test_los_terminos_que_disparan_la_conjuncion_se_registran() -> None:
    """12 de los 48 fallos del 14-ago y era imposible saber cuál de los dos era.

    La comprobación exige un sustantivo (hierro, suplementos, corticoides…) Y un
    modal (puede, conviene, necesita…), buscados sobre el texto entero sin exigir
    cercanía. Sobre las 198 respuestas publicadas el modal aparece en el 82,8 % y
    el sustantivo en el 3,0 %: la conjunción equivale, de hecho, a preguntar por
    el sustantivo. Eso deja indistinguibles la etiología y la recomendación.
    """
    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidator,
    )

    v = OutputValidator()

    etiologia = "La deficiencia de hierro puede causar anemia en el perro."
    receta = "Conviene darle un suplemento de hierro todos los dias."

    # Las dos disparan la misma clase: eso es lo que hay hoy y no se cambia.
    assert (
        v._contains_indirect_treatment(etiologia) == "indirect_treatment_recommendation"
    )
    assert v._contains_indirect_treatment(receta) == "indirect_treatment_recommendation"

    # Pero ahora se puede saber POR QUE. `hierro` es una de las dos palabras
    # ambiguas, asi que ademas se etiqueta la acepcion: aqui no hay colocacion
    # terapeutica ninguna, es una etiologia, y el campo lo dice.
    assert v._indirect_treatment_terms(etiologia) == "hierro+puede+desnudo"
    # `suplemento` NO es ambigua, asi que su formato queda byte a byte igual que
    # en la campana v3 y la taxonomia sigue siendo comparable entre campanas.
    assert v._indirect_treatment_terms(receta) == "suplemento+conviene"

    # Y un texto que no dispara no inventa términos.
    assert (
        v._indirect_treatment_terms("El hematocrito mide el volumen celular.") is None
    )


def test_los_terminos_no_cambian_ninguna_decision_del_validador() -> None:
    """I-4: no se toca el validador. Esto informa, no decide."""
    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidator,
    )

    v = OutputValidator()
    texto = "Conviene darle un suplemento de hierro."
    antes = v._contains_indirect_treatment(texto)
    v._indirect_treatment_terms(texto)
    assert v._contains_indirect_treatment(texto) == antes


def test_la_acepcion_distingue_el_compartimento_de_la_transfusion() -> None:
    """`plasma` produjo 8 de los 24 rechazos de esta clase en la campana v3.

    En un asistente de hemogramas `plasma` es un compartimento sanguineo antes
    que una transfusion: aparece en 11 de los 356 textos publicados y en los 11
    significa «la parte liquida de la sangre». Sin esta etiqueta no se puede
    saber cual de las dos acepciones produjo el rechazo, porque el backend no
    persiste el texto que rechaza.

    Esto NO cambia el veredicto: las dos frases siguen siendo rechazadas.
    """
    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidator,
    )

    v = OutputValidator()

    compartimento = (
        "El hematocrito indica que proporcion es celula frente al plasma, "
        "que puede variar."
    )
    # Ojo con el caso «transfusion de plasma»: ahi el sustantivo que casa
    # primero es `transfusion`, que ya esta en el lexico por su cuenta, y la
    # etiqueta no llega a aplicarse. Es justo el argumento de que restringir
    # `plasma` no pierde cobertura — el acto terapeutico tiene termino propio.
    assert v._indirect_treatment_terms(
        "Se indica una transfusion de plasma si la albumina puede seguir baja."
    ) == "transfusion+se indica"

    transfusion = "Debes darle plasma fresco congelado para corregir la coagulopatia."

    # Las dos siguen disparando la MISMA clase. El validador no se toca.
    for texto in (compartimento, transfusion):
        assert (
            v._contains_indirect_treatment(texto)
            == "indirect_treatment_recommendation"
        )

    # Pero ya no son indistinguibles en la telemetria.
    assert v._indirect_treatment_terms(compartimento).endswith("+desnudo")
    assert v._indirect_treatment_terms(transfusion).endswith("+terap")


def test_la_acepcion_no_emite_nunca_el_texto_que_rodea_la_palabra() -> None:
    """La invariante de privacidad del docstring: vocabulario cerrado, siempre."""
    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidator,
    )

    v = OutputValidator()
    # Un dato que jamas debe salir en un log operativo.
    texto = "A Kira, la golden de 4 anios, puede darsele hierro dextrano."
    detalle = v._indirect_treatment_terms(texto)

    assert detalle is not None
    assert "Kira" not in detalle
    assert "golden" not in detalle
    # Solo palabras de los dos vocabularios cerrados y la etiqueta de acepcion.
    partes = detalle.split("+")
    assert partes[-1] in {"terap", "desnudo"}
    assert len(partes) <= 3


def test_los_terminos_viajan_por_telemetry_detail_y_NO_por_detail() -> None:
    """`detail` alimenta el prompt de reparación, y el GOAL prohíbe tocarlo."""
    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidation,
    )
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _validation_detail_code,
    )

    v = OutputValidation(
        is_safe=False,
        text="",
        reason="indirect_treatment_recommendation",
        telemetry_detail="hierro+puede",
    )
    # El canal de reparación no ve nada nuevo.
    assert v.detail is None
    # La telemetría sí.
    assert _validation_detail_code(v) == "hierro+puede"


def test_el_detalle_de_tratamiento_es_vocabulario_ACOTADO() -> None:
    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidation,
    )
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _validation_detail_code,
    )

    for basura in ("<script>", "hierro|puede", "a" * 200, ""):
        assert (
            _validation_detail_code(
                OutputValidation(
                    is_safe=False,
                    text="",
                    reason="indirect_treatment_recommendation",
                    telemetry_detail=basura,
                )
            )
            is None
        )


# ── El fallo TERMINAL conserva tambien su detalle ───────────────────────────


def test_el_codigo_terminal_lleva_el_parametro_implicado() -> None:
    """Los terminales son los mas dificiles y eran los peor instrumentados.

    En la campana del 14-ago los 27 terminales llevaban solo la clase y los 198
    con cuerpo llevaban el detalle entero. De los 6 unsupported_numeric_claim, 5
    eran terminales y llegaron SIN parametro; el unico con `hct` es el que se
    reparo.
    """
    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidation,
    )
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _terminal_error_code,
    )

    assert (
        _terminal_error_code(
            OutputValidation(
                is_safe=False,
                text="",
                reason="unsupported_numeric_claim",
                detail="cualquier cosa",
                parameter_code="hct",
            )
        )
        == "invalid_output_unsupported_numeric_claim:hct"
    )


def test_el_codigo_terminal_sanea_al_alfabeto_del_contrato() -> None:
    """Componer un codigo que no pase el filtro del router perderia la CLASE."""
    import re

    from app.modules.llm_chat.api.router import _VALIDATION_REASON_PATTERN
    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidation,
    )
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _terminal_error_code,
    )

    # `hierro+puede` lleva un `+`, que NO esta en [a-z0-9_:].
    codigo = _terminal_error_code(
        OutputValidation(
            is_safe=False,
            text="",
            reason="indirect_treatment_recommendation",
            telemetry_detail="hierro+puede",
        )
    )
    assert codigo == "invalid_output_indirect_treatment_recommendation:hierro_puede"
    # Y el router lo acepta, que es lo que hay que garantizar.
    assert _VALIDATION_REASON_PATTERN.fullmatch(codigo.removeprefix("invalid_output_"))
    assert re.fullmatch(r"[a-z0-9_:]+", codigo.removeprefix("invalid_output_"))


def test_el_contrato_publico_no_cambia_al_anadir_el_detalle() -> None:
    """`_runtime_code` sigue colapsando en invalid_model_output."""
    from app.modules.llm_chat.api.router import (
        _runtime_code,
        _terminal_validation_reason,
    )
    from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable

    exc = ChatRuntimeUnavailable("invalid_output_unsupported_numeric_claim:hct")
    assert _runtime_code(exc) == "invalid_model_output"
    assert _terminal_validation_reason(exc) == "unsupported_numeric_claim:hct"


def test_un_terminal_sin_detalle_se_comporta_como_antes() -> None:
    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidation,
    )
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _terminal_error_code,
    )

    assert (
        _terminal_error_code(
            OutputValidation(is_safe=False, text="", reason="content_free_answer")
        )
        == "invalid_output_content_free_answer"
    )
    assert (
        _terminal_error_code(OutputValidation(is_safe=False, text="", reason=""))
        == "invalid_output_unknown"
    )


def test_la_clase_de_seguridad_internal_material_dice_QUE_se_expuso() -> None:
    """Aparecio 1 vez en 400 turnos, terminal, y llego SIN causa.

    Su `detail` ya llevaba el fragmento que caso, pero `_validation_detail_code`
    no proyectaba la clase. Saber si el modelo escribio «system_prompt» o
    simplemente «analysis_id» son dos incidentes de gravedad muy distinta.
    """
    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidation,
    )
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _validation_detail_code,
    )

    for crudo, esperado in (
        ("analysis_id", "analysis_id"),
        ("system prompt", "system_prompt"),
        ("/app/modules/", "/app/modules/"),
    ):
        assert (
            _validation_detail_code(
                OutputValidation(
                    is_safe=False,
                    text="",
                    reason="internal_material_exposed",
                    detail=crudo,
                )
            )
            == esperado
        )

    # Y sigue siendo vocabulario acotado: nada de texto libre del proveedor.
    assert (
        _validation_detail_code(
            OutputValidation(
                is_safe=False,
                text="",
                reason="internal_material_exposed",
                detail='{"role": "system", "content": "…"}',
            )
        )
        is None
    )
