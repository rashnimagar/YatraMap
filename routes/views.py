import math

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.db import models
from django.db.models import Count

from .models import BusStop, BusRoute, Operator, RouteStop
from .services.network_route_map import create_network_route_map
from .services.route_map import create_route_map, create_full_route_map
from .services.route_search import find_routes
from .services.transit_router import find_shortest_path


def route_search(request):
    stops = BusStop.objects.filter(is_active=True)

    source_id = request.GET.get("source")
    destination_id = request.GET.get("destination")
    selected_route_id = request.GET.get("route")

    results = []
    network_result = None
    source = None
    destination = None
    selected_result = None

    map_header = None
    map_html = None
    map_script = None

    network_map_header = None
    network_map_html = None
    network_map_script = None

    if source_id and destination_id:
        try:
            source = BusStop.objects.get(
                id=source_id,
                is_active=True,
            )

            destination = BusStop.objects.get(
                id=destination_id,
                is_active=True,
            )

            results = find_routes(source, destination)

            network_result = find_shortest_path(
                source,
                destination,
            )

            # If the user selected a specific route,
            # find that route among the valid search results.
            if selected_route_id:
                try:
                    selected_route_id = int(selected_route_id)
                except (TypeError, ValueError):
                    selected_route_id = None

                if selected_route_id is not None:
                    selected_result = next(
                        (
                            result
                            for result in results
                            if result.route.id == selected_route_id
                        ),
                        None,
                    )

            # On the initial search, display the first available route.
            if selected_result is None and results:
                selected_result = results[0]

            if selected_result:
                route_map = create_route_map(selected_result)

                # Render Folium components separately for Django.
                route_map.get_root().render()

                map_header = route_map.get_root().header.render()
                map_html = route_map.get_root().html.render()
                map_script = route_map.get_root().script.render()

            if (
                network_result
                and network_result.segments
                and network_result.transfers > 0
            ):
                network_map = create_network_route_map(network_result)
                network_map.get_root().render()

                network_map_header = network_map.get_root().header.render()
                network_map_html = network_map.get_root().html.render()
                network_map_script = network_map.get_root().script.render()

        except BusStop.DoesNotExist:
            source = None
            destination = None

    context = {
        "stops": stops,
        "source": source,
        "destination": destination,
        "results": results,
        "network_result": network_result,
        "selected_result": selected_result,
        "map_header": map_header,
        "map_html": map_html,
        "map_script": map_script,
        "network_map_header": network_map_header,
        "network_map_html": network_map_html,
        "network_map_script": network_map_script,
    }

    return render(
        request,
        "routes/route_search.html",
        context,
    )


def nearby_stops(request):
    """
    Return the nearest active bus stops to the supplied coordinates.

    Expected query parameters:
        lat=<latitude>
        lng=<longitude>

    Example:
        /api/nearby-stops/?lat=27.673&lng=85.324

    Returns up to five nearby active bus stops.
    """

    latitude = request.GET.get("lat")
    longitude = request.GET.get("lng")

    if latitude is None or longitude is None:
        return JsonResponse(
            {
                "error": "Latitude and longitude are required.",
            },
            status=400,
        )

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return JsonResponse(
            {
                "error": "Latitude and longitude must be valid numbers.",
            },
            status=400,
        )

    if not -90 <= latitude <= 90:
        return JsonResponse(
            {
                "error": "Latitude must be between -90 and 90.",
            },
            status=400,
        )

    if not -180 <= longitude <= 180:
        return JsonResponse(
            {
                "error": "Longitude must be between -180 and 180.",
            },
            status=400,
        )

    # Earth's approximate radius in kilometres.
    earth_radius_km = 6371.0

    def haversine_distance(
        latitude_1,
        longitude_1,
        latitude_2,
        longitude_2,
    ):
        latitude_difference = math.radians(latitude_2 - latitude_1)

        longitude_difference = math.radians(longitude_2 - longitude_1)

        first_latitude = math.radians(latitude_1)
        second_latitude = math.radians(latitude_2)

        a = (
            math.sin(latitude_difference / 2) ** 2
            + math.cos(first_latitude)
            * math.cos(second_latitude)
            * math.sin(longitude_difference / 2) ** 2
        )

        c = 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a),
        )

        return earth_radius_km * c

    nearby = []

    stops = BusStop.objects.filter(
        is_active=True,
    )

    for stop in stops:
        distance = haversine_distance(
            latitude,
            longitude,
            float(stop.latitude),
            float(stop.longitude),
        )

        nearby.append(
            {
                "id": stop.id,
                "name": stop.name,
                "latitude": float(stop.latitude),
                "longitude": float(stop.longitude),
                "distance_km": round(distance, 2),
                "location_description": (stop.location_description),
            }
        )

    nearby.sort(key=lambda stop: stop["distance_km"])

    return JsonResponse(
        {
            "results": nearby[:5],
        }
    )


def operators(request):
    operator_list = (
        Operator.objects.filter(is_active=True)
        .annotate(
            active_route_count=Count(
                "routes",
                filter=models.Q(routes__is_active=True),
            )
        )
        .order_by("name")
    )

    return render(
        request,
        "routes/operators.html",
        {
            "operators": operator_list,
        },
    )


def operator_detail(request, pk):
    operator = get_object_or_404(
        Operator,
        pk=pk,
        is_active=True,
    )

    routes = (
        BusRoute.objects.filter(
            operator=operator,
            is_active=True,
        )
        .prefetch_related(
            "route_stops__stop",
        )
        .order_by("route_number", "name")
    )

    return render(
        request,
        "routes/operator_detail.html",
        {
            "operator": operator,
            "routes": routes,
        },
    )


def route_detail(request, pk):
    """
    Display the complete details of a single active bus route,
    including every ordered stop and the full route map.
    """

    route = get_object_or_404(
        BusRoute.objects.select_related("operator"),
        pk=pk,
        is_active=True,
        operator__is_active=True,
    )

    route_stops = list(
        RouteStop.objects.filter(
            route=route,
            stop__is_active=True,
        )
        .select_related("stop")
        .order_by("sequence")
    )

    route_map = create_full_route_map(route)

    map_html = ""
    map_script = ""

    if route_map is not None:
        rendered_map = route_map.get_root().render()

        if "<script" in rendered_map:
            map_html, script_content = rendered_map.split(
                "<script",
                1,
            )
            map_script = "<script" + script_content
        else:
            map_html = rendered_map

    return render(
        request,
        "routes/route_detail.html",
        {
            "route": route,
            "route_stops": route_stops,
            "map_html": map_html,
            "map_script": map_script,
        },
    )
