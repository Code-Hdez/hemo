"""
Capa de persistencia PostgreSQL para HemoVet.

Tablas:
  - users    : cuentas de dueños de mascotas
  - pets     : mascotas registradas por usuario
  - analyses : resultados de hemogramas (opcionalmente vinculados a user/pet)
  - breeds   : razas caninas normalizadas (catalogo)

Si DATABASE_URL no esta definida, todas las funciones operan sobre dicts
en memoria (fallback para desarrollo local sin Docker).

API publica
-----------
init_db()
save_analysis(data, user_id?, pet_id?) -> None
get_analysis(analysis_id) -> dict|None
list_analyses(limit, offset) -> list[dict]
count_analyses() -> int
list_analyses_for_user(user_id, pet_id?, limit, offset) -> list[dict]
count_analyses_for_user(user_id, pet_id?) -> int

create_user(id, email, hashed_password, full_name?) -> None
get_user_by_email(email) -> dict|None
get_user_by_id(user_id) -> dict|None

create_pet(id, owner_id, name, breed?, birth_year?, sex?, weight_kg?, notes?) -> None
list_pets(owner_id) -> list[dict]
get_pet(pet_id) -> dict|None
update_pet(pet_id, **fields) -> dict|None
delete_pet(pet_id) -> bool

list_breeds() -> list[str]
"""

from __future__ import annotations

import json
import logging
import uuid
import hashlib
from decimal import Decimal, InvalidOperation
from datetime import datetime

from sqlalchemy import (
    delete,
    func,
    select,
)
from sqlalchemy.orm import Session

from app.db.base import (
    Base,
    Analysis,
    AnalysisParameter,
    Breed,
    ChatMessage,
    ChatSession,
    DashboardMetric,
    EpidemiologyEvent,
    Pet,
    RagChunk,
    RagSource,
    RetrievalEvent,
    User,
)
from app.db.session import engine
from app.core.config import settings
# Las columnas DateTime de este modulo no llevan timezone, asi que la hora que
# se escribe depende de quien la genera. El modulo de chat siempre usa utc_now()
# y aqui se usaba datetime.now() (hora local del contenedor): las mismas fechas
# que ordenan el historial longitudinal quedaban en dos husos distintos. Se
# unifica en UTC ingenuo, que es lo que ya asume el resto del sistema.
from app.shared.dates import utc_now

logger = logging.getLogger("hemovet.db")

# ---------------------------------------------------------------------------
# Deteccion de modo: PostgreSQL vs memoria
# ---------------------------------------------------------------------------

_use_db = True

# Almacenes en memoria (fallback cuando no hay PostgreSQL disponible).
_memory_analyses: dict[str, dict] = {}
_memory_users: dict[str, dict] = {}
_memory_pets: dict[str, dict] = {}
_memory_breeds: list[str] = []
_memory_chat_sessions: dict[str, dict] = {}
_memory_chat_messages: list[dict] = []
_memory_rag_sources: dict[str, dict] = {}
_memory_rag_chunks: dict[str, dict] = {}
_memory_retrieval_events: list[dict] = []
_memory_dashboard_metrics: dict[str, dict] = {}
_memory_epidemiology_events: dict[str, dict] = {}
_UNSET = object()

# Razas caninas para siembra inicial del catalogo.
_BREEDS_SEED = [
    "Labrador Retriever",
    "Golden Retriever",
    "Pastor Alemán",
    "Bulldog Francés",
    "Beagle",
    "Poodle",
    "Rottweiler",
    "Yorkshire Terrier",
    "Boxer",
    "Dachshund",
    "Husky Siberiano",
    "Shih Tzu",
    "Chihuahua",
    "Doberman",
    "Border Collie",
    "Cocker Spaniel",
    "Schnauzer",
    "Maltés",
    "Pug",
    "Bichón Frisé",
    "Shar Pei",
    "Akita",
    "Chow Chow",
    "Dálmata",
    "Gran Danés",
    "San Bernardo",
    "Samoyedo",
    "Weimaraner",
    "Basenji",
    "Pitbull",
    "Bulldog Inglés",
    "Jack Russell Terrier",
    "Lhasa Apso",
    "Pomerania",
    "Caniche",
    "Cane Corso",
    "Mastín",
    "Sealyham Terrier",
    "Setter Irlandés",
    "Bull Terrier",
    "Braco Alemán",
    "Springer Spaniel",
    "Pekinés",
    "Whippet",
    "Galgo",
    "Basset Hound",
    "Bloodhound",
    "Bóxer",
    "Shiba Inu",
    "Mestizo",
]


# ---------------------------------------------------------------------------
# SQLAlchemy ORM
# ---------------------------------------------------------------------------


# Motor y sesion (inicializados en init_db).
def _get_engine():
    return engine


# ---------------------------------------------------------------------------
# API publica: inicializacion
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Initialize the selected persistence mode without migrating production.

    The legacy in-memory adapter remains useful for isolated tests and local
    fallback flows.  A real database schema is still created only in the
    explicit test environment; every other SQL deployment must use Alembic.
    """
    global _use_db

    if not _use_db:
        seed_breeds()
        return
    if settings.APP_ENV == "test":
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        _use_db = True
        seed_breeds()
        return
    raise RuntimeError(
        "Run 'alembic upgrade head'; application startup never creates schema"
    )


def seed_breeds() -> None:
    """Inserta las razas caninas iniciales si el catalogo esta vacio."""
    global _memory_breeds

    if not _use_db:
        if not _memory_breeds:
            _memory_breeds = sorted(_BREEDS_SEED)
        return

    engine = _get_engine()
    with Session(engine) as session:
        existing = session.execute(select(func.count(Breed.id))).scalar_one()
        if existing == 0:
            for nombre in _BREEDS_SEED:
                session.add(Breed(name=nombre))
            session.commit()
            logger.info("Catalogo de razas sembrado (%d razas)", len(_BREEDS_SEED))


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _strip_internal_fields(record: dict) -> dict:
    """Elimina claves internas antes de exponer un registro."""
    return {k: v for k, v in record.items() if not k.startswith("_")}


def _analysis_row_to_dict(row: Analysis) -> dict:
    """Convierte una fila de analisis a diccionario con campos internos."""
    result = json.loads(row.data)
    result["_user_id"] = row.user_id
    result["_pet_id"] = row.pet_id
    return result


# ---------------------------------------------------------------------------
# API publica: analyses
# ---------------------------------------------------------------------------


def save_analysis(
    data: dict, user_id: str | None = None, pet_id: str | None = None
) -> None:
    """Persiste un analisis. 'data' debe tener clave 'id'."""
    analysis_id = data["id"]
    created_at = data.get("created_at", utc_now().isoformat())

    if not _use_db:
        _memory_analyses[analysis_id] = {**data, "_user_id": user_id, "_pet_id": pet_id}
        return

    engine = _get_engine()
    row = Analysis(
        id=analysis_id,
        data=json.dumps(data, ensure_ascii=False),
        created_at=datetime.fromisoformat(created_at),
        user_id=user_id,
        pet_id=pet_id,
        performed_at=_datetime_or_none(data.get("created_at")),
        laboratory=_laboratory_from_analysis(data),
        extraction_confidence=_extraction_confidence_or_none(data),
        data_origin=str(data.get("extraction_provider") or "unknown"),
    )
    with Session(engine) as session:
        session.merge(row)
        session.flush()
        session.execute(
            delete(AnalysisParameter).where(
                AnalysisParameter.analysis_id == analysis_id
            )
        )
        for ordinal, item in enumerate(data.get("lab_values") or []):
            if not isinstance(item, dict):
                continue
            value_text = str(item.get("value") if item.get("value") is not None else "")
            # Every text column is truncated to its declared width, exactly as
            # migration 0007 does when it backfills these same rows. Without
            # it, `original_name` — which comes verbatim from an extracted PDF
            # and has no bounded length — overflows VARCHAR(180) on
            # PostgreSQL, and StringDataRightTruncation aborts the whole
            # save_analysis transaction: the hemogram is silently not stored.
            # SQLite ignores column widths, so the test suite never saw it.
            session.add(
                AnalysisParameter(
                    id=str(uuid.uuid4()),
                    analysis_id=analysis_id,
                    ordinal=ordinal,
                    canonical_name=str(
                        item.get("canonical_name") or item.get("name") or "unknown"
                    )[:80],
                    display_name=str(item.get("name") or "Parámetro")[:120],
                    original_name=(
                        str(item["original_name"])[:180]
                        if item.get("original_name") is not None
                        else None
                    ),
                    numeric_value=_decimal_or_none(item.get("value")),
                    value_text=value_text[:80],
                    original_unit=(
                        str(item["unit"])[:80] if item.get("unit") is not None else None
                    ),
                    normalized_unit=(
                        str(item["normalized_unit"])[:80]
                        if item.get("normalized_unit") is not None
                        else None
                    ),
                    reference_min=_decimal_or_none(item.get("ref_min")),
                    reference_max=_decimal_or_none(item.get("ref_max")),
                    reference_origin=str(
                        item.get("reference_origin") or "unknown"
                    )[:40],
                    recorded_flag=(
                        str(item["status"])[:30]
                        if item.get("status_origin") == "recorded"
                        and item.get("status") is not None
                        else None
                    ),
                    derived_flag=(
                        str(item["derived_status"])[:30]
                        if item.get("derived_status") is not None
                        else (
                            str(item["status"])[:30]
                            if item.get("status_origin") == "derived"
                            and item.get("status") is not None
                            else None
                        )
                    ),
                    extraction_confidence=_float_or_none(
                        item.get("extraction_confidence")
                    ),
                    notes=(str(item["notes"]) if item.get("notes") else None),
                    data_origin=str(item.get("data_origin") or "unknown")[:60],
                )
            )
        session.commit()


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _float_or_none(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return min(1.0, max(0.0, number))


def _datetime_or_none(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.replace(tzinfo=None) if parsed.tzinfo is not None else parsed


def _extraction_confidence_or_none(data: dict) -> float | None:
    """Retorna la confianza de EXTRACCION del documento, o None si no existe.

    Aqui se escribia data["confidence"], que formatter.py llena con
    prediction.confidence: la confianza del clasificador ML, no la de la
    digitalizacion. El chat la vuelve a leer como fact_type
    "extraction_confidence" y se la presenta al modelo como calidad de
    extraccion, de modo que una clasificacion segura se leia como un PDF bien
    leido. Solo se acepta una confianza declarada por el extractor; las
    confianzas por parametro que si existen viven en
    analysis_parameters.extraction_confidence y no se promedian aqui, porque un
    agregado seria un numero que ningun extractor emitio.
    """
    snapshot = data.get("_case_snapshot")
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    for candidate in (
        data.get("extraction_confidence"),
        snapshot.get("extraction_confidence"),
    ):
        confidence = _float_or_none(candidate)
        if confidence is not None:
            return confidence
    return None


def _laboratory_from_analysis(data: dict) -> str | None:
    direct = data.get("laboratory") or data.get("clinic")
    snapshot = data.get("_case_snapshot")
    if not direct and isinstance(snapshot, dict):
        direct = snapshot.get("laboratory") or snapshot.get("clinic")
        metadata = snapshot.get("metadata")
        if not direct and isinstance(metadata, dict):
            direct = metadata.get("laboratory") or metadata.get("clinic")
    text = str(direct).strip() if direct is not None else ""
    return text[:200] or None


def get_analysis(analysis_id: str) -> dict | None:
    """Retorna un analisis por ID o None si no existe."""
    if not _use_db:
        rec = _memory_analyses.get(analysis_id)
        return rec.copy() if rec else None

    engine = _get_engine()
    with Session(engine) as session:
        row = session.get(Analysis, analysis_id)
        if row is None:
            return None
        return _analysis_row_to_dict(row)


def list_analyses(limit: int = 50, offset: int = 0) -> list[dict]:
    """Retorna analisis ordenados por fecha (mas reciente primero)."""
    if not _use_db:
        items = sorted(
            _memory_analyses.values(),
            key=lambda d: d.get("created_at", ""),
            reverse=True,
        )
        return [_strip_internal_fields(d) for d in items[offset : offset + limit]]

    engine = _get_engine()
    stmt = (
        select(Analysis)
        .order_by(Analysis.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    with Session(engine) as session:
        rows = session.execute(stmt).scalars().all()
        return [_strip_internal_fields(_analysis_row_to_dict(r)) for r in rows]


def count_analyses() -> int:
    """Retorna el total de registros almacenados."""
    if not _use_db:
        return len(_memory_analyses)

    engine = _get_engine()
    with Session(engine) as session:
        result = session.execute(select(func.count(Analysis.id)))
        return result.scalar_one()


def list_analysis_records_for_user(
    user_id: str,
    pet_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Retorna analisis de un usuario preservando campos internos."""
    if not _use_db:
        items = [
            d.copy()
            for d in _memory_analyses.values()
            if d.get("_user_id") == user_id
            and (pet_id is None or d.get("_pet_id") == pet_id)
        ]
        items.sort(key=lambda d: d.get("created_at", ""), reverse=True)
        return items[offset : offset + limit]

    engine = _get_engine()
    stmt = select(Analysis).where(Analysis.user_id == user_id)
    if pet_id is not None:
        stmt = stmt.where(Analysis.pet_id == pet_id)
    stmt = stmt.order_by(Analysis.created_at.desc()).offset(offset).limit(limit)
    with Session(engine) as session:
        rows = session.execute(stmt).scalars().all()
        return [_analysis_row_to_dict(r) for r in rows]


def list_analyses_for_user(
    user_id: str,
    pet_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Retorna analisis de un usuario (opcionalmente filtrados por mascota)."""
    items = list_analysis_records_for_user(
        user_id, pet_id=pet_id, limit=limit, offset=offset
    )
    return [_strip_internal_fields(d) for d in items]


def count_analyses_for_user(user_id: str, pet_id: str | None = None) -> int:
    """Retorna el total de analisis de un usuario."""
    if not _use_db:
        return sum(
            1
            for d in _memory_analyses.values()
            if d.get("_user_id") == user_id
            and (pet_id is None or d.get("_pet_id") == pet_id)
        )

    engine = _get_engine()
    stmt = select(func.count(Analysis.id)).where(Analysis.user_id == user_id)
    if pet_id is not None:
        stmt = stmt.where(Analysis.pet_id == pet_id)
    with Session(engine) as session:
        return session.execute(stmt).scalar_one()


def save_dashboard_metric(key: str, payload: dict) -> None:
    """Persiste un payload JSON agregado para consumo del dashboard."""
    now = utc_now()

    if not _use_db:
        _memory_dashboard_metrics[key] = {
            "key": key,
            "data": payload,
            "updated_at": now.isoformat(),
        }
        return

    engine = _get_engine()
    row = DashboardMetric(
        key=key,
        data=json.dumps(payload, ensure_ascii=False),
        updated_at=now,
    )
    with Session(engine) as session:
        session.merge(row)
        session.commit()


def get_dashboard_metric(key: str) -> dict | None:
    """Retorna un payload de dashboard por clave o None si no existe."""
    if not _use_db:
        item = _memory_dashboard_metrics.get(key)
        if item is None:
            return None
        return dict(item["data"])

    engine = _get_engine()
    with Session(engine) as session:
        row = session.get(DashboardMetric, key)
        if row is None:
            return None
        return json.loads(row.data)


# ---------------------------------------------------------------------------
# API publica: epidemiologia
# ---------------------------------------------------------------------------


def _event_id(event: dict) -> str:
    raw = "|".join(
        str(event.get(key) or "") for key in ("analysis_id", "zone_code", "finding")
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _coerce_datetime(
    value: datetime | str | None, fallback: datetime | None = None
) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            normalized = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
        except ValueError:
            pass
    return fallback or utc_now()


def save_epidemiology_events(events: list[dict]) -> int:
    """Persiste eventos epidemiologicos idempotentes y retorna cuantos recibio."""
    if not events:
        return 0

    now = utc_now()
    normalized: list[dict] = []
    for event in events:
        item = dict(event)
        item["id"] = item.get("id") or _event_id(item)
        item["occurred_at"] = _coerce_datetime(item.get("occurred_at"), fallback=now)
        item["created_at"] = _coerce_datetime(item.get("created_at"), fallback=now)
        normalized.append(item)

    if not _use_db:
        for item in normalized:
            _memory_epidemiology_events[item["id"]] = {
                **item,
                "occurred_at": item["occurred_at"].isoformat(),
                "created_at": item["created_at"].isoformat(),
            }
        return len(normalized)

    engine = _get_engine()
    with Session(engine) as session:
        # Ensure referenced analyses exist to satisfy FK constraints in DB mode.
        analysis_ids = {item["analysis_id"] for item in normalized if item.get("analysis_id")}
        for aid in analysis_ids:
            if session.get(Analysis, aid) is None:
                placeholder = Analysis(id=aid, data=json.dumps({"id": aid}), created_at=now)
                session.add(placeholder)
        # Flush so placeholder analyses are present before inserting events.
        if analysis_ids:
            session.flush()

        for item in normalized:
            row = EpidemiologyEvent(
                id=item["id"],
                analysis_id=item["analysis_id"],
                pet_id=item.get("pet_id"),
                zone_code=item["zone_code"],
                zone_label=item["zone_label"],
                lat=float(item["lat"]),
                lng=float(item["lng"]),
                finding=item["finding"],
                severity=item["severity"],
                occurred_at=item["occurred_at"],
                created_at=item["created_at"],
            )
            session.merge(row)
        session.commit()
    return len(normalized)


def list_epidemiology_events(limit: int = 5000, offset: int = 0) -> list[dict]:
    """Retorna eventos epidemiologicos ordenados por fecha clinica descendente."""
    if not _use_db:
        items = sorted(
            _memory_epidemiology_events.values(),
            key=lambda d: d.get("occurred_at", ""),
            reverse=True,
        )
        return [dict(item) for item in items[offset : offset + limit]]

    engine = _get_engine()
    stmt = (
        select(EpidemiologyEvent)
        .order_by(EpidemiologyEvent.occurred_at.desc())
        .offset(offset)
        .limit(limit)
    )
    with Session(engine) as session:
        rows = session.execute(stmt).scalars().all()
        return [_epidemiology_event_row_to_dict(row) for row in rows]


def delete_epidemiology_events_for_analysis(analysis_id: str) -> int:
    """Elimina eventos epidemiologicos derivados de un analisis."""
    if not analysis_id:
        return 0

    if not _use_db:
        ids = [
            event_id
            for event_id, item in _memory_epidemiology_events.items()
            if item.get("analysis_id") == analysis_id
        ]
        for event_id in ids:
            del _memory_epidemiology_events[event_id]
        return len(ids)

    engine = _get_engine()
    with Session(engine) as session:
        rows = (
            session.execute(
                select(EpidemiologyEvent).where(
                    EpidemiologyEvent.analysis_id == analysis_id
                )
            )
            .scalars()
            .all()
        )
        count = len(rows)
        for row in rows:
            session.delete(row)
        session.commit()
        return count


def delete_epidemiology_events_for_pet(pet_id: str) -> int:
    """Elimina eventos epidemiologicos derivados de una mascota."""
    if not pet_id:
        return 0

    if not _use_db:
        ids = [
            event_id
            for event_id, item in _memory_epidemiology_events.items()
            if item.get("pet_id") == pet_id
        ]
        for event_id in ids:
            del _memory_epidemiology_events[event_id]
        return len(ids)

    engine = _get_engine()
    with Session(engine) as session:
        rows = (
            session.execute(
                select(EpidemiologyEvent).where(EpidemiologyEvent.pet_id == pet_id)
            )
            .scalars()
            .all()
        )
        count = len(rows)
        for row in rows:
            session.delete(row)
        session.commit()
        return count


def epidemiology_revision() -> str:
    """Retorna una revision liviana para SSE/polling."""
    if not _use_db:
        if not _memory_epidemiology_events:
            return "0:"
        latest = max(
            str(item.get("created_at") or "")
            for item in _memory_epidemiology_events.values()
        )
        return f"{len(_memory_epidemiology_events)}:{latest}"

    engine = _get_engine()
    with Session(engine) as session:
        count = session.execute(select(func.count(EpidemiologyEvent.id))).scalar_one()
        latest = session.execute(
            select(func.max(EpidemiologyEvent.created_at))
        ).scalar_one()
        latest_text = latest.isoformat() if latest else ""
        return f"{int(count)}:{latest_text}"


def _epidemiology_event_row_to_dict(row: EpidemiologyEvent) -> dict:
    return {
        "id": row.id,
        "analysis_id": row.analysis_id,
        "pet_id": row.pet_id,
        "zone_code": row.zone_code,
        "zone_label": row.zone_label,
        "lat": row.lat,
        "lng": row.lng,
        "finding": row.finding,
        "severity": row.severity,
        "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def get_latest_analysis_for_pet(user_id: str, pet_id: str) -> dict | None:
    """Retorna el analisis mas reciente de una mascota del usuario."""
    items = list_analysis_records_for_user(user_id, pet_id=pet_id, limit=1, offset=0)
    return items[0] if items else None


def get_latest_analysis_for_user(user_id: str) -> dict | None:
    """Retorna el analisis mas reciente de un usuario."""
    items = list_analysis_records_for_user(user_id, limit=1, offset=0)
    return items[0] if items else None


# ---------------------------------------------------------------------------
# API publica: users
# ---------------------------------------------------------------------------


def create_user(
    user_id: str,
    email: str,
    hashed_password: str,
    full_name: str | None = None,
    role: str = "user",
) -> None:
    """Inserta un nuevo usuario en la base de datos."""
    now = utc_now()

    if not _use_db:
        _memory_users[user_id] = {
            "id": user_id,
            "email": email,
            "hashed_password": hashed_password,
            "full_name": full_name,
            "created_at": now.isoformat(),
            "is_active": True,
            "role": role,
            "onboarding_tour_status": "pending",
            "onboarding_tour_version": None,
            "onboarding_tour_dismissed_at": None,
        }
        return

    engine = _get_engine()
    row = User(
        id=user_id,
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        created_at=now,
        is_active=True,
        role=role,
        onboarding_tour_status="pending",
    )
    with Session(engine) as session:
        session.add(row)
        session.commit()


def get_user_by_email(email: str) -> dict | None:
    """Busca un usuario por email. Retorna None si no existe."""
    if not _use_db:
        return next((u for u in _memory_users.values() if u["email"] == email), None)

    engine = _get_engine()
    stmt = select(User).where(User.email == email)
    with Session(engine) as session:
        row = session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return _user_row_to_dict(row)


def get_user_by_id(user_id: str) -> dict | None:
    """Busca un usuario por ID. Retorna None si no existe."""
    if not _use_db:
        return _memory_users.get(user_id)

    engine = _get_engine()
    with Session(engine) as session:
        row = session.get(User, user_id)
        if row is None:
            return None
        return _user_row_to_dict(row)


def update_user_onboarding_tour(
    user_id: str, *, status: str, version: str
) -> dict | None:
    """Marca el tutorial global como completado o saltado para un usuario."""
    dismissed_at = utc_now()

    if not _use_db:
        user = _memory_users.get(user_id)
        if user is None:
            return None
        user.update(
            {
                "onboarding_tour_status": status,
                "onboarding_tour_version": version,
                "onboarding_tour_dismissed_at": dismissed_at.isoformat(),
            }
        )
        return dict(user)

    engine = _get_engine()
    with Session(engine) as session:
        row = session.get(User, user_id)
        if row is None:
            return None
        row.onboarding_tour_status = status
        row.onboarding_tour_version = version
        row.onboarding_tour_dismissed_at = dismissed_at
        session.commit()
        session.refresh(row)
        return _user_row_to_dict(row)


def _user_row_to_dict(row: User) -> dict:
    """Convierte una fila User a diccionario."""
    return {
        "id": row.id,
        "email": row.email,
        "hashed_password": row.hashed_password,
        "full_name": row.full_name,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "is_active": row.is_active,
        "role": row.role,
        "onboarding_tour_status": row.onboarding_tour_status,
        "onboarding_tour_version": row.onboarding_tour_version,
        "onboarding_tour_dismissed_at": (
            row.onboarding_tour_dismissed_at.isoformat()
            if row.onboarding_tour_dismissed_at
            else None
        ),
    }


# ---------------------------------------------------------------------------
# API publica: pets
# ---------------------------------------------------------------------------


def create_pet(
    pet_id: str,
    owner_id: str,
    name: str,
    breed: str | None = None,
    birth_year: int | None = None,
    sex: str | None = None,
    weight_kg: float | None = None,
    notes: str | None = None,
    residence_zone_code: str | None = None,
    residence_label: str | None = None,
    residence_lat: float | None = None,
    residence_lng: float | None = None,
    residence_precision: str | None = None,
    residence_consent_at: datetime | None = None,
    profile_photo_key: str | None = None,
) -> dict:
    """Inserta una nueva mascota y retorna el dict resultante."""
    now = utc_now()
    pet = {
        "id": pet_id,
        "owner_id": owner_id,
        "name": name,
        "breed": breed,
        "birth_year": birth_year,
        "sex": sex,
        "weight_kg": weight_kg,
        "notes": notes,
        "residence_zone_code": residence_zone_code,
        "residence_label": residence_label,
        "residence_lat": residence_lat,
        "residence_lng": residence_lng,
        "residence_precision": residence_precision,
        "residence_consent_at": (
            residence_consent_at.isoformat() if residence_consent_at else None
        ),
        "residence_consent": residence_consent_at is not None,
        "profile_photo_key": profile_photo_key,
        "created_at": now.isoformat(),
    }

    if not _use_db:
        _memory_pets[pet_id] = pet
        return pet

    engine = _get_engine()
    row = Pet(
        id=pet_id,
        owner_id=owner_id,
        name=name,
        breed=breed,
        birth_year=birth_year,
        sex=sex,
        weight_kg=weight_kg,
        notes=notes,
        residence_zone_code=residence_zone_code,
        residence_label=residence_label,
        residence_lat=residence_lat,
        residence_lng=residence_lng,
        residence_precision=residence_precision,
        residence_consent_at=residence_consent_at,
        profile_photo_key=profile_photo_key,
        created_at=now,
    )
    with Session(engine) as session:
        # Ensure owner exists to satisfy FK constraints in DB mode
        owner = session.get(User, owner_id)
        if owner is None:
            session.add(
                User(
                    id=owner_id,
                    email=f"{owner_id}@example.invalid",
                    hashed_password="__placeholder__",
                    full_name=None,
                    created_at=now,
                    is_active=True,
                    role="user",
                )
            )
            # Flush so the new user is persisted before inserting the pet
            # (ensures FK constraint is satisfied regardless of insert ordering)
            session.flush()
        session.add(row)
        session.commit()
    return pet


def list_pets(owner_id: str) -> list[dict]:
    """Retorna todas las mascotas de un usuario."""
    if not _use_db:
        return [p for p in _memory_pets.values() if p["owner_id"] == owner_id]

    engine = _get_engine()
    stmt = select(Pet).where(Pet.owner_id == owner_id).order_by(Pet.created_at)
    with Session(engine) as session:
        rows = session.execute(stmt).scalars().all()
        return [_pet_row_to_dict(r) for r in rows]


def get_pet(pet_id: str) -> dict | None:
    """Retorna una mascota por ID o None."""
    if not _use_db:
        return _memory_pets.get(pet_id)

    engine = _get_engine()
    with Session(engine) as session:
        row = session.get(Pet, pet_id)
        if row is None:
            return None
        return _pet_row_to_dict(row)


def count_pet_breeds() -> list[tuple[str, int]]:
    """Retorna pares (raza, conteo) agregando todas las mascotas del sistema."""
    if not _use_db:
        counter: dict[str, int] = {}
        for p in _memory_pets.values():
            b = (p.get("breed") or "").strip()
            if not b:
                continue
            counter[b] = counter.get(b, 0) + 1
        return sorted(counter.items(), key=lambda kv: kv[1], reverse=True)

    engine = _get_engine()
    stmt = (
        select(Pet.breed, func.count(Pet.id))
        .where(Pet.breed.isnot(None))
        .where(Pet.breed != "")
        .group_by(Pet.breed)
        .order_by(func.count(Pet.id).desc())
    )
    with Session(engine) as session:
        rows = session.execute(stmt).all()
        return [(str(breed).strip(), int(count)) for breed, count in rows if breed]


def find_pets_for_user_by_name(
    user_id: str | None, query: str, limit: int = 5
) -> list[dict]:
    """Busca mascotas del usuario por nombre con matching exacto, normalizado y fuzzy."""
    from app.modules.llm_chat.utils import (
        contains_whole_phrase,
        fuzzy_ratio,
        normalize_text,
        tokenize,
    )

    if not user_id:
        return []

    pets = list_pets(user_id)
    query_norm = normalize_text(query)
    tokens = tokenize(query)
    matches: list[tuple[float, dict]] = []
    for pet in pets:
        name = pet.get("name") or ""
        name_norm = normalize_text(name)
        if not name_norm:
            continue

        score = 0.0
        if contains_whole_phrase(query_norm, name_norm):
            score = 1.0
        elif name_norm in query_norm:
            score = 0.96
        else:
            ratios = [fuzzy_ratio(name_norm, query_norm)]
            ratios.extend(fuzzy_ratio(name_norm, token) for token in tokens)
            score = max(ratios) if ratios else 0.0

        if score >= 0.88:
            matches.append((score, pet))

    matches.sort(key=lambda item: (-item[0], item[1].get("name") or ""))
    return [pet for _, pet in matches[:limit]]


def update_pet(pet_id: str, **fields) -> dict | None:
    """Actualiza campos de una mascota y retorna el dict actualizado."""
    if not _use_db:
        pet = _memory_pets.get(pet_id)
        if pet is None:
            return None
        for k, v in fields.items():
            if k.startswith("residence_"):
                pet[k] = v
                continue
            if v is not None:
                pet[k] = v
        pet["residence_consent"] = pet.get("residence_consent_at") is not None
        return pet

    engine = _get_engine()
    with Session(engine) as session:
        row = session.get(Pet, pet_id)
        if row is None:
            return None
        for k, v in fields.items():
            if not hasattr(row, k):
                continue
            if k.startswith("residence_"):
                setattr(row, k, v)
                continue
            if v is not None:
                setattr(row, k, v)
        session.commit()
        session.refresh(row)
        return _pet_row_to_dict(row)


def set_pet_profile_photo_key(
    pet_id: str, profile_photo_key: str | None
) -> dict | None:
    """Actualiza explicitamente la foto, incluyendo la eliminacion con ``None``."""
    if not _use_db:
        pet = _memory_pets.get(pet_id)
        if pet is None:
            return None
        pet["profile_photo_key"] = profile_photo_key
        return pet

    engine = _get_engine()
    with Session(engine) as session:
        row = session.get(Pet, pet_id)
        if row is None:
            return None
        row.profile_photo_key = profile_photo_key
        session.commit()
        session.refresh(row)
        return _pet_row_to_dict(row)


def delete_pet(pet_id: str) -> bool:
    """Elimina una mascota. Retorna True si existia, False si no."""
    if not _use_db:
        if pet_id in _memory_pets:
            del _memory_pets[pet_id]
            return True
        return False

    engine = _get_engine()
    with Session(engine) as session:
        row = session.get(Pet, pet_id)
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def _pet_row_to_dict(row: Pet) -> dict:
    """Convierte una fila Pet a diccionario."""
    return {
        "id": row.id,
        "owner_id": row.owner_id,
        "name": row.name,
        "breed": row.breed,
        "birth_year": row.birth_year,
        "sex": row.sex,
        "weight_kg": row.weight_kg,
        "notes": row.notes,
        "residence_zone_code": row.residence_zone_code,
        "residence_label": row.residence_label,
        "residence_lat": row.residence_lat,
        "residence_lng": row.residence_lng,
        "residence_precision": row.residence_precision,
        "residence_consent_at": (
            row.residence_consent_at.isoformat() if row.residence_consent_at else None
        ),
        "residence_consent": row.residence_consent_at is not None,
        "profile_photo_key": row.profile_photo_key,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# ---------------------------------------------------------------------------
# API publica: chat / rag
# ---------------------------------------------------------------------------


def get_chat_session(session_id: str) -> dict | None:
    """Retorna una sesion de chat por ID."""
    if not _use_db:
        session = _memory_chat_sessions.get(session_id)
        return session.copy() if session else None

    engine = _get_engine()
    with Session(engine) as session:
        row = session.get(ChatSession, session_id)
        if row is None:
            return None
        return {
            "id": row.id,
            "user_id": row.user_id,
            "active_pet_id": row.active_pet_id,
            "active_analysis_id": row.active_analysis_id,
            "active_source_id": row.active_source_id,
            "active_topic": row.active_topic,
            "last_mode": row.last_mode,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


def get_or_create_chat_session(
    session_id: str | None = None,
    user_id: str | None = None,
    last_mode: str = "auto",
) -> dict:
    """Obtiene o crea una sesion de chat persistente."""
    now = utc_now().isoformat()

    if session_id:
        existing = get_chat_session(session_id)
        if existing is not None:
            # Nunca reutilizamos una sesion si cambia el usuario autenticado
            # o si una sesion privada intenta abrirse sin autenticacion.
            if existing.get("user_id") != user_id:
                session_id = None
            else:
                return existing

    new_id = session_id or str(uuid.uuid4())
    record = {
        "id": new_id,
        "user_id": user_id,
        "active_pet_id": None,
        "active_analysis_id": None,
        "active_source_id": None,
        "active_topic": None,
        "last_mode": last_mode,
        "created_at": now,
        "updated_at": now,
    }

    if not _use_db:
        _memory_chat_sessions[new_id] = record
        return record.copy()

    engine = _get_engine()
    row = ChatSession(
        id=new_id,
        user_id=user_id,
        last_mode=last_mode or "auto",
        created_at=datetime.fromisoformat(now),
        updated_at=datetime.fromisoformat(now),
    )
    with Session(engine) as session:
        session.merge(row)
        session.commit()
    return record


def update_chat_session_context(
    session_id: str,
    *,
    active_pet_id: str | None | object = _UNSET,
    active_analysis_id: str | None | object = _UNSET,
    active_source_id: str | None | object = _UNSET,
    active_topic: str | None | object = _UNSET,
    last_mode: str | None | object = _UNSET,
) -> dict | None:
    """Actualiza el contexto activo de una sesion de chat."""
    now = utc_now().isoformat()
    if not _use_db:
        record = _memory_chat_sessions.get(session_id)
        if record is None:
            return None
        if active_pet_id is not _UNSET:
            record["active_pet_id"] = active_pet_id
        if active_analysis_id is not _UNSET:
            record["active_analysis_id"] = active_analysis_id
        if active_source_id is not _UNSET:
            record["active_source_id"] = active_source_id
        if active_topic is not _UNSET:
            record["active_topic"] = active_topic
        if last_mode is not _UNSET:
            record["last_mode"] = last_mode
        record["updated_at"] = now
        return record.copy()

    engine = _get_engine()
    with Session(engine) as session:
        row = session.get(ChatSession, session_id)
        if row is None:
            return None
        if active_pet_id is not _UNSET:
            row.active_pet_id = active_pet_id
        if active_analysis_id is not _UNSET:
            row.active_analysis_id = active_analysis_id
        if active_source_id is not _UNSET:
            row.active_source_id = active_source_id
        if active_topic is not _UNSET:
            row.active_topic = active_topic
        if last_mode is not _UNSET:
            row.last_mode = last_mode
        row.updated_at = datetime.fromisoformat(now)
        session.commit()
        return get_chat_session(session_id)


def create_chat_message(
    session_id: str,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> dict:
    """Persiste un mensaje del chat."""
    message_id = str(uuid.uuid4())
    now = utc_now().isoformat()
    record = {
        "id": message_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "metadata": metadata or {},
        "created_at": now,
    }

    if not _use_db:
        _memory_chat_messages.append(record)
        return record.copy()

    engine = _get_engine()
    with Session(engine) as session:
        chat_session = session.scalar(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .with_for_update()
        )
        if chat_session is None:
            raise ValueError("Chat session not found")
        turn_index = max(1, int(chat_session.next_turn_index or 1))
        chat_session.next_turn_index = turn_index + 1
        row = ChatMessage(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
            context_revision=int(chat_session.context_revision or 1),
            turn_index=turn_index,
            created_at=datetime.fromisoformat(now),
        )
        session.add(row)
        session.commit()
    return record


def create_retrieval_event(
    *,
    session_id: str,
    user_id: str | None,
    analysis_id: str | None,
    query_text: str,
    resolved_context: dict | None,
    top_sources: list[dict] | None,
) -> dict:
    """Persiste un evento de retrieval para auditoria."""
    event_id = str(uuid.uuid4())
    now = utc_now().isoformat()
    record = {
        "id": event_id,
        "session_id": session_id,
        "user_id": user_id,
        "analysis_id": analysis_id,
        "query_text": query_text,
        "resolved_context": resolved_context or {},
        "top_sources": top_sources or [],
        "created_at": now,
    }

    if not _use_db:
        _memory_retrieval_events.append(record)
        return record.copy()

    engine = _get_engine()
    row = RetrievalEvent(
        id=event_id,
        session_id=session_id,
        user_id=user_id,
        analysis_id=analysis_id,
        query_text=query_text,
        resolved_context_json=json.dumps(resolved_context or {}, ensure_ascii=False),
        top_sources_json=json.dumps(top_sources or [], ensure_ascii=False),
        created_at=datetime.fromisoformat(now),
    )
    with Session(engine) as session:
        session.add(row)
        session.commit()
    return record


def upsert_rag_source(
    source_id: str,
    title: str,
    source_type: str,
    metadata: dict | None = None,
) -> None:
    """Inserta o actualiza una fuente del corpus."""
    now = utc_now().isoformat()
    record = {
        "id": source_id,
        "title": title,
        "source_type": source_type,
        "metadata": metadata or {},
        "updated_at": now,
    }

    if not _use_db:
        _memory_rag_sources[source_id] = record
        return

    engine = _get_engine()
    row = RagSource(
        id=source_id,
        title=title,
        source_type=source_type,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        updated_at=datetime.fromisoformat(now),
        created_at=datetime.fromisoformat(now),
    )
    with Session(engine) as session:
        session.merge(row)
        session.commit()


def save_rag_chunks(chunks: list[dict]) -> None:
    """Guarda chunks del corpus RAG."""
    if not chunks:
        return

    if not _use_db:
        for chunk in chunks:
            _memory_rag_chunks[chunk["id"]] = chunk
        return

    engine = _get_engine()
    with Session(engine) as session:
        for chunk in chunks:
            row = RagChunk(
                id=chunk["id"],
                source_id=chunk["source_id"],
                title=chunk["title"],
                text=chunk["text"],
                raw_text=chunk.get("raw_text"),
                clean_text=chunk.get("clean_text"),
                retrieval_text=chunk.get("retrieval_text"),
                source_type=chunk["source_type"],
                chunk_type=chunk.get("chunk_type"),
                metadata_json=json.dumps(
                    chunk.get("metadata") or {}, ensure_ascii=False
                ),
                created_at=utc_now(),
            )
            session.merge(row)
        session.commit()


# ---------------------------------------------------------------------------
# API publica: breeds
# ---------------------------------------------------------------------------


def list_breeds() -> list[str]:
    """Retorna la lista de nombres de razas caninas ordenada alfabeticamente."""
    if not _use_db:
        return sorted(_memory_breeds)

    engine = _get_engine()
    stmt = select(Breed.name).order_by(Breed.name)
    with Session(engine) as session:
        return list(session.execute(stmt).scalars().all())
