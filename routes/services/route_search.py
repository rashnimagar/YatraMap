from dataclasses import dataclass

from routes.models import BusRoute, BusStop, RouteStop


@dataclass
class RouteSearchResult:
    route: BusRoute
    stops: list[RouteStop]
    total_distance: float


def find_routes(source: BusStop, destination: BusStop) -> list[RouteSearchResult]:
    """
    Find direct bus routes connecting the source and destination stops.

    A route is considered valid when both stops belong to the route.
    For bidirectional routes, either stop order is accepted.
    """

    source_route_stops = RouteStop.objects.filter(
        stop=source,
        stop__is_active=True,
        route__is_active=True,
    ).select_related("route")

    destination_route_stops = RouteStop.objects.filter(
        stop=destination,
        stop__is_active=True,
        route__is_active=True,
    ).select_related("route")

    destination_by_route = {
        item.route_id: item
        for item in destination_route_stops
    }

    results = []

    for source_route_stop in source_route_stops:
        route = source_route_stop.route
        destination_route_stop = destination_by_route.get(route.id)

        if destination_route_stop is None:
            continue

        source_sequence = source_route_stop.sequence
        destination_sequence = destination_route_stop.sequence

        if source_sequence == destination_sequence:
            continue

        if destination_sequence > source_sequence:
            start_sequence = source_sequence
            end_sequence = destination_sequence
        elif route.is_bidirectional:
            start_sequence = destination_sequence
            end_sequence = source_sequence
        else:
            continue

        route_stops = list(
            RouteStop.objects.filter(
                route=route,
                sequence__gte=start_sequence,
                sequence__lte=end_sequence,
            )
            .select_related("stop")
            .order_by("sequence")
        )
        total_distance = calculate_distance(route_stops)

        if destination_sequence < source_sequence:
            route_stops.reverse()

        results.append(
            RouteSearchResult(
                route=route,
                stops=route_stops,
                total_distance=total_distance,
            )
        )

    return results


def calculate_distance(route_stops: list[RouteStop]) -> float:
    """
    Calculate total journey distance between the selected stops.

    The first stop in the selected segment contributes no distance;
    each subsequent stop contributes its distance from the previous stop.
    """

    if len(route_stops) < 2:
        return 0.0

    total = sum(
        float(route_stop.distance_from_previous or 0)
        for route_stop in route_stops[1:]
    )

    return round(total, 2)