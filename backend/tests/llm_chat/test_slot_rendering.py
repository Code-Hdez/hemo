"""M.2 — que escriba el servidor: los slots y la prosa ensamblada.

El test que importa es `test_la_prosa_del_servidor_pasa_el_validador_real`: los
demas comprueban piezas, ese comprueba el proposito. Si algun dia falla, el
mecanismo entero ha dejado de funcionar y no hay que ajustarlo, hay que medirlo
otra vez.
"""

from __future__ import annotations

import pytest

from app.modules.llm_chat.application.services.output_claim_validator import (
    OutputClaimValidator,
)
from app.modules.llm_chat.application.services.slot_rendering import (
    AfirmacionSlot,
    construir_esquema_de_turno,
    etiqueta_desambiguada,
    renderizar_afirmaciones,
)

# El caso real del fixture: absoluto NORMAL y porcentaje ALTO. Estados distintos,
# que es exactamente la condicion que dispara `ambiguous_parameter_claim`.
HECHOS = [
    {
        "code": "NEU",
        "parameter": "Neutrofilos",
        "value": "8.4",
        "unit": "x10^3/uL",
        "status": "normal",
        "study_date": "2026-01-10",
    },
    {
        "code": "NEU_PCT",
        "parameter": "Neutrofilos %",
        "value": "85.0",
        "unit": "%",
        "status": "high",
        "study_date": "2026-01-10",
    },
]


def test_la_prosa_del_servidor_pasa_el_validador_real() -> None:
    """El proposito entero de M.2, contra el validador de produccion.

    `[MEDIDO]` La redaccion que el plan proponia —«el recuento absoluto de
    neutrofilos es de 8.4 x10^3/uL, dentro del rango»— NO pasa: `generic_family`
    marca cualquier alias del absoluto. Lo que pasa es separar la etiqueta del
    valor en clausulas distintas.
    """
    v = OutputClaimValidator()

    texto = renderizar_afirmaciones(
        [
            AfirmacionSlot(parametro="NEU", estado="dentro_del_rango", valor="8.4"),
            AfirmacionSlot(parametro="NEU_PCT", estado="alto", valor="85.0"),
        ],
        HECHOS,
    )
    assert v.validate(texto, case_facts=HECHOS).is_valid

    # Y el contraste: pegarlas en una sola clausula vuelve a disparar.
    pegado = "El recuento absoluto de neutrofilos es de 8.4 x10^3/uL, dentro del rango."
    assert not v.validate(pegado, case_facts=HECHOS).is_valid


def test_lo_que_escribe_hoy_el_modelo_sigue_siendo_invalido() -> None:
    """No se ha relajado nada: la frase ambigua sigue rechazandose."""
    v = OutputClaimValidator()
    assert not v.validate(
        "Los neutrofilos estan altos en este hemograma.", case_facts=HECHOS
    ).is_valid


def test_el_enum_del_parametro_no_lleva_la_familia_generica() -> None:
    esquema = construir_esquema_de_turno(HECHOS)
    assert esquema is not None
    codigos = esquema["properties"]["afirmaciones"]["items"]["properties"]["parametro"][
        "enum"
    ]
    assert codigos == ["NEU", "NEU_PCT"]
    # El modelo emite un CODIGO, nunca prosa: no puede escribir «neutrofilos».
    assert all(c.isupper() for c in codigos)


def test_el_valor_es_enum_de_cadenas_y_no_un_rango_numerico() -> None:
    """`minimum`/`maximum` no se enforcan para no-enteros. Un enum de cadenas si."""
    props = construir_esquema_de_turno(HECHOS)["properties"]["afirmaciones"]["items"][
        "properties"
    ]
    assert props["valor"] == {"enum": ["8.4", "85.0"]}
    assert "minimum" not in props["valor"]
    assert "maximum" not in props["valor"]
    assert all(isinstance(x, str) for x in props["valor"]["enum"])


def test_los_enum_se_construyen_POR_TURNO() -> None:
    """Menos candidatos, menos confusion: el gradiente medido era 0/5,7/11,5 %."""
    uno = construir_esquema_de_turno(HECHOS[:1])
    props = uno["properties"]["afirmaciones"]["items"]["properties"]
    assert props["parametro"]["enum"] == ["NEU"]
    assert props["valor"]["enum"] == ["8.4"]


def test_sin_hechos_no_hay_esquema() -> None:
    assert construir_esquema_de_turno([]) is None


def test_la_fecha_va_en_el_enum_a_proposito() -> None:
    props = construir_esquema_de_turno(HECHOS)["properties"]["afirmaciones"]["items"][
        "properties"
    ]
    assert props["fecha"] == {"enum": ["2026-01-10"]}


@pytest.mark.parametrize(
    ("codigo", "nombre", "esperado"),
    [
        ("NEU", "Neutrofilos", "Neutrofilos, recuento absoluto"),
        ("NEU_PCT", "Neutrofilos %", "Porcentaje de neutrofilos"),
        ("LYM_PCT", "Linfocitos %", "Porcentaje de linfocitos"),
    ],
)
def test_la_etiqueta_desambigua_las_dos_formas(
    codigo: str, nombre: str, esperado: str
) -> None:
    assert etiqueta_desambiguada(codigo, nombre) == esperado


def test_un_parametro_fuera_del_contexto_se_omite_en_vez_de_inventarse() -> None:
    """El enum lo impide, pero si llegara, no se fabrica un hecho."""
    texto = renderizar_afirmaciones(
        [AfirmacionSlot(parametro="PLT", estado="alto", valor="999")], HECHOS
    )
    assert texto == ""


def test_la_etiqueta_y_el_valor_van_en_clausulas_distintas() -> None:
    """El punto entre las dos ES el mecanismo. Si se pierde, vuelve el fallo."""
    texto = renderizar_afirmaciones(
        [AfirmacionSlot(parametro="NEU", estado="dentro_del_rango", valor="8.4")],
        HECHOS,
    )
    lineas = texto.splitlines()
    assert lineas[0] == "Neutrofilos, recuento absoluto."
    assert "8.4" not in lineas[0]
    assert "rango" not in lineas[0]
    assert "Neutrofilos" not in lineas[1]


# ── M.3 · el saneado de la prosa libre ──────────────────────────────────────


def test_la_prosa_saneada_no_lleva_cifras_del_paciente() -> None:
    """Si el modelo no puede escribir la cifra, no puede inventarla."""
    from app.modules.llm_chat.application.services.slot_rendering import sanear_prosa

    r = sanear_prosa(
        "Los neutrofilos son un tipo de globulo blanco. "
        "En este caso el valor es de 8.4. "
        "Su funcion es defender al organismo de infecciones."
    )
    assert "8.4" not in r.texto
    assert r.oraciones_quitadas == 1
    assert "cifra" in r.motivos
    # Y lo educativo se conserva: no es una mordaza, es un recorte.
    assert "globulo blanco" in r.texto
    assert "defender al organismo" in r.texto


def test_el_saneado_recorta_pero_NO_reintenta() -> None:
    """Anexo A §6: reintentar multiplicaria provider_calls. Se recorta."""
    from app.modules.llm_chat.application.services.slot_rendering import sanear_prosa

    r = sanear_prosa("Todo esto lleva 12.5 dentro.")
    assert r.texto == ""
    assert r.hubo_recorte
    # El resultado es un texto, no una excepcion ni una senal de reintento.
    assert isinstance(r.texto, str)


def test_el_saneado_quita_la_afirmacion_de_estado() -> None:
    from app.modules.llm_chat.application.services.slot_rendering import sanear_prosa

    r = sanear_prosa(
        "El hemograma mide varias poblaciones celulares. Los neutrofilos estan altos."
    )
    assert "altos" not in r.texto
    assert "estado" in r.motivos


def test_el_saneado_quita_el_diagnostico_definitivo() -> None:
    """definitive_diagnosis eran 6 fallos dados por irreducibles.

    `[MEDIDO]` Sanear cuesta 0,00 % sobre los 356 textos publicados: cero
    oraciones tocadas. Y el contenido que quita no deberia estar ahi.
    """
    from app.modules.llm_chat.application.services.slot_rendering import sanear_prosa

    r = sanear_prosa("Conviene revisar la serie roja. Tu perro tiene anemia.")
    assert "tiene anemia" not in r.texto
    assert "definitive_diagnosis" in r.motivos


def test_una_enumeracion_no_es_una_cifra_del_paciente() -> None:
    from app.modules.llm_chat.application.services.slot_rendering import sanear_prosa

    r = sanear_prosa("1. Los globulos rojos transportan oxigeno.")
    assert r.oraciones_quitadas == 0
    assert "globulos rojos" in r.texto


def test_la_fecha_y_la_unidad_no_cuentan_como_cifra_del_paciente() -> None:
    """La fecha aporta digitos, y la unidad `x10^3/uL` tambien. Ninguna es un valor."""
    from app.modules.llm_chat.application.services.slot_rendering import sanear_prosa

    r = sanear_prosa("El estudio del 2026-01-10 se informo en x10^3/uL.")
    assert r.oraciones_quitadas == 0


def test_el_texto_ensamblado_completo_pasa_el_validador() -> None:
    """El proposito de M.2 + M.3 juntos: slots del servidor + prosa saneada."""
    from app.modules.llm_chat.application.services.slot_rendering import sanear_prosa

    v = OutputClaimValidator()
    slots = renderizar_afirmaciones(
        [
            AfirmacionSlot(parametro="NEU", estado="dentro_del_rango", valor="8.4"),
            AfirmacionSlot(parametro="NEU_PCT", estado="alto", valor="85.0"),
        ],
        HECHOS,
    )
    prosa = sanear_prosa(
        "Los neutrofilos son la primera linea de defensa frente a infecciones "
        "bacterianas. Los neutrofilos estan altos. "
        "Conviene comentar estos resultados con tu veterinario."
    )
    final = f"{slots}\n\n{prosa.texto}"
    assert v.validate(final, case_facts=HECHOS).is_valid
    assert prosa.oraciones_quitadas == 1


# ── El cableado en el caso de uso ───────────────────────────────────────────


def _respuesta(texto: str):
    from app.modules.llm_chat.domain.entities import ModelResponse, TokenUsage

    return ModelResponse(
        text=texto,
        model="qwen",
        usage=TokenUsage(),
        duration_ms=1,
        finish_reason="stop",
    )


class _Stub:
    """Lo minimo para invocar los dos metodos sin construir el caso de uso."""

    server_writes_enabled = True


def _metodo(nombre: str):
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        SendChatMessageUseCase,
    )

    return getattr(SendChatMessageUseCase, nombre).__get__(_Stub(), _Stub)


def test_el_esquema_del_turno_sale_del_proveedor_de_slots() -> None:
    proveedor = _metodo("_slot_schema_provider")(facts=HECHOS)
    esquema, bloque = proveedor((), frozenset())
    # NINGUN bloque de prompt: la gramatica hace el trabajo, no una instruccion.
    assert bloque == ""
    props = esquema["properties"]["afirmaciones"]["items"]["properties"]
    assert props["parametro"]["enum"] == ["NEU", "NEU_PCT"]


def test_si_un_estudio_sale_del_presupuesto_sus_valores_salen_del_esquema() -> None:
    hechos = [
        {**HECHOS[0], "analysis_id": "a1"},
        {**HECHOS[1], "analysis_id": "a2"},
    ]
    proveedor = _metodo("_slot_schema_provider")(facts=hechos)
    esquema, _ = proveedor((), frozenset({"a1"}))
    props = esquema["properties"]["afirmaciones"]["items"]["properties"]
    assert props["parametro"]["enum"] == ["NEU"]


def test_el_decodificador_ensambla_y_registra_el_recorte() -> None:
    import json

    payload = json.dumps(
        {
            "afirmaciones": [
                {"parametro": "NEU", "estado": "dentro_del_rango", "valor": "8.4"}
            ],
            "explicacion": (
                "Los neutrofilos defienden frente a infecciones. "
                "Los neutrofilos estan altos."
            ),
        }
    )
    salida = _metodo("_decode_slot_generation")(_respuesta(payload), facts=HECHOS)
    assert "Neutrofilos, recuento absoluto." in salida.text
    assert "8.4" in salida.text
    assert "estan altos" not in salida.text
    # El sobre-rechazo de M.5 se lee de aqui.
    assert salida.provider_metrics["prosa_oraciones_quitadas"] == 1
    assert salida.provider_metrics["prosa_motivos_recorte"] == "estado"
    assert salida.provider_metrics["slots_emitidos"] == 1


def test_un_json_ilegible_se_devuelve_TAL_CUAL_y_lo_juzga_el_validador() -> None:
    """Inventar un fallback aqui persistiria una respuesta degradada sin contarla."""
    crudo = "esto no es json"
    salida = _metodo("_decode_slot_generation")(_respuesta(crudo), facts=HECHOS)
    assert salida.text == crudo


def test_el_texto_ensamblado_por_el_decodificador_pasa_el_validador() -> None:
    import json

    payload = json.dumps(
        {
            "afirmaciones": [
                {"parametro": "NEU", "estado": "dentro_del_rango", "valor": "8.4"},
                {"parametro": "NEU_PCT", "estado": "alto", "valor": "85.0"},
            ],
            "explicacion": "Conviene comentar estos resultados con tu veterinario.",
        }
    )
    salida = _metodo("_decode_slot_generation")(_respuesta(payload), facts=HECHOS)
    assert OutputClaimValidator().validate(salida.text, case_facts=HECHOS).is_valid
