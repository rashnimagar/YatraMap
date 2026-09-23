from dataclasses import dataclass
import heapq
from itertools import count

from routes.models import BusStop, RouteStop


@dataclass
class TransitEdge:
    """
    A directed connection between two consecutive bus stops.
    """

    from_stop: BusStop
    to_stop: BusStop
    route: object
    distance: float


@dataclass
class TransitSegment:
    """
    A continuous journey on a single bus route.
    """

    route: object
    operator: object
    stops: list[BusStop]
    distance: float


@dataclass
class TransitPath:
    """
    A complete journey through the transit network.
    """

    stops: list[BusStop]
    edges: list[TransitEdge]
    total_distance: float
    transfers: int
    routing_cost: float
    segments: list[TransitSegment]


def build_transit_graph() -> dict[int, list[TransitEdge]]:
    """
    Build a directed transit graph from all active routes.

    Each active bus stop is a graph node.

    Consecutive stops on a route become edges. Bidirectional routes
    receive edges in both directions, while one-way routes only receive
    edges in their defined sequence.
    """

    route_stops = list(
        RouteStop.objects.filter(
            route__is_active=True,
            stop__is_active=True,
        )
        .select_related("route", "route__operator", "stop")
        .order_by("route_id", "sequence")
    )

    graph: dict[int, list[TransitEdge]] = {}

    # Group RouteStop records by route.
    routes: dict[int, list[RouteStop]] = {}

    for route_stop in route_stops:
        routes.setdefault(route_stop.route_id, []).append(route_stop)

    for route_stop_list in routes.values():
        if len(route_stop_list) < 2:
            continue

        route = route_stop_list[0].route

        for current, following in zip(
            route_stop_list,
            route_stop_list[1:],
        ):
            distance = float(following.distance_from_previous or 0)

            forward_edge = TransitEdge(
                from_stop=current.stop,
                to_stop=following.stop,
                route=route,
                distance=distance,
            )

            graph.setdefault(current.stop_id, []).append(
                forward_edge
            )

            if route.is_bidirectional:
                reverse_edge = TransitEdge(
                    from_stop=following.stop,
                    to_stop=current.stop,
                    route=route,
                    distance=distance,
                )

                graph.setdefault(following.stop_id, []).append(
                    reverse_edge
                )

    return graph


def find_shortest_path(
    source: BusStop,
    destination: BusStop,
    transfer_penalty: float = 2.0,
) -> TransitPath | None:
    """
    Find the best journey between two bus stops.

    The routing algorithm uses Dijkstra's algorithm with a
    route-aware state.

    Routing cost:

        actual distance + transfer penalty * transfers

    The actual journey distance remains separate from the routing
    cost so the UI can report the real distance accurately.
    """

    if source.id == destination.id:
        return TransitPath(
            stops=[source],
            edges=[],
            total_distance=0.0,
            transfers=0,
            routing_cost=0.0,
            segments=[],
        )

    graph = build_transit_graph()

    if source.id not in graph:
        return None

    # A state is:
    #
    #     (stop_id, current_route_id)
    #
    # The route is part of the state because reaching the same stop
    # while riding different routes can have different future costs.
    #
    # None represents the initial state before boarding a bus.
    source_state = (source.id, None)

    # Best routing cost discovered for each state.
    best_cost: dict[tuple[int, int | None], float] = {
        source_state: 0.0,
    }

    # Actual accumulated distance for each state.
    best_distance: dict[tuple[int, int | None], float] = {
        source_state: 0.0,
    }

    # Number of transfers for each state.
    best_transfers: dict[tuple[int, int | None], int] = {
        source_state: 0,
    }

    # Previous state used to reconstruct the journey.
    previous_state: dict[
        tuple[int, int | None],
        tuple[int, int | None],
    ] = {}

    # Edge used to reach each state.
    previous_edge: dict[
        tuple[int, int | None],
        TransitEdge,
    ] = {}

    # Priority queue:
    #
    # (routing_cost, sequence_number, state)
    #
    # The sequence number gives heapq a deterministic tie-breaker
    # without requiring state objects to be comparable.
    queue = []
    sequence = count()

    heapq.heappush(
        queue,
        (
            0.0,
            next(sequence),
            source_state,
        ),
    )

    destination_state = None

    while queue:
        current_cost, _, current_state = heapq.heappop(queue)

        # Ignore stale queue entries.
        if current_cost > best_cost.get(
            current_state,
            float("inf"),
        ):
            continue

        current_stop_id, current_route_id = current_state

        # We can finish at the destination regardless of which route
        # we are currently using.
        if current_stop_id == destination.id:
            destination_state = current_state
            break

        for edge in graph.get(current_stop_id, []):
            next_route_id = edge.route.id

            # Boarding the first bus is not a transfer.
            is_transfer = (
                current_route_id is not None
                and current_route_id != next_route_id
            )

            transfer_count = (
                best_transfers[current_state]
                + int(is_transfer)
            )

            actual_distance = (
                best_distance[current_state]
                + edge.distance
            )

            routing_cost = (
                actual_distance
                + transfer_count * transfer_penalty
            )

            next_state = (
                edge.to_stop.id,
                next_route_id,
            )

            existing_cost = best_cost.get(next_state)

            if (
                existing_cost is None
                or routing_cost < existing_cost
            ):
                best_cost[next_state] = routing_cost
                best_distance[next_state] = actual_distance
                best_transfers[next_state] = transfer_count

                previous_state[next_state] = current_state
                previous_edge[next_state] = edge

                heapq.heappush(
                    queue,
                    (
                        routing_cost,
                        next(sequence),
                        next_state,
                    ),
                )

    if destination_state is None:
        return None

    # Reconstruct edges from destination back to source.
    edges: list[TransitEdge] = []
    current_state = destination_state

    while current_state != source_state:
        edge = previous_edge.get(current_state)

        if edge is None:
            return None

        edges.append(edge)
        current_state = previous_state[current_state]

    edges.reverse()

    stops = [source]

    for edge in edges:
        stops.append(edge.to_stop)

    return TransitPath(
        stops=stops,
        edges=edges,
        total_distance=round(
            best_distance[destination_state],
            2,
        ),
        transfers=best_transfers[destination_state],
        routing_cost=round(
            best_cost[destination_state],
            2,
        ),
        segments=build_segments(edges),
    )


def count_transfers(edges: list[TransitEdge]) -> int:
    """
    Count how many times the passenger changes bus routes.
    """

    if not edges:
        return 0

    transfers = 0
    previous_route_id = edges[0].route.id

    for edge in edges[1:]:
        if edge.route.id != previous_route_id:
            transfers += 1

        previous_route_id = edge.route.id

    return transfers


def build_segments(edges: list[TransitEdge]) -> list[TransitSegment]:
    """
    Group consecutive edges that belong to the same bus route
    into continuous journey segments.
    """

    if not edges:
        return []

    segments: list[TransitSegment] = []

    current_route = edges[0].route
    current_stops = [
        edges[0].from_stop,
        edges[0].to_stop,
    ]
    current_distance = edges[0].distance

    for edge in edges[1:]:
        if edge.route.id == current_route.id:
            current_stops.append(edge.to_stop)
            current_distance += edge.distance
            continue

        segments.append(
            TransitSegment(
                route=current_route,
                operator=current_route.operator,
                stops=current_stops,
                distance=round(current_distance, 2),
            )
        )

        current_route = edge.route
        current_stops = [
            edge.from_stop,
            edge.to_stop,
        ]
        current_distance = edge.distance

    segments.append(
        TransitSegment(
            route=current_route,
            operator=current_route.operator,
            stops=current_stops,
            distance=round(current_distance, 2),
        )
    )

    return segments