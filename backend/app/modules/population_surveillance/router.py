"""
Router FastAPI para el módulo de epidemiología comunitaria.

Endpoints:
  GET /api/v1/epidemiology/points       -- Puntos georeferenciados para el mapa
  GET /api/v1/epidemiology/stream       -- Stream SSE de actualizaciones del mapa
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from .repository import current_revision
from .schemas import EpidemiologyPoint, SurveillanceReport
from .service import get_epidemiology_points, surveillance_report

router = APIRouter(prefix="/epidemiology", tags=["Population Surveillance"])
report_router = APIRouter(prefix="/surveillance", tags=["Population Surveillance"])


@router.get("/points", response_model=list[EpidemiologyPoint])
def get_points(
    finding: str | None = Query(default=None, max_length=160),
    period_days: int = Query(default=365, ge=7, le=365),
) -> list[EpidemiologyPoint]:
    """Puntos agregados del mapa epidemiologico, sin identificadores individuales."""
    return get_epidemiology_points(finding=finding, period_days=period_days)


@report_router.get("/report", response_model=SurveillanceReport)
def get_report(
    period_days: int = Query(default=30, ge=7, le=365)
) -> SurveillanceReport:
    return surveillance_report(period_days)


@router.get("/stream")
async def stream_updates() -> StreamingResponse:
    """SSE: avisa al frontend que el mapa debe refrescar sus puntos."""

    async def event_generator():
        last_revision = current_revision()
        yield _sse("snapshot", last_revision)

        while True:
            await asyncio.sleep(5)
            revision = current_revision()
            if revision != last_revision:
                last_revision = revision
                yield _sse("map_updated", revision)
            else:
                yield _sse("heartbeat", revision)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(event_type: str, revision: str) -> str:
    payload = {
        "type": event_type,
        "revision": revision,
        "updated_at": datetime.now().isoformat(),
    }
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
