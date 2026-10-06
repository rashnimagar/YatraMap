import math

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.db import models
from django.db.models import Count
from django.views import View
from django.views.generic import ListView, DetailView

from .models import BusStop, BusRoute, Operator, RouteStop
from .services.network_route_map import create_network_route_map
from .services.route_map import create_route_map, create_full_route_map
from .services.route_search import find_routes
from .services.transit_router import find_shortest_path


def haversine_distance(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """
    Calculate the great-circle distance between two points on Earth in kilometres.

    Earth's approximate radius is 6371.0 km.
    """
    earth_radius_km = 6371.0

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


class RouteSearchView(View):
    """
    Class-based view for route searching, displaying direct and network results,
    and rendering interactive route maps.
    """
    template_name = "routes/route_search.html"

    def get(self, request, *args, **kwargs):
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
            self.template_name,
            context,
        )


class NearbyStopsView(View):
    """
    Return the nearest active bus stops to the supplied coordinates via JSON.

    Expected query parameters:
        lat=<latitude>
        lng=<longitude>

    Returns up to five nearby active bus stops.
    """

    def get(self, request, *args, **kwargs):
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
                    "location_description": stop.location_description,
                }
            )

        nearby.sort(key=lambda stop: stop["distance_km"])

        return JsonResponse(
            {
                "results": nearby[:5],
            }
        )


class OperatorListView(ListView):
    """
    Display a list of all active operators annotated with active route counts.
    """
    model = Operator
    template_name = "routes/operators.html"
    context_object_name = "operators"

    def get_queryset(self):
        return (
            Operator.objects.filter(is_active=True)
            .annotate(
                active_route_count=Count(
                    "routes",
                    filter=models.Q(routes__is_active=True),
                )
            )
            .order_by("name")
        )


class OperatorDetailView(DetailView):
    """
    Display details for a single active operator and its active bus routes.
    """
    model = Operator
    template_name = "routes/operator_detail.html"
    context_object_name = "operator"

    def get_queryset(self):
        return Operator.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["routes"] = (
            BusRoute.objects.filter(
                operator=self.object,
                is_active=True,
            )
            .prefetch_related("route_stops__stop")
            .order_by("route_number", "name")
        )
        return context


class RouteDetailView(DetailView):
    """
    Display the complete details of a single active bus route,
    including every ordered stop and the full route map.
    """
    model = BusRoute
    template_name = "routes/route_detail.html"
    context_object_name = "route"

    def get_queryset(self):
        return BusRoute.objects.select_related("operator").filter(
            is_active=True,
            operator__is_active=True,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        route = self.object

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

        context["route_stops"] = route_stops
        context["map_html"] = map_html
        context["map_script"] = map_script
        return context


# Backward-compatible view callables
route_search = RouteSearchView.as_view()
nearby_stops = NearbyStopsView.as_view()
operators = OperatorListView.as_view()
operator_detail = OperatorDetailView.as_view()
route_detail = RouteDetailView.as_view()
