import folium
from django.conf import settings

from .transit_router import TransitPath


_CARTO_VOYAGER_URL = (
    "https://{s}.basemaps.cartocdn.com/"
    "rastertiles/voyager/{z}/{x}/{y}{r}.png"
)

_CARTO_ATTRIBUTION = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">'
    "OpenStreetMap</a> contributors &copy; "
    '<a href="https://carto.com/attributions">CARTO</a>'
)

_SEGMENT_COLORS = [
    "#2563eb",
    "#7c3aed",
    "#059669",
    "#ea580c",
    "#db2777",
    "#0891b2",
]


def _get_carto_tiles_url() -> str:
    """
    Return the CARTO Voyager tile URL.

    The API key is added using CARTO's expected `key=` query
    parameter when one is configured in Django settings.
    """

    api_key = getattr(settings, "CARTO_API_KEY", "").strip()

    if api_key:
        return f"{_CARTO_VOYAGER_URL}?key={api_key}"

    return _CARTO_VOYAGER_URL


def create_network_route_map(network_result: TransitPath) -> folium.Map:
    """
    Create a Folium map for a complete network journey.

    Each transit segment is drawn separately so transfers between
    different bus routes are visually distinguishable.

    The function accepts any TransitPath produced by the transit
    router and does not depend on hard-coded routes or stops.
    """

    stops = network_result.stops

    if not stops:
        raise ValueError("Network journey must contain at least one stop.")

    coordinates = [
        (float(stop.latitude), float(stop.longitude))
        for stop in stops
    ]

    center_latitude, center_longitude = coordinates[0]

    route_map = folium.Map(
        location=[center_latitude, center_longitude],
        zoom_start=13,
        control_scale=True,
        tiles=None,
    )

    # Use the same CARTO Voyager configuration as the direct
    # route map, including the API key when configured.
    folium.TileLayer(
        tiles=_get_carto_tiles_url(),
        attr=_CARTO_ATTRIBUTION,
        name="Street Map",
        overlay=False,
        control=True,
    ).add_to(route_map)

    # -------------------------------------------------------------
    # DRAW JOURNEY SEGMENTS
    # -------------------------------------------------------------

    for segment_index, segment in enumerate(network_result.segments):
        segment_coordinates = [
            (float(stop.latitude), float(stop.longitude))
            for stop in segment.stops
        ]

        if len(segment_coordinates) < 2:
            continue

        color = _SEGMENT_COLORS[
            segment_index % len(_SEGMENT_COLORS)
        ]

        folium.PolyLine(
            locations=segment_coordinates,
            color=color,
            weight=6,
            opacity=0.9,
            tooltip=(
                f"Route {segment.route.route_number} — "
                f"{segment.route.name}"
            ),
        ).add_to(route_map)

    # -------------------------------------------------------------
    # MARK JOURNEY STOPS
    # -------------------------------------------------------------

    marked_stop_ids = set()

    for index, stop in enumerate(stops):
        if stop.id in marked_stop_ids:
            continue

        marked_stop_ids.add(stop.id)

        latitude = float(stop.latitude)
        longitude = float(stop.longitude)

        is_start = index == 0
        is_destination = index == len(stops) - 1

        if is_start:
            background_color = "#16a34a"
            label = "S"
            popup_title = "Starting stop"

        elif is_destination:
            background_color = "#dc2626"
            label = "D"
            popup_title = "Destination stop"

        else:
            background_color = "#2563eb"
            label = str(index + 1)
            popup_title = "Journey stop"

        icon = folium.DivIcon(
            html=f"""
                <div style="
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    background: {background_color};
                    color: white;
                    border: 3px solid white;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: 700;
                    font-size: 12px;
                    font-family: Arial, sans-serif;
                ">
                    {label}
                </div>
            """
        )

        folium.Marker(
            location=[latitude, longitude],
            popup=folium.Popup(
                f"<strong>{popup_title}</strong><br>{stop.name}",
                max_width=250,
            ),
            tooltip=stop.name,
            icon=icon,
        ).add_to(route_map)

    # -------------------------------------------------------------
    # MARK TRANSFER POINTS
    # -------------------------------------------------------------

    transfer_stop_ids = _get_transfer_stop_ids(network_result)

    for transfer_stop in stops:
        if transfer_stop.id not in transfer_stop_ids:
            continue

        latitude = float(transfer_stop.latitude)
        longitude = float(transfer_stop.longitude)

        transfer_icon = folium.DivIcon(
            html="""
                <div style="
                    width: 24px;
                    height: 24px;
                    border-radius: 50%;
                    background: #f59e0b;
                    color: white;
                    border: 3px solid white;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.30);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: 800;
                    font-size: 13px;
                    font-family: Arial, sans-serif;
                ">
                    T
                </div>
            """
        )

        folium.Marker(
            location=[latitude, longitude],
            popup=folium.Popup(
                f"<strong>Transfer point</strong><br>"
                f"Change bus at {transfer_stop.name}",
                max_width=250,
            ),
            tooltip=f"Transfer: {transfer_stop.name}",
            icon=transfer_icon,
        ).add_to(route_map)

    # -------------------------------------------------------------
    # FIT MAP TO COMPLETE JOURNEY
    # -------------------------------------------------------------

    if len(coordinates) == 1:
        route_map.location = coordinates[0]
        route_map.zoom_start = 15
    else:
        route_map.fit_bounds(
            coordinates,
            padding=(30, 30),
        )

    _add_network_legend(route_map, network_result)

    return route_map


def _get_transfer_stop_ids(
    network_result: TransitPath,
) -> set[int]:
    """
    Return the stop IDs where the journey changes bus routes.

    A transfer occurs between two consecutive edges when their
    route IDs differ.
    """

    transfer_stop_ids: set[int] = set()

    edges = network_result.edges

    if len(edges) < 2:
        return transfer_stop_ids

    for previous_edge, current_edge in zip(edges, edges[1:]):
        if previous_edge.route.id != current_edge.route.id:
            transfer_stop_ids.add(current_edge.from_stop.id)

    return transfer_stop_ids

def _add_network_legend(
    route_map: folium.Map,
    network_result: TransitPath,
) -> None:
    """
    Add a dynamic legend describing the routes and markers
    used by the network journey map.
    """

    legend_rows = []

    for segment_index, segment in enumerate(network_result.segments):
        color = _SEGMENT_COLORS[
            segment_index % len(_SEGMENT_COLORS)
        ]

        legend_rows.append(
            f"""
            <div style="
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 7px;
            ">
                <span style="
                    display: inline-block;
                    width: 28px;
                    height: 5px;
                    border-radius: 999px;
                    background: {color};
                    flex-shrink: 0;
                "></span>

                <span>
                    <strong>
                        Route {segment.route.route_number}
                    </strong>
                    — {segment.route.name}
                </span>
            </div>
            """
        )

    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 28px;
        left: 28px;
        z-index: 9999;
        background: rgba(255, 255, 255, 0.96);
        padding: 14px 16px;
        border-radius: 10px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.20);
        font-family: Arial, sans-serif;
        font-size: 12px;
        line-height: 1.4;
        min-width: 230px;
        max-width: 320px;
    ">

        <div style="
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 10px;
            color: #111827;
        ">
            Network Journey
        </div>

        {''.join(legend_rows)}

        <div style="
            border-top: 1px solid #e5e7eb;
            margin: 10px 0;
        "></div>

        <div style="
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        ">
            <span style="
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: #16a34a;
                color: white;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
                font-size: 10px;
            ">
                S
            </span>

            <span>Starting stop</span>
        </div>

        <div style="
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        ">
            <span style="
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: #dc2626;
                color: white;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
                font-size: 10px;
            ">
                D
            </span>

            <span>Destination</span>
        </div>

        <div style="
            display: flex;
            align-items: center;
            gap: 8px;
        ">
            <span style="
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: #f59e0b;
                color: white;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                font-weight: 800;
                font-size: 10px;
            ">
                T
            </span>

            <span>Transfer point</span>
        </div>

    </div>
    """

    route_map.get_root().html.add_child(
        folium.Element(legend_html)
    )