from dataclasses import dataclass

from routes.models import BusRoute, BusStop, RouteStop


@dataclass
class RouteSearchResult:
    route: BusRoute
    stops: list[RouteStop]
    total_distance: float
    estimated_minutes: int


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

    destination_by_route = {item.route_id: item for item in destination_route_stops}

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
        estimated_minutes = calculate_estimated_minutes(
            total_distance,
        )

        if destination_sequence < source_sequence:
            route_stops.reverse()

        results.append(
            RouteSearchResult(
                route=route,
                stops=route_stops,
                total_distance=total_distance,
                estimated_minutes=estimated_minutes,
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
        float(route_stop.distance_from_previous or 0) for route_stop in route_stops[1:]
    )

    return round(total, 2)


# Planning estimate only.
# This is not live traffic or timetable data.
AVERAGE_BUS_SPEED_KMH = 18.0
TRANSFER_TIME_MINUTES = 5


def calculate_estimated_minutes(
    distance_km: float,
    transfers: int = 0,
) -> int:
    """
    Estimate journey time from distance and transfers.

    The estimate is intentionally approximate because YatraMap
    does not currently have live traffic, timetable, or GPS data.

    Distance time is based on the configured average bus speed.
    Each transfer adds a fixed transfer allowance.
    """

    if distance_km <= 0:
        return 0

    travel_minutes = (distance_km / AVERAGE_BUS_SPEED_KMH) * 60

    transfer_minutes = transfers * TRANSFER_TIME_MINUTES

    return max(
        1,
        round(travel_minutes + transfer_minutes),
    )
