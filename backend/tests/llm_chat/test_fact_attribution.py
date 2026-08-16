"""Fase 3 — la atribución de hechos se deriva, no se le pide al modelo."""

from __future__ import annotations

from app.modules.llm_chat.application.services.fact_attribution import (
    atribuir_hechos,
)


def _hecho(code, value, unit="x10^9/L", low=None, high=None, fid=None, nombre=None):
    return {
        "code": code,
        "value": value,
        "unit": unit,
        "reference_low": low,
        "reference_high": high,
        "status": "normal",
        "fact_id": fid or f"f_{code.lower()}",
        "canonical_name": nombre or code,
        "analysis_id": "a1",
        "study_key": "H1",
        "study_date": "2025-12-18",
    }


HECHOS = [
    _hecho("WBC", 15.23, low=5.5, high=16.9, nombre="leucocitos"),
    _hecho("RBC", 8.93, unit="x10^12/L", low=5.5, high=8.5, nombre="eritrocitos"),
    _hecho("HCT", 63.6, unit="%", low=37.0, high=55.0, nombre="hematocrito"),
]


def test_atribuye_la_cifra_al_hecho_cuyo_parametro_se_nombra_cerca() -> None:
    r = atribuir_hechos("El valor de los leucocitos (WBC) es de 15.23 x10^9/L.", HECHOS)
    assert r.fact_ids == ("f_wbc",)
    assert r.atribuidas[0].nombrado_cerca is True
    assert not r.hay_cifra_sin_respaldo


def test_una_cifra_que_no_corresponde_a_ningun_hecho_queda_sin_respaldo() -> None:
    """Es la señal de alucinación numérica, derivada del texto."""
    r = atribuir_hechos("Los leucocitos están en 22.4 x10^9/L.", HECHOS)
    assert r.hay_cifra_sin_respaldo
    assert 22.4 in r.sin_respaldo
    assert r.fact_ids == ()


def test_los_limites_del_rango_autorizado_no_son_alucinacion() -> None:
    """Decir «el rango es 5,5 a 16,9» no inventa nada: son datos inyectados."""
    r = atribuir_hechos("El rango de referencia va de 5.5 a 16.9 x10^9/L.", HECHOS)
    assert not r.hay_cifra_sin_respaldo


def test_acepta_la_coma_decimal_del_espanol() -> None:
    r = atribuir_hechos("El hematocrito es 63,6 %.", HECHOS)
    assert r.fact_ids == ("f_hct",)


def test_tolera_el_redondeo_de_la_prosa() -> None:
    """El modelo escribe «unos 15,2»; sigue siendo el mismo hecho."""
    r = atribuir_hechos("Los leucocitos rondan 15.2 x10^9/L.", HECHOS)
    assert r.fact_ids == ("f_wbc",)


def test_sin_nombre_cerca_solo_atribuye_si_el_valor_es_inequivoco() -> None:
    ambiguos = [_hecho("A", 10.0, fid="f_a"), _hecho("B", 10.0, fid="f_b")]
    assert atribuir_hechos("Vi un 10.0 por ahí.", ambiguos).fact_ids == ()
    # Con un unico candidato, el valor basta.
    assert atribuir_hechos("Vi un 10.0 por ahí.", [ambiguos[0]]).fact_ids == ("f_a",)


def test_declara_que_hechos_inyecto_el_servidor_y_el_texto_no_uso() -> None:
    """Cobertura medible sin exigirla: una respuesta puede citar 1 de 3."""
    r = atribuir_hechos("El hematocrito es 63.6 %.", HECHOS)
    assert r.fact_ids == ("f_hct",)
    assert r.no_usados == ("f_rbc", "f_wbc")


def test_texto_vacio_o_sin_hechos_no_atribuye_nada() -> None:
    assert atribuir_hechos("", HECHOS).fact_ids == ()
    assert atribuir_hechos("Un texto cualquiera.", None).fact_ids == ()


def test_varias_cifras_se_atribuyen_por_separado() -> None:
    r = atribuir_hechos(
        "Los leucocitos (WBC) están en 15.23 y el hematocrito en 63.6 %.", HECHOS
    )
    assert r.fact_ids == ("f_hct", "f_wbc")
    assert len(r.atribuidas) == 2


def test_sin_sobre_la_atribucion_no_se_pierde_sino_que_se_deriva() -> None:
    """El hueco que deja quitar el sobre lo cubre el servidor.

    Antes de la Fase 3, `verified_fact_ids` salía de `envelope.used_fact_ids` y
    quedaba VACÍO cuando la salida estructurada estaba apagada. Ahora se deriva
    del texto contra los hechos que el propio servidor inyectó, que es
    verificación en vez de autodeclaración.
    """
    import inspect

    from app.modules.llm_chat.application.use_cases import send_chat_message

    fuente = inspect.getsource(send_chat_message)
    assert "atribuir_hechos(candidate.text, coverage_facts).fact_ids" in fuente, (
        "el caso de uso debe derivar la atribución cuando no hay sobre"
    )
