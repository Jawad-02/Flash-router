from __future__ import annotations

import heapq
import math
from typing import Any

from graph_loader import haversine_km
from schemas import RouteResponse

MAX_EDGES = 150000


def _thin_list(items: list, max_count: int) -> list:
    n = len(items)
    if n <= max_count:
        return [list(item) for item in items]
    step = (n - 1) / (max_count - 1)
    result = [list(items[round(i * step)]) for i in range(max_count - 1)]
    result.append(list(items[-1]))
    return result


def _build_route_path(nodes: dict, path: list[str]) -> list[list[float]]:
    route_path: list[list[float]] = []
    for nid in path:
        coord = nodes.get(nid)
        if coord:
            route_path.append([coord['lat'], coord['lng']])
    return route_path


def _reconstruct_path(
    previous: dict[str, str],
    start_id: str,
    end_id: str,
) -> list[str]:
    path: list[str] = []
    current: str | None = end_id
    while current is not None:
        path.append(current)
        current = previous.get(current)
    path.reverse()
    return path


class DijkstraEngine:
    def __init__(self, graph: dict[str, Any], _end_coords: tuple[float, float] | None = None) -> None:
        self.graph = graph

    def find_shortest_path(self, start_id: str, end_id: str) -> RouteResponse:
        nodes = self.graph['nodes']
        edges = self.graph['edges']

        if start_id not in nodes:
            raise ValueError(f'Start node "{start_id}" not found in graph')
        if end_id not in nodes:
            raise ValueError(f'End node "{end_id}" not found in graph')

        distances: dict[str, float] = {start_id: 0.0}
        previous: dict[str, str] = {}
        pq: list[tuple[float, str]] = [(0.0, start_id)]
        settled: set[str] = set()
        explored: list = []

        while pq:
            current_dist, current_id = heapq.heappop(pq)
            if current_id in settled:
                continue
            settled.add(current_id)

            if current_id in previous:
                prev_id = previous[current_id]
                w = edges[prev_id][current_id]
                explored.append([
                    nodes[prev_id]['lat'], nodes[prev_id]['lng'],
                    nodes[current_id]['lat'], nodes[current_id]['lng'],
                    prev_id, current_id, w,
                ])

            if current_id == end_id:
                path = _reconstruct_path(previous, start_id, end_id)
                return RouteResponse(
                    path=path, cost=distances[end_id],
                    explored_edges=_thin_list(explored, MAX_EDGES),
                    route_path=_build_route_path(nodes, path),
                )

            for neighbor_id, weight in edges.get(current_id, {}).items():
                if neighbor_id in settled or neighbor_id not in nodes:
                    continue
                new_dist = current_dist + weight
                old = distances.get(neighbor_id, math.inf)
                if new_dist < old:
                    distances[neighbor_id] = new_dist
                    previous[neighbor_id] = current_id
                    heapq.heappush(pq, (new_dist, neighbor_id))

        return RouteResponse(
            path=[], cost=-1.0,
            explored_edges=_thin_list(explored, MAX_EDGES),
        )


class AStarEngine:
    def __init__(self, graph: dict[str, Any], end_coords: tuple[float, float] | None = None) -> None:
        self.graph = graph
        self.end_lat, self.end_lng = end_coords or (0.0, 0.0)

    def find_shortest_path(self, start_id: str, end_id: str) -> RouteResponse:
        nodes = self.graph['nodes']
        edges = self.graph['edges']

        if start_id not in nodes:
            raise ValueError(f'Start node "{start_id}" not found in graph')
        if end_id not in nodes:
            raise ValueError(f'End node "{end_id}" not found in graph')

        g_score: dict[str, float] = {start_id: 0.0}
        previous: dict[str, str] = {}
        end_node = nodes[end_id]

        def heuristic(nid: str) -> float:
            c = nodes[nid]
            return haversine_km(c['lat'], c['lng'], end_node['lat'], end_node['lng'])

        pq: list[tuple[float, str]] = [(heuristic(start_id), start_id)]
        settled: set[str] = set()
        explored: list = []

        while pq:
            _, current_id = heapq.heappop(pq)
            if current_id in settled:
                continue
            settled.add(current_id)

            if current_id in previous:
                prev_id = previous[current_id]
                w = edges[prev_id][current_id]
                explored.append([
                    nodes[prev_id]['lat'], nodes[prev_id]['lng'],
                    nodes[current_id]['lat'], nodes[current_id]['lng'],
                    prev_id, current_id, w,
                ])

            if current_id == end_id:
                path = _reconstruct_path(previous, start_id, end_id)
                return RouteResponse(
                    path=path, cost=g_score[end_id],
                    explored_edges=_thin_list(explored, MAX_EDGES),
                    route_path=_build_route_path(nodes, path),
                )

            for neighbor_id, weight in edges.get(current_id, {}).items():
                if neighbor_id in settled or neighbor_id not in nodes:
                    continue
                tentative_g = g_score[current_id] + weight
                old_g = g_score.get(neighbor_id, math.inf)
                if tentative_g < old_g:
                    g_score[neighbor_id] = tentative_g
                    previous[neighbor_id] = current_id
                    f = tentative_g + heuristic(neighbor_id)
                    heapq.heappush(pq, (f, neighbor_id))

        return RouteResponse(
            path=[], cost=-1.0,
            explored_edges=_thin_list(explored, MAX_EDGES),
        )


class BiDijkstraEngine:
    def __init__(self, graph: dict[str, Any], _end_coords: tuple[float, float] | None = None) -> None:
        self.graph = graph

    def find_shortest_path(self, start_id: str, end_id: str) -> RouteResponse:
        nodes = self.graph['nodes']
        edges = self.graph['edges']

        if start_id not in nodes:
            raise ValueError(f'Start node "{start_id}" not found in graph')
        if end_id not in nodes:
            raise ValueError(f'End node "{end_id}" not found in graph')

        rev_edges: dict[str, dict[str, float]] = {}
        for u, neighbors in edges.items():
            for v, w in neighbors.items():
                rev_edges.setdefault(v, {})[u] = w

        dist_f: dict[str, float] = {start_id: 0.0}
        dist_b: dict[str, float] = {end_id: 0.0}
        prev_f: dict[str, str] = {}
        prev_b: dict[str, str] = {}
        pq_f: list[tuple[float, str]] = [(0.0, start_id)]
        pq_b: list[tuple[float, str]] = [(0.0, end_id)]
        settled_f: set[str] = set()
        settled_b: set[str] = set()
        explored: list = []

        mu = math.inf
        meeting: str | None = None

        def reconstruct() -> RouteResponse:
            assert meeting is not None
            path_f = _reconstruct_path(prev_f, start_id, meeting)
            path_b: list[str] = []
            cur: str | None = prev_b.get(meeting)
            while cur is not None:
                path_b.append(cur)
                cur = prev_b.get(cur)
            path = path_f + [meeting] + path_b
            total = dist_f[meeting] + dist_b[meeting]
            return RouteResponse(
                path=path, cost=total,
                explored_edges=_thin_list(explored, MAX_EDGES),
                route_path=_build_route_path(nodes, path),
            )

        def record_explored(cur: str, pm: dict[str, str]) -> None:
            if cur in pm:
                p = pm[cur]
                w = edges[p][cur]
                explored.append([
                    nodes[p]['lat'], nodes[p]['lng'],
                    nodes[cur]['lat'], nodes[cur]['lng'],
                    p, cur, w,
                ])

        turn_f = True

        while pq_f and pq_b:
            if turn_f:
                if not pq_f:
                    turn_f = False
                    continue
                dc, cur = heapq.heappop(pq_f)
                while dc != dist_f.get(cur, math.inf):
                    if not pq_f:
                        break
                    dc, cur = heapq.heappop(pq_f)
                if cur in settled_f:
                    turn_f = not turn_f
                    continue
                settled_f.add(cur)
                record_explored(cur, prev_f)

                if cur in settled_b:
                    cand = dist_f[cur] + dist_b[cur]
                    if cand < mu:
                        mu = cand
                        meeting = cur
                    if min(pq_f[0][0] if pq_f else math.inf, pq_b[0][0] if pq_b else math.inf) >= mu / 2:
                        return reconstruct()
                    turn_f = not turn_f
                    continue

                for nbr, w in edges.get(cur, {}).items():
                    if nbr in settled_f or nbr not in nodes:
                        continue
                    nd = dist_f[cur] + w
                    if nd < dist_f.get(nbr, math.inf):
                        dist_f[nbr] = nd
                        prev_f[nbr] = cur
                        heapq.heappush(pq_f, (nd, nbr))

                if meeting is not None:
                    top = min(pq_f[0][0] if pq_f else math.inf, pq_b[0][0] if pq_b else math.inf)
                    if top >= mu / 2:
                        return reconstruct()
            else:
                if not pq_b:
                    turn_f = True
                    continue
                dc, cur = heapq.heappop(pq_b)
                while dc != dist_b.get(cur, math.inf):
                    if not pq_b:
                        break
                    dc, cur = heapq.heappop(pq_b)
                if cur in settled_b:
                    turn_f = not turn_f
                    continue
                settled_b.add(cur)
                record_explored(cur, prev_b)

                if cur in settled_f:
                    cand = dist_b[cur] + dist_f[cur]
                    if cand < mu:
                        mu = cand
                        meeting = cur
                    if min(pq_f[0][0] if pq_f else math.inf, pq_b[0][0] if pq_b else math.inf) >= mu / 2:
                        return reconstruct()
                    turn_f = not turn_f
                    continue

                for nbr, w in rev_edges.get(cur, {}).items():
                    if nbr in settled_b or nbr not in nodes:
                        continue
                    nd = dist_b[cur] + w
                    if nd < dist_b.get(nbr, math.inf):
                        dist_b[nbr] = nd
                        prev_b[nbr] = cur
                        heapq.heappush(pq_b, (nd, nbr))

                if meeting is not None:
                    top = min(pq_f[0][0] if pq_f else math.inf, pq_b[0][0] if pq_b else math.inf)
                    if top >= mu / 2:
                        return reconstruct()

            turn_f = not turn_f

        if meeting is not None:
            return reconstruct()
        return RouteResponse(
            path=[], cost=-1.0,
            explored_edges=_thin_list(explored, MAX_EDGES),
        )


class GreedyBestFirstEngine:
    def __init__(self, graph: dict[str, Any], end_coords: tuple[float, float] | None = None) -> None:
        self.graph = graph
        self.end_lat, self.end_lng = end_coords or (0.0, 0.0)

    def find_shortest_path(self, start_id: str, end_id: str) -> RouteResponse:
        nodes = self.graph['nodes']
        edges = self.graph['edges']

        if start_id not in nodes:
            raise ValueError(f'Start node "{start_id}" not found in graph')
        if end_id not in nodes:
            raise ValueError(f'End node "{end_id}" not found in graph')

        previous: dict[str, str] = {}
        end_node = nodes[end_id]

        def heuristic(nid: str) -> float:
            c = nodes[nid]
            return haversine_km(c['lat'], c['lng'], end_node['lat'], end_node['lng'])

        pq: list[tuple[float, str]] = [(heuristic(start_id), start_id)]
        visited: set[str] = set()
        explored: list = []

        while pq:
            _, current_id = heapq.heappop(pq)
            if current_id in visited:
                continue
            visited.add(current_id)

            if current_id in previous:
                prev_id = previous[current_id]
                w = edges[prev_id][current_id]
                explored.append([
                    nodes[prev_id]['lat'], nodes[prev_id]['lng'],
                    nodes[current_id]['lat'], nodes[current_id]['lng'],
                    prev_id, current_id, w,
                ])

            if current_id == end_id:
                path = _reconstruct_path(previous, start_id, end_id)
                cost = sum(
                    edges.get(path[i], {}).get(path[i + 1], 0)
                    for i in range(len(path) - 1)
                )
                return RouteResponse(
                    path=path, cost=round(cost, 4),
                    explored_edges=_thin_list(explored, MAX_EDGES),
                    route_path=_build_route_path(nodes, path),
                )

            for neighbor_id, weight in edges.get(current_id, {}).items():
                if neighbor_id in visited or neighbor_id not in nodes:
                    continue
                previous.setdefault(neighbor_id, current_id)
                heapq.heappush(pq, (heuristic(neighbor_id), neighbor_id))

        return RouteResponse(
            path=[], cost=-1.0,
            explored_edges=_thin_list(explored, MAX_EDGES),
        )


def get_engine(algorithm: str, graph: dict[str, Any], end_coords: tuple[float, float] | None = None) -> DijkstraEngine | AStarEngine | BiDijkstraEngine | GreedyBestFirstEngine:
    match algorithm:
        case 'astar':
            return AStarEngine(graph, end_coords)
        case 'bidirectional':
            return BiDijkstraEngine(graph, end_coords)
        case 'greedy':
            return GreedyBestFirstEngine(graph, end_coords)
        case _:
            return DijkstraEngine(graph, end_coords)
