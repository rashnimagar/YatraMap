import csv
import math
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

STOPS_FILE = BASE_DIR / "stops.csv"
ROUTE_STOPS_FILE = BASE_DIR / "route_stops.csv"


def haversine_distance(
    latitude_1,
    longitude_1,
    latitude_2,
    longitude_2,
):
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


def load_stops():
    stops = {}

    with STOPS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            if not row["latitude"] or not row["longitude"]:
                raise ValueError(f"Missing coordinates for stop: {row['stop_id']}")

            stops[row["stop_id"]] = {
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
            }

    return stops


def calculate_route_distances():
    stops = load_stops()

    with ROUTE_STOPS_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file))
        fieldnames = [
            "route_id",
            "stop_id",
            "sequence",
            "distance_from_previous",
        ]

    previous_route_id = None
    previous_stop = None

    for row in rows:
        route_id = row["route_id"]
        stop_id = row["stop_id"]

        if route_id != previous_route_id:
            row["distance_from_previous"] = ""
            previous_route_id = route_id
            previous_stop = stop_id
            continue

        current_stop = stops[stop_id]
        previous_coordinates = stops[previous_stop]

        distance = haversine_distance(
            previous_coordinates["latitude"],
            previous_coordinates["longitude"],
            current_stop["latitude"],
            current_stop["longitude"],
        )

        row["distance_from_previous"] = f"{distance:.2f}"

        previous_stop = stop_id

    with ROUTE_STOPS_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {len(rows)} route-stop records.")


if __name__ == "__main__":
    calculate_route_distances()
