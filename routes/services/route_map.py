import folium
from django.conf import settings
from folium.features import DivIcon

from .route_search import RouteSearchResult


# CARTO now requires a free API key for their basemap tiles.
_CARTO_API_KEY = getattr(settings, "CARTO_API_KEY", "")

_CARTO_VOYAGER_URL = (
    "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
)

if _CARTO_API_KEY:
    _CARTO_VOYAGER_URL += f"?key={_CARTO_API_KEY}"


_CARTO_ATTR = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">'
    "OpenStreetMap</a> contributors "
    '&copy; <a href="https://carto.com/attributions">CARTO</a>'
)


def create_route_map(result: RouteSearchResult):
    """
    Create a Folium map for a selected bus route result.
    """

    stops = result.stops

    if not stops:
        return None

    first_stop = stops[0].stop

    route_map = folium.Map(
        location=[
            float(first_stop.latitude),
            float(first_stop.longitude),
        ],
        zoom_start=14,
        control_scale=True,
        width="100%",
        height="600px",
        tiles=None,
    )

    folium.TileLayer(
        tiles=_CARTO_VOYAGER_URL,
        attr=_CARTO_ATTR,
        name="Voyager",
        subdomains="abcd",
        max_zoom=20,
    ).add_to(route_map)

    # Marker styling
    route_map.get_root().html.add_child(
        folium.Element(
            """
            <style>
                .yatra-stop-marker {
                    width: 34px;
                    height: 34px;
                    border-radius: 50%;
                    color: #ffffff;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-family: Arial, sans-serif;
                    font-size: 13px;
                    font-weight: 700;
                    border: 3px solid #ffffff;
                    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.30);
                }

                .yatra-stop-marker.start {
                    background: #65a30d;
                }

                .yatra-stop-marker.middle {
                    background: #0284c7;
                }

                .yatra-stop-marker.end {
                    background: #dc2626;
                }
            </style>
            """
        )
    )

    coordinates = []

    for index, route_stop in enumerate(stops):
        stop = route_stop.stop

        latitude = float(stop.latitude)
        longitude = float(stop.longitude)

        coordinates.append([latitude, longitude])

        # Determine marker type.
        if index == 0:
            marker_class = "start"
            marker_label = "Origin"
        elif index == len(stops) - 1:
            marker_class = "end"
            marker_label = "Destination"
        else:
            marker_class = "middle"
            marker_label = "Bus Stop"

        # Human-readable stop number.
        stop_number = index + 1

        folium.Marker(
            location=[latitude, longitude],
            popup=folium.Popup(
                f"<strong>{stop.name}</strong><br>"
                f"{marker_label}<br>"
                f"Stop {stop_number} of {len(stops)}",
                max_width=250,
            ),
            tooltip=stop.name,
            icon=DivIcon(
                html=(
                    f'<div class="yatra-stop-marker {marker_class}">{stop_number}</div>'
                ),
                icon_size=(34, 34),
                icon_anchor=(17, 17),
            ),
        ).add_to(route_map)

    # Draw the route between the stops.
    folium.PolyLine(
        locations=coordinates,
        weight=5,
        opacity=0.8,
        tooltip=result.route.name,
    ).add_to(route_map)

    # Automatically fit the map around the complete route.
    route_map.fit_bounds(coordinates)

    return route_map


def create_full_route_map(route):
    """
    Create a Folium map showing the complete bus route.

    Unlike create_route_map(), this function receives a BusRoute
    directly and displays every active stop belonging to that route,
    ordered by RouteStop.sequence.

    This is used by the public route-detail page.
    """

    route_stops = list(
        route.route_stops.filter(stop__is_active=True)
        .select_related("stop")
        .order_by("sequence")
    )

    if not route_stops:
        return None

    coordinates = [
        (
            float(route_stop.stop.latitude),
            float(route_stop.stop.longitude),
        )
        for route_stop in route_stops
    ]

    route_map = folium.Map(
        location=coordinates[0],
        zoom_start=13,
        width="100%",
        height="600px",
        control_scale=True,
    )

    # Use the same CARTO Voyager map tiles as the existing
    # route-search map.
    folium.TileLayer(
        tiles=_CARTO_VOYAGER_URL,
        attr=(
            '&copy; <a href="https://www.openstreetmap.org/copyright">'
            "OpenStreetMap</a> contributors "
            '&copy; <a href="https://carto.com/attributions">'
            "CARTO</a>"
        ),
        name="CARTO Voyager",
        overlay=False,
        control=True,
    ).add_to(route_map)

    total_stops = len(route_stops)

    # Add every stop as a numbered marker.
    for index, route_stop in enumerate(route_stops, start=1):
        stop = route_stop.stop

        latitude = float(stop.latitude)
        longitude = float(stop.longitude)

        if index == 1:
            marker_color = "#16a34a"
            marker_label = "Origin"
        elif index == total_stops:
            marker_color = "#dc2626"
            marker_label = "Destination"
        else:
            marker_color = "#2563eb"
            marker_label = f"Stop {index}"

        icon = folium.DivIcon(
            html=f"""
            <div style="
                background:{marker_color};
                color:white;
                width:30px;
                height:30px;
                border-radius:50% 50% 50% 0;
                transform:rotate(-45deg);
                display:flex;
                align-items:center;
                justify-content:center;
                border:3px solid white;
                box-shadow:0 2px 6px rgba(0,0,0,.3);
                font-weight:700;
                font-size:12px;
            ">
                <span style="transform:rotate(45deg);">
                    {index}
                </span>
            </div>
            """,
            icon_size=(30, 30),
            icon_anchor=(15, 30),
        )

        popup_html = f"""
        <div style="min-width:180px;">
            <strong>{stop.name}</strong>
            <br>
            <span>{marker_label}</span>
            <br>
            <small>Route stop {route_stop.sequence}</small>
        </div>
        """

        folium.Marker(
            location=[latitude, longitude],
            icon=icon,
            tooltip=stop.name,
            popup=folium.Popup(
                popup_html,
                max_width=300,
            ),
        ).add_to(route_map)

    # Draw the COMPLETE route from the first stop to the last stop.
    folium.PolyLine(
        locations=coordinates,
        color="#16a34a",
        weight=5,
        opacity=0.85,
    ).add_to(route_map)

    # Automatically fit the map to the entire route.
    if len(coordinates) > 1:
        route_map.fit_bounds(coordinates)

    return route_map
