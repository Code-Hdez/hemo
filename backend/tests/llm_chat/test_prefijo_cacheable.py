"""Fase 2 — el prefijo del prompt tiene que poder reutilizarse.

La caché de prefijo de Ollama es de prefijo EXACTO a nivel de token: un solo
token distinto la invalida desde ahí hasta el final. En la Puerta 0 se midió
que los turnos 2+ costaban entre el 72 % y el 1 368 % del prefill del turno 1,
es decir, que no se reutilizaba nada.

Estos tests fijan las dos condiciones que lo hacían imposible, para que nadie
las reintroduzca sin que salte algo.
"""

from __future__ import annotations

from app.modules.llm_chat.application.services.prompt_builder import PromptBuilder


def test_el_rol_system_no_cambia_de_turno_a_turno() -> None:
    """El system precede a TODO el prompt de usuario.

    Si varía por turno, rompe el prefijo en su primera línea variable y deja el
    prompt de usuario entero sin poder reutilizarse, por bien ordenado que esté.
    """
    base = "REGLAS BASE INMUTABLES"
    a = PromptBuilder._compose_system_prompt(
        base, {"generation_instruction": "Enfoque A para este turno"}
    )
    b = PromptBuilder._compose_system_prompt(
        base, {"generation_instruction": "Enfoque B, completamente distinto"}
    )
    assert a == b == base, "el rol system debe ser idéntico entre turnos"


def test_el_historial_no_se_reordena_por_la_pregunta() -> None:
    """Elegir turnos por solapamiento léxico los hace aparecer y desaparecer.

    Con eso, el bloque de historial cambia de contenido en cada turno y ninguna
    reutilización de prefijo es posible desde ahí.
    """

    class _Msg:
        def __init__(self, ident: str, content: str) -> None:
            self.id = ident
            self.client_message_id = ident
            self.content = content

        def __repr__(self) -> str:  # pragma: no cover - solo para fallos
            return f"<{self.id}>"

    historia = [_Msg(f"m{i}", f"contenido del turno {i}") for i in range(8)]

    con_termino = PromptBuilder._select_history(
        historia, question="contenido del turno 0", message_limit=4
    )
    sin_termino = PromptBuilder._select_history(
        historia, question="una pregunta sin ninguna palabra en comun", message_limit=4
    )
    assert con_termino == sin_termino, (
        "la selección de historial no puede depender de las palabras de la pregunta"
    )
    # Y lo que devuelve son los más recientes, en orden.
    assert [m.id for m in con_termino] == ["m6", "m7"]


def test_el_historial_conserva_el_orden_cronologico() -> None:
    """Una ventana de los N mas recientes NO puede ser un prefijo estable.

    Al llegar un turno nuevo la ventana se desplaza y el bloque cambia por el
    principio, asi que el historial NO pertenece al prefijo cacheable: vive en
    la cola volatil del prompt, junto a la memoria y al RAG. Lo que si se puede
    garantizar, y es lo que este test fija, es que el orden sea cronologico
    estricto y no dependa de la pregunta.
    """

    class _Msg:
        def __init__(self, ident: str) -> None:
            self.id = ident
            self.client_message_id = ident
            self.content = f"texto {ident}"

    historia = [_Msg(f"m{i}") for i in range(6)]
    salida = PromptBuilder._select_history(historia, question="q", message_limit=8)
    ids = [m.id for m in salida]
    assert ids == sorted(ids, key=lambda x: int(x[1:])), "el orden debe ser cronologico"
    assert ids[-1] == "m5", "el turno mas reciente no puede faltar"
