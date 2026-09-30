import csv
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from routes.models import BusRoute, BusStop, Operator, RouteStop


class Command(BaseCommand):
    help = "Import Kathmandu Valley transit data from CSV files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing transit data before importing.",
        )

    def handle(self, *args, **options):
        base_dir = Path("data")

        operators_file = base_dir / "operators.csv"
        routes_file = base_dir / "routes.csv"
        stops_file = base_dir / "stops.csv"
        route_stops_file = base_dir / "route_stops.csv"

        files = [
            operators_file,
            routes_file,
            stops_file,
            route_stops_file,
        ]

        for file_path in files:
            if not file_path.exists():
                raise CommandError(f"Required data file not found: {file_path}")

        try:
            with transaction.atomic():
                if options["clear"]:
                    self.clear_data()

                operators = self.import_operators(operators_file)
                stops = self.import_stops(stops_file)
                routes = self.import_routes(routes_file, operators)
                self.import_route_stops(
                    route_stops_file,
                    routes,
                    stops,
                )

        except Exception as exc:
            raise CommandError(f"Import failed: {exc}") from exc

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Transit data imported successfully."))
        self.stdout.write(f"Operators: {Operator.objects.count()}")
        self.stdout.write(f"Stops: {BusStop.objects.count()}")
        self.stdout.write(f"Routes: {BusRoute.objects.count()}")
        self.stdout.write(f"Route stops: {RouteStop.objects.count()}")

    def clear_data(self):
        self.stdout.write(self.style.WARNING("Clearing existing transit data..."))

        RouteStop.objects.all().delete()
        BusRoute.objects.all().delete()
        BusStop.objects.all().delete()
        Operator.objects.all().delete()

    def read_csv(self, file_path):
        with file_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            return list(csv.DictReader(file))

    def import_operators(self, file_path):
        rows = self.read_csv(file_path)
        operators = {}

        for row in rows:
            operator_id = row["operator_id"].strip()
            name = row["name"].strip()

            if not operator_id:
                raise ValueError("Operator ID cannot be empty.")

            if not name:
                raise ValueError(f"Operator name is empty for {operator_id}.")

            operator, _ = Operator.objects.update_or_create(
                name=name,
                defaults={
                    "description": row.get("description", "").strip(),
                },
            )

            operators[operator_id] = operator

        self.stdout.write(f"Imported {len(operators)} operators.")

        return operators

    def import_stops(self, file_path):
        rows = self.read_csv(file_path)
        stops = {}

        for row in rows:
            stop_id = row["stop_id"].strip()
            name = row["name"].strip()

            if not stop_id:
                raise ValueError("Stop ID cannot be empty.")

            if not name:
                raise ValueError(f"Stop name is empty for {stop_id}.")

            latitude = row["latitude"].strip()
            longitude = row["longitude"].strip()

            if not latitude or not longitude:
                raise ValueError(f"Missing coordinates for stop: {stop_id}")

            stop, _ = BusStop.objects.update_or_create(
                name=name,
                defaults={
                    "latitude": Decimal(latitude),
                    "longitude": Decimal(longitude),
                    "location_description": row.get(
                        "location_description",
                        "",
                    ).strip(),
                },
            )

            stops[stop_id] = stop

        self.stdout.write(f"Imported {len(stops)} stops.")

        return stops

    def import_routes(self, file_path, operators):
        rows = self.read_csv(file_path)
        routes = {}

        for row in rows:
            route_id = row["route_id"].strip()
            operator_id = row["operator_id"].strip()
            route_number = row["route_number"].strip()
            name = row["name"].strip()

            if operator_id not in operators:
                raise ValueError(
                    f"Unknown operator '{operator_id}' for route '{route_id}'."
                )

            if not route_id:
                raise ValueError("Route ID cannot be empty.")

            route, _ = BusRoute.objects.update_or_create(
                operator=operators[operator_id],
                route_number=route_number,
                name=name,
                defaults={
                    "is_bidirectional": (
                        row["is_bidirectional"].strip().lower() == "true"
                    ),
                },
            )

            routes[route_id] = route

        self.stdout.write(f"Imported {len(routes)} routes.")

        return routes

    def import_route_stops(
        self,
        file_path,
        routes,
        stops,
    ):
        rows = self.read_csv(file_path)

        imported = 0

        for row in rows:
            route_id = row["route_id"].strip()
            stop_id = row["stop_id"].strip()

            if route_id not in routes:
                raise ValueError(f"Unknown route '{route_id}' in route_stops.csv.")

            if stop_id not in stops:
                raise ValueError(f"Unknown stop '{stop_id}' in route_stops.csv.")

            sequence = int(row["sequence"])

            distance_value = row.get(
                "distance_from_previous",
                "",
            ).strip()

            distance = Decimal(distance_value) if distance_value else None

            RouteStop.objects.update_or_create(
                route=routes[route_id],
                sequence=sequence,
                defaults={
                    "stop": stops[stop_id],
                    "distance_from_previous": distance,
                },
            )

            imported += 1

        self.stdout.write(f"Imported {imported} route-stop records.")
