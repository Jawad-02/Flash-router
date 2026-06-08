"""One-time script: fetch Mersin road network from Overpass API, save as mersin_graph.json."""

from __future__ import annotations

import json
import math
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
OUTPUT = DATA_DIR / 'mersin_graph.json'
OLD_FILE = DATA_DIR / 'city_graph.json'

# Bounding box for Mersin city (topographic map extent)
SOUTH, WEST, NORTH, EAST = 36.64, 34.47, 36.96, 34.79

OVERPASS_URL = 'https://overpass-api.de/api/interpreter'


def build_query(south: float, west: float, north: float, east: float) -> str:
    return f'''
    [out:json];
    (
      way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)$"]({south},{west},{north},{east});
    );
    out body;
    >;
    out skel qt;
    '''


def fetch_overpass(query: str) -> dict:
    url = f'{OVERPASS_URL}?data={urllib.parse.quote(query)}'
    req = urllib.request.Request(url, headers={'User-Agent': 'FlashRouter/1.0'})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f'HTTP error: {e.code} {e.reason}', file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f'Network error: {e.reason}', file=sys.stderr)
        sys.exit(1)


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_ways(data: dict) -> dict:
    nodes: dict[str, dict[str, float]] = {}
    edges: dict[str, dict[str, float]] = {}
    way_count = 0

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

        way_count += 1
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

    result = {'nodes': nodes, 'edges': edges}
    print(f'Parsed {way_count} ways → {len(nodes)} nodes, {sum(len(v) for v in edges.values())} edges')
    return result


def main() -> None:
    print(f'Fetching Mersin roads (bbox: {SOUTH},{WEST},{NORTH},{EAST})...')
    query = build_query(SOUTH, WEST, NORTH, EAST)
    data = fetch_overpass(query)

    print(f'Overpass returned {len(data.get("elements", []))} elements')
    graph = parse_ways(data)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, 'w') as f:
        json.dump(graph, f, indent=2)

    print(f'Saved to {OUTPUT}')

    if OLD_FILE.exists():
        OLD_FILE.unlink()
        print(f'Deleted old {OLD_FILE}')


if __name__ == '__main__':
    main()
