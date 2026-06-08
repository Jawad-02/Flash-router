from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

graph_cache: dict[str, dict] = {}


class GraphLoadError(Exception):
    ...


class OverpassError(Exception):
    ...


def load_static_graph(path: str | Path, area_key: str) -> None:
    graph_path = Path(path)

    if not graph_path.exists():
        raise GraphLoadError(f'Graph file not found: {graph_path}')

    with open(graph_path) as f:
        data = json.load(f)

    if 'nodes' not in data or 'edges' not in data:
        raise GraphLoadError('Graph must contain "nodes" and "edges" keys')

    graph_cache[area_key] = data


def build_overpass_query(
    south: float, west: float, north: float, east: float,
) -> str:
    return f'''
    [out:json];
    (
      way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)$"]({south},{west},{north},{east});
    );
    out body;
    >;
    out skel qt;
    '''


def fetch_overpass_bbox(
    south: float, west: float, north: float, east: float,
) -> dict:
    query = build_overpass_query(south, west, north, east)
    url = f'https://overpass-api.de/api/interpreter?data={urllib.parse.quote(query)}'
    req = urllib.request.Request(url, headers={'User-Agent': 'FlashRouter/1.0'})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise OverpassError(f'Overpass HTTP {e.code}: {e.reason}')
    except urllib.error.URLError as e:
        raise OverpassError(f'Overpass network error: {e.reason}')


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_overpass_response(data: dict) -> dict:
    nodes: dict[str, dict[str, float]] = {}
    edges: dict[str, dict[str, float]] = {}

    for element in data.get('elements', []):
        if element.get('type') != 'node':
            continue
        nid = str(element['id'])
        nodes[nid] = {'lat': float(element['lat']), 'lng': float(element['lon'])}

    for element in data.get('elements', []):
        if element.get('type') != 'way':
            continue

        refs = element.get('nodes', [])
        if len(refs) < 2:
            continue

        prev_id: str | None = None

        for ref in refs:
            node_id = str(ref)
            if node_id not in nodes:
                continue

            if prev_id is not None:
                a = nodes[prev_id]
                b = nodes[node_id]
                dist = round(haversine_km(a['lat'], a['lng'], b['lat'], b['lng']), 4)

                if dist > 0:
                    edges.setdefault(prev_id, {})[node_id] = dist
                    edges.setdefault(node_id, {})[prev_id] = dist

            prev_id = node_id

    return {'nodes': nodes, 'edges': dict(edges), 'original_edges': {k: dict(v) for k, v in edges.items()}}


def area_key_from_bbox(
    south: float, west: float, north: float, east: float,
) -> str:
    return f'area_{south:.2f}_{west:.2f}_{north:.2f}_{east:.2f}'


def _parse_bbox_from_key(key: str) -> tuple[float, float, float, float] | None:
    parts = key.split('_')
    if len(parts) != 5 or parts[0] != 'area':
        return None
    try:
        return float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
    except ValueError:
        return None


def get_or_fetch_corridor(
    start_lat: float, start_lng: float, end_lat: float, end_lng: float,
) -> dict:
    margin = 0.01
    south = math.floor((min(start_lat, end_lat) - margin) * 100) / 100
    west = math.floor((min(start_lng, end_lng) - margin) * 100) / 100
    north = math.ceil((max(start_lat, end_lat) + margin) * 100) / 100
    east = math.ceil((max(start_lng, end_lng) + margin) * 100) / 100
    key = area_key_from_bbox(south, west, north, east)

    if key in graph_cache:
        return graph_cache[key]

    for cache_key, graph in graph_cache.items():
        cached = _parse_bbox_from_key(cache_key)
        if cached and cached[0] <= south and cached[1] <= west and cached[2] >= north and cached[3] >= east:
            graph_cache[key] = graph
            return graph

    raw = fetch_overpass_bbox(south, west, north, east)
    graph = parse_overpass_response(raw)

    if not graph['nodes']:
        raise OverpassError(
            'No roads found in this area. Try clicking closer to a city.'
        )

    graph_cache[key] = graph
    return graph


def nearest_node(lat: float, lng: float, nodes: dict) -> str:
    best_id: str | None = None
    best_dist = math.inf

    for nid, coord in nodes.items():
        d = (lat - coord['lat']) ** 2 + (lng - coord['lng']) ** 2
        if d < best_dist:
            best_dist = d
            best_id = nid

    return best_id
