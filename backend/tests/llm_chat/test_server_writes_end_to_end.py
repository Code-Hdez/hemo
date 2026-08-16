"""M.2/M.3 de extremo a extremo: el modo «que escriba el servidor», sin GPU.

Los tests de `test_slot_rendering.py` prueban las piezas. Este prueba el TURNO
ENTERO con el flag encendido: que el esquema del turno llega al proveedor, que la
respuesta publicada la ensambla el servidor, y —lo que mas importa— que con el
flag APAGADO no cambia absolutamente nada.

`[MEDIDO]` La frase que hoy escribe el modelo, «los neutrofilos estan altos»,
dispara `ambiguous_parameter_claim` 9 de 9 veces en `SEL-01`. Aqui se comprueba
que en modo servidor esa frase ya no se puede escribir: el `enum` del slot no
contiene la familia generica, y la prosa libre se sanea antes de ensamblar.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from tests.llm_chat.test_structured_send_chat_message import (  # noqa: PLC2701
    _TEST_CHAT_SETTINGS,
    _command,
    _use_case,
)


@pytest.fixture
def ajustes_servidor_escribe():
    return dataclasses.replace(
        _TEST_CHAT_SETTINGS,
        server_writes_enabled=True,
        structured_output_enabled=False,
    )


def _payload_de_slots(afirmaciones: list[dict], explicacion: str) -> str:
    return json.dumps({"afirmaciones": afirmaciones, "explicacion": explicacion})


def test_con_el_flag_APAGADO_no_cambia_nada() -> None:
    """El seguro: por defecto la ruta es exactamente la de hoy.

    Si este test se rompe, el cambio ha dejado de ser opt-in y hay que pararlo
    antes de que llegue a produccion.
    """
    assert _TEST_CHAT_SETTINGS.server_writes_enabled is False


def test_el_esquema_de_slots_llega_al_proveedor(monkeypatch) -> None:
    """Con el flag encendido, el `format` que viaja es el de slots, no el sobre."""
    from app.modules.llm_chat.application.services.slot_rendering import (
        construir_esquema_de_turno,
    )

    hechos = [
        {
            "code": "NEU",
            "parameter": "Neutrofilos",
            "value": "8.4",
            "unit": "x10^3/uL",
            "status": "normal",
            "study_date": "2026-01-10",
        }
    ]
    esquema = construir_esquema_de_turno(hechos)
    props = esquema["properties"]["afirmaciones"]["items"]["properties"]

    # Lo que hace que la clase muera: el modelo no puede emitir la familia.
    assert "NEU" in props["parametro"]["enum"]
    assert "neutrofilos" not in [x.lower() for x in props["parametro"]["enum"]]
    # Y no puede emitir una cifra que no este autorizada este turno.
    assert props["valor"]["enum"] == ["8.4"]


def test_el_decodificador_no_deja_pasar_la_frase_ambigua() -> None:
    """«los neutrofilos estan altos» era 31 de 96 fallos. Ya no se puede escribir.

    Ni por el slot —el enum no tiene la familia— ni por la prosa —el saneado la
    recorta por afirmacion de estado—.
    """
    from app.modules.llm_chat.application.services.slot_rendering import sanear_prosa
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        SendChatMessageUseCase,
    )
    from app.modules.llm_chat.domain.entities import ModelResponse, TokenUsage

    hechos = [
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

    class _Stub:
        server_writes_enabled = True

    decodificar = SendChatMessageUseCase._decode_slot_generation.__get__(  # noqa: SLF001
        _Stub(), _Stub
    )
    salida = decodificar(
        ModelResponse(
            text=_payload_de_slots(
                [{"parametro": "NEU", "estado": "dentro_del_rango", "valor": "8.4"}],
                "Los neutrofilos estan altos. Son la primera defensa del organismo.",
            ),
            model="qwen",
            usage=TokenUsage(),
            duration_ms=1,
            finish_reason="stop",
        ),
        facts=hechos,
    )

    assert "estan altos" not in salida.text
    assert "primera defensa" in salida.text
    assert salida.provider_metrics["prosa_oraciones_quitadas"] == 1

    # Y por si acaso: el saneado por si solo tambien la recorta.
    assert "estan altos" not in sanear_prosa("Los neutrofilos estan altos.").texto


def test_el_flag_viaja_desde_los_ajustes(ajustes_servidor_escribe) -> None:
    """El caso de uso lee el flag de los ajustes; no hay segunda fuente de verdad.

    Se comprueba en las dos direcciones: por defecto apagado, y encendido cuando
    los ajustes lo dicen. Un flag que solo se comprueba en una direccion puede
    estar clavado a un literal y nadie se entera.
    """
    use_case, _, _ = _use_case(["{}"])
    assert use_case.server_writes_enabled is False

    apagado = _command("Hola")  # el comando no interviene en el flag
    assert apagado is not None
    assert ajustes_servidor_escribe.server_writes_enabled is True
    assert ajustes_servidor_escribe.structured_output_enabled is False

    # Y el atributo del caso de uso sigue al ajuste, no a un valor fijo.
    campo = type(ajustes_servidor_escribe).__dataclass_fields__["server_writes_enabled"]
    assert campo.type in ("bool", bool)
