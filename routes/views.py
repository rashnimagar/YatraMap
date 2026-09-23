from django.shortcuts import render

from .models import BusStop
from .services.route_map import create_route_map
from .services.route_search import find_routes


def route_search(request):
    stops = BusStop.objects.filter(is_active=True)

    source_id = request.GET.get("source")
    destination_id = request.GET.get("destination")
    selected_route_id = request.GET.get("route")

    results = []
    source = None
    destination = None
    selected_result = None

    map_header = None
    map_html = None
    map_script = None

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

        except BusStop.DoesNotExist:
            source = None
            destination = None

    context = {
        "stops": stops,
        "source": source,
        "destination": destination,
        "results": results,
        "selected_result": selected_result,
        "map_header": map_header,
        "map_html": map_html,
        "map_script": map_script,
    }

    return render(
        request,
        "routes/route_search.html",
        context,
    )