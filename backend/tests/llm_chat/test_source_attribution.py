"""Fase 3 — las fuentes se derivan en el servidor, y con etiqueta honesta."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.llm_chat.application.services.source_attribution import (
    atribuir_fuentes,
)


@dataclass(frozen=True)
class _Chunk:
    id: str
    source_id: str
    text: str


FUENTES = [
    _Chunk(
        "c1",
        "S1",
        "La policitemia canina cursa con hematocrito elevado y eritrocitosis "
        "absoluta secundaria a hipoxia cronica renal.",
    ),
    _Chunk(
        "c2",
        "S2",
        "Las plaquetas agrupadas provocan pseudotrombocitopenia en el contador "
        "automatico y exigen revision del frotis sanguineo.",
    ),
]


def test_consultadas_es_un_hecho_del_servidor_no_del_modelo() -> None:
    """Lo que se puso en el prompt, lo diga el texto o no."""
    r = atribuir_fuentes("Una respuesta que no menciona nada de esto.", FUENTES)
    assert r.consultadas == ("S1", "S2")


def test_el_solapamiento_detecta_la_fuente_que_reaparece() -> None:
    r = atribuir_fuentes(
        "El hematocrito elevado sugiere eritrocitosis absoluta por hipoxia cronica.",
        FUENTES,
    )
    assert r.solapamiento[0].source_id == "S1"
    assert r.solapamiento[0].fraccion > r.solapamiento[-1].fraccion


def test_el_solapamiento_no_se_llama_evidencia() -> None:
    """La señal de desvío es dar lo recuperado como prueba de cada afirmación.

    El tipo no expone ningún campo que invite a confundirlo: ni `evidence`, ni
    `proof`, ni `supports`.
    """
    r = atribuir_fuentes("texto", FUENTES)
    campos = set(r.solapamiento[0].__slots__)
    assert not (campos & {"evidence", "proof", "supports", "evidencia", "prueba"})
    assert "terminos_compartidos" in campos


def test_las_palabras_comunes_no_inflan_el_solapamiento() -> None:
    """Sin filtro, cualquier texto en español solapa con cualquier fuente."""
    r = atribuir_fuentes("El de la los las que se por para con una y o en", FUENTES)
    assert all(s.terminos_compartidos == 0 for s in r.solapamiento)


def test_texto_vacio_conserva_las_consultadas() -> None:
    """Que el turno no produjera texto no borra lo que el servidor consultó."""
    r = atribuir_fuentes("", FUENTES)
    assert r.consultadas == ("S1", "S2")
    assert all(s.terminos_compartidos == 0 for s in r.solapamiento)


def test_sin_fuentes_no_inventa_ninguna() -> None:
    assert atribuir_fuentes("cualquier cosa", None).consultadas == ()
    assert atribuir_fuentes("cualquier cosa", []).consultadas == ()


def test_el_filtro_por_umbral_sigue_siendo_una_medida() -> None:
    r = atribuir_fuentes(
        "hematocrito elevado eritrocitosis absoluta hipoxia cronica renal "
        "policitemia canina cursa secundaria",
        FUENTES,
    )
    assert "S1" in r.por_encima_de(0.5)
    assert "S2" not in r.por_encima_de(0.5)
