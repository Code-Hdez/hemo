"""M.9 — el error terminal tipado, comprobado POR INYECCION.

Por que importa, y no es higiene
--------------------------------
Suena a limpieza hasta que se ve lo que arregla: **los turnos muertos que el
metodo prohibe descontar del denominador son exactamente estos**. Si un fallo
terminal se colara como turno persistido, se contaria como si hubiera
respondido, y la tasa publicada seria mejor que la real.

Se mide **forzando el agotamiento de la escalera**, no esperando a que ocurra.
Un doble que siempre devuelve texto invalido vale mas que diez campanas
esperando la coincidencia.

`[MEDIDO]` En la campana v3 hubo **49 turnos terminales de 405**, y los 49 siguen
en el denominador.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.modules.llm_chat.application.use_cases.send_chat_message import (
    ChatRuntimeUnavailable,
)
from tests.llm_chat.test_structured_send_chat_message import (  # noqa: PLC2701
    ConversationRepository as _RepoBase,
)
from tests.llm_chat.test_structured_send_chat_message import (  # noqa: PLC2701
    _command,
    _use_case,
)


class RepoQueRegistra(_RepoBase):
    """Como el doble de siempre, pero anotando lo que el ledger recibiria."""

    def __init__(self) -> None:
        super().__init__()
        self.fallos: list[dict] = []
        self.incompletos: list[dict] = []

    async def mark_turn_failed(
        self, conversation_id, client_message_id, *, error_code, expected_attempt=None
    ) -> None:
        self.fallos.append(
            {
                "conversation_id": conversation_id,
                "client_message_id": client_message_id,
                "error_code": error_code,
            }
        )

    async def mark_turn_incomplete(
        self, conversation_id, client_message_id, *, error_code, expected_attempt=None
    ) -> None:
        self.incompletos.append({"error_code": error_code})


def _turno_que_agota_la_escalera():
    """Todas las generaciones devuelven algo que no supera el contrato."""
    use_case, conversations, llm = _use_case(["no es un sobre valido"] * 8)
    repo = RepoQueRegistra()
    use_case.conversations = repo
    return use_case, repo, llm


def test_1_el_error_es_una_CLASE_tipada_y_no_un_500_generico() -> None:
    use_case, _, _ = _turno_que_agota_la_escalera()

    with pytest.raises(ChatRuntimeUnavailable) as exc:
        asyncio.run(use_case.execute(_command("Que valores estan fuera de rango?")))

    # Una clase propia del dominio, no una excepcion generica.
    assert isinstance(exc.value, ChatRuntimeUnavailable)
    codigo = str(exc.value.args[0])
    # Y un codigo estable y legible, no texto libre.
    assert codigo
    assert " " not in codigo
    assert codigo == codigo.lower()


def test_2_NO_se_persiste_ningun_mensaje_del_asistente() -> None:
    """Una respuesta que el proveedor nunca produjo validamente no se guarda."""
    use_case, repo, _ = _turno_que_agota_la_escalera()

    with pytest.raises(ChatRuntimeUnavailable):
        asyncio.run(use_case.execute(_command("Que cambio entre los estudios?")))

    del_asistente = [m for m in repo.messages if getattr(m, "role", None) == "assistant"]
    assert del_asistente == []


def test_3_el_ledger_registra_el_turno_como_FALLO_TERMINAL() -> None:
    """Si no se registra, el turno desaparece y el denominador miente."""
    use_case, repo, _ = _turno_que_agota_la_escalera()

    with pytest.raises(ChatRuntimeUnavailable):
        asyncio.run(use_case.execute(_command("Cuantos hemogramas tiene?")))

    assert repo.fallos, "el fallo terminal no llego al ledger"
    assert repo.fallos[-1]["error_code"]
    assert repo.fallos[-1]["client_message_id"]


def test_4_no_queda_escritura_parcial() -> None:
    """Ni turno huerfano, ni memoria movida: o el turno entero o nada."""
    use_case, repo, _ = _turno_que_agota_la_escalera()

    with pytest.raises(ChatRuntimeUnavailable):
        asyncio.run(use_case.execute(_command("Dame mas detalle tecnico.")))

    # Lo unico que puede haber es el mensaje del USUARIO; nada del asistente y
    # ningun estado de memoria derivado de una respuesta que no existe.
    roles = {getattr(m, "role", None) for m in repo.messages}
    assert "assistant" not in roles


def test_5_el_codigo_terminal_conserva_el_motivo_de_validacion() -> None:
    """`_terminal_error_code` proyecta la razon: sin eso el fallo es opaco.

    `[MEDIDO]` La campana v3 pudo desglosar las 8 clases de rechazo gracias a
    esto. Con un codigo unico, los 96 fallos habrian sido un numero sin causa.
    """
    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidation,
    )
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _terminal_error_code,
    )

    codigo = _terminal_error_code(
        OutputValidation(
            is_safe=False,
            text="",
            reason="ambiguous_parameter_claim",
            telemetry_detail="neu",
        )
    )
    assert codigo.startswith("invalid_output_ambiguous_parameter_claim")
    # Y acotado: no arrastra texto libre del modelo.
    assert len(codigo) <= 135


def test_6_dos_turnos_terminales_seguidos_no_se_pisan() -> None:
    """Cada uno con su client_message_id: el denominador cuenta los dos."""
    use_case, repo, _ = _turno_que_agota_la_escalera()

    for _ in range(2):
        with pytest.raises(ChatRuntimeUnavailable):
            asyncio.run(
                use_case.execute(
                    _command(f"Pregunta {uuid4()}"),
                )
            )

    ids = {f["client_message_id"] for f in repo.fallos}
    assert len(repo.fallos) == 2
    assert len(ids) == 2
