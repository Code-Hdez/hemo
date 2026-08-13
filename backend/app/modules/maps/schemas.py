from __future__ import annotations

from pydantic import BaseModel, Field


class ResidenceZoneOut(BaseModel):
    code: str
    label: str
    province: str
    municipality: str
    lat: float
    lng: float
    precision: str = "municipality"


class ResidenceResolveRequest(BaseModel):
    query: str = Field(min_length=3, max_length=300)
    limit: int = Field(default=5, ge=1, le=8)


class ResidenceCandidateOut(BaseModel):
    id: str
    label: str
    lat: float
    lng: float
    precision: str
    source: str


class NearbyVeterinaryCareRequest(BaseModel):
    pet_id: str = Field(min_length=1, max_length=120)
    radius_meters: int = Field(default=10_000, ge=1_000, le=25_000)


class VeterinaryPlaceOut(BaseModel):
    name: str
    lat: float
    lng: float
    distance_meters: int
    address: str | None = None
    osm_url: str


class NearbyVeterinaryCareResponse(BaseModel):
    items: list[VeterinaryPlaceOut] = Field(default_factory=list)
    source: str
    search_url: str
    location_precision: str
    message: str
