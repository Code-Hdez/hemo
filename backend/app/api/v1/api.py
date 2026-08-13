"""Canonical registry for version 1 of the public API."""

from fastapi import APIRouter

from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.hematology.router import router as hematology_router
from app.modules.llm_chat.api.router import router as llm_chat_router
from app.modules.maps.router import router as maps_router
from app.modules.pets.router import router as pets_router
from app.modules.pet_history.router import router as pet_history_router
from app.modules.population_surveillance.router import (
    report_router as surveillance_report_router,
)
from app.modules.population_surveillance.router import router as surveillance_router

api_router = APIRouter(prefix=settings.API_V1_PREFIX)
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(hematology_router)
api_router.include_router(pets_router)
api_router.include_router(pet_history_router)
api_router.include_router(llm_chat_router)
api_router.include_router(maps_router)
api_router.include_router(surveillance_router)
api_router.include_router(surveillance_report_router)
