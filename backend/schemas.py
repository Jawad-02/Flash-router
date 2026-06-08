from __future__ import annotations

from pydantic import BaseModel, Field


class RouteRequest(BaseModel):
    start_lat: float = Field(..., ge=-90, le=90)
    start_lng: float = Field(..., ge=-180, le=180)
    end_lat: float = Field(..., ge=-90, le=90)
    end_lng: float = Field(..., ge=-180, le=180)
    algorithm: str = ''


class RouteResponse(BaseModel):
    path: list[str]
    cost: float
    detail: str = ''
    explored_edges: list[list] = []
    route_path: list[list[float]] = []
    algorithm: str = ''
    computation_ms: float = 0.0
    area_key: str = ''


class TrafficUpdate(BaseModel):
    area_key: str = Field(..., min_length=1)
    edge_from: str = Field(..., min_length=1)
    edge_to: str = Field(..., min_length=1)
    new_weight: float = Field(..., ge=0)


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
