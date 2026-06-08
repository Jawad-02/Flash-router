from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from httpx import AsyncClient

import math

from algorithms import get_engine
from graph_loader import (
    OverpassError,
    get_or_fetch_corridor,
    graph_cache,
    haversine_km,
    load_static_graph,
    nearest_node,
)
from schemas import ContactRequest, RouteRequest, RouteResponse, TrafficUpdate

load_dotenv()

app = FastAPI(title='Flash Router')

STATIC_DIR = Path(__file__).resolve().parent.parent / 'static'
MERSIN_GRAPH = Path(__file__).resolve().parent.parent / 'data' / 'mersin_graph.json'
MERSIN_AREA_KEY = 'area_36.64_34.47_36.96_34.79'
MAX_DISTANCE_KM = 50.0


@app.on_event('startup')
def startup() -> None:
    if MERSIN_GRAPH.exists():
        load_static_graph(MERSIN_GRAPH, MERSIN_AREA_KEY)


@app.post('/api/route', response_model=RouteResponse)
def compute_route(req: RouteRequest) -> RouteResponse:
    start_coord = (req.start_lat, req.start_lng)
    end_coord = (req.end_lat, req.end_lng)

    distance_km = haversine_km(*start_coord, *end_coord)
    if distance_km > MAX_DISTANCE_KM:
        raise HTTPException(
            status_code=400,
            detail=f'Distance {distance_km:.1f} km exceeds maximum of {MAX_DISTANCE_KM} km',
        )

    margin = 0.01
    area_key = (
        f'area_'
        f'{math.floor((min(req.start_lat, req.end_lat) - margin) * 100) / 100:.2f}_'
        f'{math.floor((min(req.start_lng, req.end_lng) - margin) * 100) / 100:.2f}_'
        f'{math.ceil((max(req.start_lat, req.end_lat) + margin) * 100) / 100:.2f}_'
        f'{math.ceil((max(req.start_lng, req.end_lng) + margin) * 100) / 100:.2f}'
    )

    try:
        graph = get_or_fetch_corridor(req.start_lat, req.start_lng, req.end_lat, req.end_lng)
    except OverpassError as e:
        raise HTTPException(status_code=502, detail=str(e))

    start_id = nearest_node(req.start_lat, req.start_lng, graph['nodes'])
    end_id = nearest_node(req.end_lat, req.end_lng, graph['nodes'])

    algorithm = req.algorithm or 'dijkstra'
    engine = get_engine(algorithm, graph, (req.end_lat, req.end_lng))

    t0 = time.perf_counter()
    try:
        result = engine.find_shortest_path(start_id, end_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result.computation_ms = round((time.perf_counter() - t0) * 1000, 2)
    result.algorithm = algorithm
    result.area_key = area_key

    if result.cost < 0:
        result.detail = 'No road connection found between these points'

    return result


RESEND_API_KEY = os.getenv('RESEND_API_KEY', '')
MAIL_FROM_ADDRESS = os.getenv('MAIL_FROM_ADDRESS', 'no-reply@jawadmerwah.dev')


@app.post('/api/contact')
async def handle_contact(req: ContactRequest) -> dict:
    if not RESEND_API_KEY or 'placeholder' in RESEND_API_KEY:
        return {'status': 'ok', 'detail': 'Message received (email not configured)'}
    async with AsyncClient() as client:
        resp = await client.post(
            'https://api.resend.com/emails',
            headers={
                'Authorization': f'Bearer {RESEND_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'from': f'Flash <{MAIL_FROM_ADDRESS}>',
                'to': ['me@jawadmerwah.dev'],
                'subject': f'Flash Contact: {req.name}',
                'text': f'Message from {req.name} via the Flash router app ({req.email}):\n\n{req.message}',
            },
        )
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail='Failed to send email')
    return {'status': 'ok'}


@app.post('/api/traffic')
def update_traffic(update: TrafficUpdate) -> dict:
    cache_entry = graph_cache.get(update.area_key)
    if cache_entry is None:
        raise HTTPException(status_code=404, detail=f'Area "{update.area_key}" not in cache')
    edges = cache_entry['edges']
    original_edges = cache_entry.get('original_edges', {})
    from_id = update.edge_from
    to_id = update.edge_to
    if from_id not in edges or to_id not in edges[from_id]:
        raise HTTPException(status_code=404, detail='Edge not found in graph')
    if update.new_weight == 0 and from_id in original_edges and to_id in original_edges[from_id]:
        orig = original_edges[from_id][to_id]
        edges[from_id][to_id] = orig
        edges.setdefault(to_id, {})[from_id] = orig
    else:
        edges[from_id][to_id] = update.new_weight
        edges.setdefault(to_id, {})[from_id] = update.new_weight
    return {'status': 'ok'}


if STATIC_DIR.is_dir():
    app.mount('/', StaticFiles(directory=str(STATIC_DIR), html=True), name='static')
