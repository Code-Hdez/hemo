"""Barrido de retencion del chat: cierra lo vencido y borra la telemetria vieja.

Por que existe
--------------
``CHAT_SESSION_TTL_SECONDS`` solo escribia ``chat_sessions.expires_at``, y esa
columna nada mas filtra dos consultas (la resolucion automatica de conversacion
y el listado). Una conversacion "vencida" desaparecia de la lista pero seguia
activa en la base, y ninguna fila se borraba nunca: ``chat_turn_attempts`` crece
una fila por cada reintento del LLM y ``retrieval_events`` una por cada pregunta
del usuario, sin techo.

Que se cierra y que se borra
----------------------------
- Se CIERRA la conversacion vencida (``status='expired'``). Borrar la fila
  ``ChatSession`` esta prohibido: ``chat_messages.session_id`` y
  ``chat_turns.session_id`` son ON DELETE CASCADE, asi que eliminarla destruye
  la transcripcion completa — el invariante que documenta
  ``sqlalchemy_repositories.get_or_create`` y que ya causo un bug real (el
  logout borraba sesiones y el asistente "olvidaba" todo). El TTL pasa a ser un
  cambio de estado real en vez de un filtro de consulta, y el historial
  sobrevive en PostgreSQL.
- Se BORRAN las filas de ``chat_turn_attempts`` ya terminadas y viejas: son
  telemetria de ejecucion (proveedor, tokens, duracion, codigo de error) sin
  texto de la conversacion; lo que el reintento significa para el usuario vive
  en ``chat_turns`` (``attempt_count``, ``status``, ``error_code``), que no se
  toca. ``attempt_number`` se deriva de ``chat_turns.attempt_count``, no de un
  conteo de filas, de modo que borrarlas no colisiona con un reintento futuro.
- Se BORRAN los ``retrieval_events`` viejos: guardan el texto crudo de la
  pregunta del usuario y solo sirven para auditar el retrieval reciente. Es una
  tabla hoja, nadie la referencia.

La transcripcion (``chat_messages``/``chat_turns``) no se borra por antiguedad:
es el registro de lo que el asistente le dijo a un dueno sobre su mascota y
crece al ritmo de lo que una persona escribe, no de los reintentos del modelo.
Si algun dia hace falta una retencion dura sobre ella, debe ser una decision
explicita de politica de datos, no un efecto lateral de este barrido.

Uso
---
    python -m app.db.retention [--attempt-retention-days N]
                               [--retrieval-retention-days N]
                               [--batch-size N] [--dry-run]

Es un comando, no un hook de arranque: el proceso web no debe decidir cuando
barrer ni pagar ese trabajo en el primer request.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.llm_chat.domain.value_objects import TurnStatus
from app.modules.llm_chat.models import ChatSession, ChatTurnAttempt, RetrievalEvent
from app.shared.dates import utc_now

# Ventanas por defecto. Los intentos son diagnostico operativo: un mes cubre
# holgadamente cualquier investigacion de incidentes de generacion. El retrieval
# guarda texto del usuario, asi que su ventana es la unica que existe por
# minimizacion de datos, no por espacio.
DEFAULT_ATTEMPT_RETENTION_DAYS = 30
DEFAULT_RETRIEVAL_RETENTION_DAYS = 90
# Cada lote es una transaccion propia: la tabla que mas crece es justamente la
# que se barre, y un unico DELETE sobre millones de filas bloquearia al chat en
# vivo. Cortar en lotes tambien hace el barrido reanudable si se interrumpe.
DEFAULT_BATCH_SIZE = 1000

# Un intento en curso puede seguir siendo mutado por ``_finish_turn_attempt``
# (es el que devuelve ``_latest_attempt``), asi que nunca se borra.
_IN_FLIGHT_ATTEMPT_STATUSES = (TurnStatus.PENDING.value, TurnStatus.PROCESSING.value)


@dataclass(frozen=True)
class RetentionReport:
    closed_conversations: int
    deleted_turn_attempts: int
    deleted_retrieval_events: int

    def as_text(self) -> str:
        return (
            f"closed_conversations={self.closed_conversations} "
            f"deleted_turn_attempts={self.deleted_turn_attempts} "
            f"deleted_retrieval_events={self.deleted_retrieval_events}"
        )


def close_expired_conversations(
    session: Session, *, now: datetime, dry_run: bool = False
) -> int:
    """Marca como 'expired' las conversaciones activas cuyo TTL ya paso."""
    condition = (
        ChatSession.status == "active",
        ChatSession.expires_at.isnot(None),
        ChatSession.expires_at <= now,
    )
    if dry_run:
        return int(
            session.scalar(select(func.count(ChatSession.id)).where(*condition)) or 0
        )
    # ``updated_at`` queda intacto a proposito: es la ultima actividad real de
    # la conversacion y el orden con que se listan; un barrido automatico no es
    # actividad del usuario.
    result: Any = session.execute(
        update(ChatSession).where(*condition).values(status="expired")
    )
    session.commit()
    return int(result.rowcount or 0)


def purge_turn_attempts(
    session: Session,
    *,
    now: datetime,
    retention_days: int,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
) -> int:
    """Borra los intentos ya terminados anteriores a la ventana de retencion."""
    cutoff = now - timedelta(days=retention_days)
    condition = (
        ChatTurnAttempt.created_at < cutoff,
        ChatTurnAttempt.status.notin_(_IN_FLIGHT_ATTEMPT_STATUSES),
    )
    if dry_run:
        return int(
            session.scalar(select(func.count(ChatTurnAttempt.id)).where(*condition))
            or 0
        )
    return _delete_in_batches(session, ChatTurnAttempt, condition, batch_size)


def purge_retrieval_events(
    session: Session,
    *,
    now: datetime,
    retention_days: int,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
) -> int:
    """Borra los eventos de retrieval anteriores a la ventana de retencion."""
    cutoff = now - timedelta(days=retention_days)
    condition = (RetrievalEvent.created_at < cutoff,)
    if dry_run:
        return int(
            session.scalar(select(func.count(RetrievalEvent.id)).where(*condition)) or 0
        )
    return _delete_in_batches(session, RetrievalEvent, condition, batch_size)


def run_retention(
    session: Session,
    *,
    now: datetime | None = None,
    attempt_retention_days: int = DEFAULT_ATTEMPT_RETENTION_DAYS,
    retrieval_retention_days: int = DEFAULT_RETRIEVAL_RETENTION_DAYS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
) -> RetentionReport:
    """Ejecuta el barrido completo y retorna cuantas filas toco cada paso."""
    moment = now or utc_now()
    return RetentionReport(
        closed_conversations=close_expired_conversations(
            session, now=moment, dry_run=dry_run
        ),
        deleted_turn_attempts=purge_turn_attempts(
            session,
            now=moment,
            retention_days=attempt_retention_days,
            batch_size=batch_size,
            dry_run=dry_run,
        ),
        deleted_retrieval_events=purge_retrieval_events(
            session,
            now=moment,
            retention_days=retrieval_retention_days,
            batch_size=batch_size,
            dry_run=dry_run,
        ),
    )


def _delete_in_batches(
    session: Session,
    model: type[ChatTurnAttempt] | type[RetrievalEvent],
    condition: tuple[Any, ...],
    batch_size: int,
) -> int:
    deleted = 0
    while True:
        ids = list(
            session.scalars(select(model.id).where(*condition).limit(batch_size))
        )
        if not ids:
            return deleted
        session.execute(delete(model).where(model.id.in_(ids)))
        session.commit()
        deleted += len(ids)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.db.retention",
        description=(
            "Cierra las conversaciones de chat vencidas y borra la telemetria "
            "anterior a la ventana de retencion. Nunca borra transcripciones."
        ),
    )
    parser.add_argument(
        "--attempt-retention-days",
        type=int,
        default=DEFAULT_ATTEMPT_RETENTION_DAYS,
        help="Dias de intentos de turno a conservar (por defecto: %(default)s).",
    )
    parser.add_argument(
        "--retrieval-retention-days",
        type=int,
        default=DEFAULT_RETRIEVAL_RETENTION_DAYS,
        help="Dias de eventos de retrieval a conservar (por defecto: %(default)s).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Filas borradas por transaccion (por defecto: %(default)s).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Cuenta lo que borraria o cerraria sin modificar nada.",
    )
    args = parser.parse_args(argv)
    if args.attempt_retention_days < 1 or args.retrieval_retention_days < 1:
        parser.error("las ventanas de retencion se expresan en dias >= 1")
    if args.batch_size < 1:
        parser.error("--batch-size debe ser >= 1")
    return args


def main(argv: list[str] | None = None) -> RetentionReport:
    args = _parse_args(argv)
    with SessionLocal() as session:
        return run_retention(
            session,
            attempt_retention_days=args.attempt_retention_days,
            retrieval_retention_days=args.retrieval_retention_days,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    print(main().as_text())
