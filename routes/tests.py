from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import BusRoute, BusStop, Operator, RouteStop
from .services.route_search import find_routes

from routes.services.transit_router import (
    build_transit_graph,
    find_shortest_path,
)

class RouteSearchTests(TestCase):

    def setUp(self):
        self.operator = Operator.objects.create(
            name="Sajha Yatayat",
        )

        self.other_operator = Operator.objects.create(
            name="Test Transport",
        )

        self.lagankhel = BusStop.objects.create(
            name="Lagankhel",
            latitude=Decimal("27.6650"),
            longitude=Decimal("85.3240"),
        )

        self.jawalakhel = BusStop.objects.create(
            name="Jawalakhel",
            latitude=Decimal("27.6710"),
            longitude=Decimal("85.3180"),
        )

        self.pulchowk = BusStop.objects.create(
            name="Pulchowk",
            latitude=Decimal("27.6770"),
            longitude=Decimal("85.3180"),
        )

        self.kupandol = BusStop.objects.create(
            name="Kupandol",
            latitude=Decimal("27.6850"),
            longitude=Decimal("85.3190"),
        )

        self.tripureshwor = BusStop.objects.create(
            name="Tripureshwor",
            latitude=Decimal("27.6940"),
            longitude=Decimal("85.3160"),
        )

        self.route = BusRoute.objects.create(
            operator=self.operator,
            route_number="01",
            name="Lagankhel - Tripureshwor",
            base_fare=Decimal("20.00"),
            is_bidirectional=True,
        )

        self.create_route_stops(
            self.route,
            [
                (self.lagankhel, "0.00"),
                (self.jawalakhel, "1.20"),
                (self.pulchowk, "1.10"),
                (self.kupandol, "1.30"),
                (self.tripureshwor, "1.80"),
            ],
        )

    def create_route_stops(self, route, stops):
        for sequence, (stop, distance) in enumerate(stops, start=1):
            RouteStop.objects.create(
                route=route,
                stop=stop,
                sequence=sequence,
                distance_from_previous=Decimal(distance),
            )

    def test_finds_forward_route(self):
        results = find_routes(
            self.lagankhel,
            self.tripureshwor,
        )

        self.assertEqual(len(results), 1)

        result = results[0]

        self.assertEqual(result.route, self.route)

        self.assertEqual(
            [item.stop for item in result.stops],
            [
                self.lagankhel,
                self.jawalakhel,
                self.pulchowk,
                self.kupandol,
                self.tripureshwor,
            ],
        )

        self.assertEqual(result.total_distance, 5.4)

    def test_finds_partial_route(self):
        results = find_routes(
            self.jawalakhel,
            self.kupandol,
        )

        self.assertEqual(len(results), 1)

        result = results[0]

        self.assertEqual(
            [item.stop for item in result.stops],
            [
                self.jawalakhel,
                self.pulchowk,
                self.kupandol,
            ],
        )

        self.assertEqual(result.total_distance, 2.4)

    def test_finds_reverse_route(self):
        results = find_routes(
            self.tripureshwor,
            self.lagankhel,
        )

        self.assertEqual(len(results), 1)

        result = results[0]

        self.assertEqual(
            [item.stop for item in result.stops],
            [
                self.tripureshwor,
                self.kupandol,
                self.pulchowk,
                self.jawalakhel,
                self.lagankhel,
            ],
        )

        self.assertEqual(result.total_distance, 5.4)

    def test_no_route_when_destination_is_not_on_route(self):
        outside_stop = BusStop.objects.create(
            name="Outside Stop",
            latitude=Decimal("27.7000"),
            longitude=Decimal("85.3000"),
        )

        results = find_routes(
            self.lagankhel,
            outside_stop,
        )

        self.assertEqual(results, [])

    def test_same_source_and_destination_returns_no_route(self):
        results = find_routes(
            self.lagankhel,
            self.lagankhel,
        )

        self.assertEqual(results, [])

    def test_inactive_route_is_ignored(self):
        self.route.is_active = False
        self.route.save()

        results = find_routes(
            self.lagankhel,
            self.tripureshwor,
        )

        self.assertEqual(results, [])

    def test_inactive_source_stop_is_ignored(self):
        self.lagankhel.is_active = False
        self.lagankhel.save()

        results = find_routes(
            self.lagankhel,
            self.tripureshwor,
        )

        self.assertEqual(results, [])

    def test_inactive_destination_stop_is_ignored(self):
        self.tripureshwor.is_active = False
        self.tripureshwor.save()

        results = find_routes(
            self.lagankhel,
            self.tripureshwor,
        )

        self.assertEqual(results, [])

    def test_one_way_route_does_not_allow_reverse_travel(self):
        self.route.is_bidirectional = False
        self.route.save()

        results = find_routes(
            self.tripureshwor,
            self.lagankhel,
        )

        self.assertEqual(results, [])

    def test_one_way_route_allows_forward_travel(self):
        self.route.is_bidirectional = False
        self.route.save()

        results = find_routes(
            self.lagankhel,
            self.tripureshwor,
        )

        self.assertEqual(len(results), 1)

        result = results[0]

        self.assertEqual(result.total_distance, 5.4)

    def test_multiple_routes_are_returned(self):
        second_route = BusRoute.objects.create(
            operator=self.other_operator,
            route_number="02",
            name="Lagankhel - Tripureshwor Express",
            base_fare=Decimal("25.00"),
            is_bidirectional=True,
        )

        self.create_route_stops(
            second_route,
            [
                (self.lagankhel, "0.00"),
                (self.pulchowk, "2.00"),
                (self.tripureshwor, "2.50"),
            ],
        )

        results = find_routes(
            self.lagankhel,
            self.tripureshwor,
        )

        self.assertEqual(len(results), 2)

        route_ids = {result.route.id for result in results}

        self.assertEqual(
            route_ids,
            {
                self.route.id,
                second_route.id,
            },
        )

    def test_route_stops_are_returned_in_travel_order(self):
        results = find_routes(
            self.tripureshwor,
            self.jawalakhel,
        )

        self.assertEqual(len(results), 1)

        result = results[0]

        self.assertEqual(
            [item.sequence for item in result.stops],
            [5, 4, 3, 2],
        )

    def test_missing_distance_does_not_crash(self):
        route_stop = RouteStop.objects.get(
            route=self.route,
            stop=self.pulchowk,
        )

        route_stop.distance_from_previous = None
        route_stop.save()

        results = find_routes(
            self.lagankhel,
            self.tripureshwor,
        )

        self.assertEqual(len(results), 1)

        self.assertEqual(
            results[0].total_distance,
            4.3,
        )

class RouteSearchViewTests(TestCase):
    def setUp(self):
        self.operator = Operator.objects.create(
            name="Test Operator",
        )

        self.stop_a = BusStop.objects.create(
            name="Stop A",
            latitude=27.6700,
            longitude=85.3200,
        )

        self.stop_b = BusStop.objects.create(
            name="Stop B",
            latitude=27.6750,
            longitude=85.3250,
        )

        self.stop_c = BusStop.objects.create(
            name="Stop C",
            latitude=27.6800,
            longitude=85.3300,
        )

        self.route_1 = BusRoute.objects.create(
            operator=self.operator,
            route_number="R1",
            name="Route One",
            base_fare=20,
            is_bidirectional=True,
        )

        self.route_2 = BusRoute.objects.create(
            operator=self.operator,
            route_number="R2",
            name="Route Two",
            base_fare=25,
            is_bidirectional=True,
        )

        RouteStop.objects.create(
            route=self.route_1,
            stop=self.stop_a,
            sequence=1,
            distance_from_previous=0,
        )
        RouteStop.objects.create(
            route=self.route_1,
            stop=self.stop_b,
            sequence=2,
            distance_from_previous=2,
        )

        RouteStop.objects.create(
            route=self.route_2,
            stop=self.stop_a,
            sequence=1,
            distance_from_previous=0,
        )
        RouteStop.objects.create(
            route=self.route_2,
            stop=self.stop_b,
            sequence=2,
            distance_from_previous=3,
        )

    def test_initial_search_selects_first_route(self):
        response = self.client.get(
            reverse("route_search"),
            {
                "source": self.stop_a.id,
                "destination": self.stop_b.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["selected_result"])
        self.assertEqual(
            response.context["selected_result"].route.id,
            self.route_1.id,
        )

    def test_valid_route_parameter_selects_requested_route(self):
        response = self.client.get(
            reverse("route_search"),
            {
                "source": self.stop_a.id,
                "destination": self.stop_b.id,
                "route": self.route_2.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["selected_result"])
        self.assertEqual(
            response.context["selected_result"].route.id,
            self.route_2.id,
        )

    def test_invalid_route_parameter_is_handled_safely(self):
        response = self.client.get(
            reverse("route_search"),
            {
                "source": self.stop_a.id,
                "destination": self.stop_b.id,
                "route": "999999",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["selected_result"])

    def test_non_numeric_route_parameter_is_handled_safely(self):
        response = self.client.get(
            reverse("route_search"),
            {
                "source": self.stop_a.id,
                "destination": self.stop_b.id,
                "route": "not-a-number",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["selected_result"])

    def test_selected_route_belongs_to_search_results(self):
        response = self.client.get(
            reverse("route_search"),
            {
                "source": self.stop_a.id,
                "destination": self.stop_b.id,
                "route": self.route_2.id,
            },
        )

        selected_result = response.context["selected_result"]
        results = response.context["results"]

        result_route_ids = {
            result.route.id
            for result in results
        }

        self.assertIn(
            selected_result.route.id,
            result_route_ids,
        )
        self.assertEqual(
            selected_result.route.id,
            self.route_2.id,
        )

class TransitRouterTests(TestCase):
    def setUp(self):
        self.operator_a = Operator.objects.create(
            name="Operator A",
        )

        self.operator_b = Operator.objects.create(
            name="Operator B",
        )

        self.godawari = BusStop.objects.create(
            name="Godawari",
            latitude=27.59,
            longitude=85.32,
        )

        self.satdobato = BusStop.objects.create(
            name="Satdobato",
            latitude=27.65,
            longitude=85.32,
        )

        self.lagankhel = BusStop.objects.create(
            name="Lagankhel",
            latitude=27.67,
            longitude=85.32,
        )

        self.bhaktapur = BusStop.objects.create(
            name="Bhaktapur",
            latitude=27.67,
            longitude=85.43,
        )

        self.durbar_square = BusStop.objects.create(
            name="Bhaktapur Durbar Square",
            latitude=27.67,
            longitude=85.43,
        )

    def create_route(
        self,
        operator,
        route_number,
        name,
        stops,
        bidirectional=True,
    ):
        route = BusRoute.objects.create(
            operator=operator,
            route_number=route_number,
            name=name,
            is_bidirectional=bidirectional,
        )

        for sequence, (stop, distance) in enumerate(stops, start=1):
            RouteStop.objects.create(
                route=route,
                stop=stop,
                sequence=sequence,
                distance_from_previous=distance,
            )

        return route

    def test_graph_contains_route_connections(self):
        self.create_route(
            self.operator_a,
            "A",
            "Godawari - Satdobato",
            [
                (self.godawari, 0),
                (self.satdobato, 4),
            ],
        )

        graph = build_transit_graph()

        self.assertIn(self.godawari.id, graph)

        edges = graph[self.godawari.id]

        self.assertEqual(len(edges), 1)
        self.assertEqual(
            edges[0].to_stop,
            self.satdobato,
        )
        self.assertEqual(
            edges[0].distance,
            4.0,
        )

    def test_bidirectional_route_creates_reverse_connection(self):
        self.create_route(
            self.operator_a,
            "A",
            "Godawari - Satdobato",
            [
                (self.godawari, 0),
                (self.satdobato, 4),
            ],
        )

        graph = build_transit_graph()

        satdobato_edges = graph[self.satdobato.id]

        self.assertEqual(len(satdobato_edges), 1)
        self.assertEqual(
            satdobato_edges[0].to_stop,
            self.godawari,
        )

    def test_one_way_route_does_not_create_reverse_connection(self):
        self.create_route(
            self.operator_a,
            "A",
            "Godawari - Satdobato",
            [
                (self.godawari, 0),
                (self.satdobato, 4),
            ],
            bidirectional=False,
        )

        graph = build_transit_graph()

        self.assertNotIn(
            self.satdobato.id,
            graph,
        )

    def test_routes_join_at_shared_stop(self):
        self.create_route(
            self.operator_a,
            "A",
            "Godawari - Satdobato",
            [
                (self.godawari, 0),
                (self.satdobato, 4),
            ],
        )

        self.create_route(
            self.operator_b,
            "B",
            "Satdobato - Bhaktapur",
            [
                (self.satdobato, 0),
                (self.bhaktapur, 6),
            ],
        )

        path = find_shortest_path(
            self.godawari,
            self.bhaktapur,
        )

        self.assertIsNotNone(path)

        self.assertEqual(
            path.stops,
            [
                self.godawari,
                self.satdobato,
                self.bhaktapur,
            ],
        )

        self.assertEqual(
            path.total_distance,
            10.0,
        )

        self.assertEqual(
            path.transfers,
            1,
        )

    def test_shortest_path_prefers_shorter_distance(self):
        # Short route:
        #
        # Godawari -> Satdobato -> Bhaktapur
        #
        # Total = 10 km

        self.create_route(
            self.operator_a,
            "A",
            "Godawari - Satdobato",
            [
                (self.godawari, 0),
                (self.satdobato, 4),
            ],
        )

        self.create_route(
            self.operator_b,
            "B",
            "Satdobato - Bhaktapur",
            [
                (self.satdobato, 0),
                (self.bhaktapur, 6),
            ],
        )

        # Longer alternative:
        #
        # Godawari -> Lagankhel -> Bhaktapur
        #
        # Total = 15 km

        self.create_route(
            self.operator_a,
            "C",
            "Godawari - Lagankhel",
            [
                (self.godawari, 0),
                (self.lagankhel, 7),
            ],
        )

        self.create_route(
            self.operator_b,
            "D",
            "Lagankhel - Bhaktapur",
            [
                (self.lagankhel, 0),
                (self.bhaktapur, 8),
            ],
        )

        path = find_shortest_path(
            self.godawari,
            self.bhaktapur,
        )

        self.assertIsNotNone(path)

        self.assertEqual(
            path.stops,
            [
                self.godawari,
                self.satdobato,
                self.bhaktapur,
            ],
        )

        self.assertEqual(
            path.total_distance,
            10.0,
        )

    def test_no_path_returns_none(self):
        isolated_stop = BusStop.objects.create(
            name="Isolated Stop",
            latitude=27.70,
            longitude=85.30,
        )

        path = find_shortest_path(
            self.godawari,
            isolated_stop,
        )

        self.assertIsNone(path)

    def test_inactive_route_is_ignored(self):
        route = self.create_route(
            self.operator_a,
            "A",
            "Godawari - Satdobato",
            [
                (self.godawari, 0),
                (self.satdobato, 4),
            ],
        )

        route.is_active = False
        route.save()

        path = find_shortest_path(
            self.godawari,
            self.satdobato,
        )

        self.assertIsNone(path)

    def test_inactive_stop_is_ignored(self):
        self.satdobato.is_active = False
        self.satdobato.save()

        self.create_route(
            self.operator_a,
            "A",
            "Godawari - Satdobato",
            [
                (self.godawari, 0),
                (self.satdobato, 4),
            ],
        )

        path = find_shortest_path(
            self.godawari,
            self.satdobato,
        )

        self.assertIsNone(path)

    def test_same_source_and_destination(self):
        path = find_shortest_path(
            self.godawari,
            self.godawari,
        )

        self.assertIsNotNone(path)

        self.assertEqual(
            path.stops,
            [self.godawari],
        )

        self.assertEqual(
            path.total_distance,
            0.0,
        )

        self.assertEqual(
            path.transfers,
            0,
        )

    def test_routing_cost_can_prefer_fewer_transfers(self):
        # Journey A:
        #
        # Godawari -> Satdobato -> Lagankhel -> Bhaktapur
        #
        # Distance = 10 km
        # Transfers = 2
        #
        # Cost with penalty 3 = 16

        self.create_route(
            self.operator_a,
            "A",
            "Godawari - Satdobato",
            [
                (self.godawari, 0),
                (self.satdobato, 4),
            ],
        )

        self.create_route(
            self.operator_b,
            "B",
            "Satdobato - Lagankhel",
            [
                (self.satdobato, 0),
                (self.lagankhel, 3),
            ],
        )

        self.create_route(
            self.operator_a,
            "C",
            "Lagankhel - Bhaktapur",
            [
                (self.lagankhel, 0),
                (self.bhaktapur, 3),
            ],
        )

        # Journey B:
        #
        # Godawari -> Bhaktapur
        #
        # Distance = 11 km
        # Transfers = 1
        #
        # Cost with penalty 3 = 14

        self.create_route(
            self.operator_a,
            "D",
            "Godawari - Bhaktapur",
            [
                (self.godawari, 0),
                (self.bhaktapur, 11),
            ],
        )

        path = find_shortest_path(
            self.godawari,
            self.bhaktapur,
            transfer_penalty=3.0,
        )

        self.assertIsNotNone(path)

        self.assertEqual(
            path.stops,
            [
                self.godawari,
                self.bhaktapur,
            ],
        )

        self.assertEqual(
            path.total_distance,
            11.0,
        )

        self.assertEqual(
            path.transfers,
            0,
        )

        self.assertEqual(
            path.routing_cost,
            11.0,
        )

    def test_fewer_transfers_can_beat_shorter_distance(self):
        # Shorter journey:
        # Godawari -> Satdobato -> Lagankhel -> Bhaktapur
        # 10 km, 2 transfers
        # Cost = 16 with penalty 3.

        self.create_route(
            self.operator_a,
            "A",
            "Godawari - Satdobato",
            [
                (self.godawari, 0),
                (self.satdobato, 4),
            ],
        )

        self.create_route(
            self.operator_b,
            "B",
            "Satdobato - Lagankhel",
            [
                (self.satdobato, 0),
                (self.lagankhel, 3),
            ],
        )

        self.create_route(
            self.operator_a,
            "C",
            "Lagankhel - Bhaktapur",
            [
                (self.lagankhel, 0),
                (self.bhaktapur, 3),
            ],
        )

        # Longer journey:
        # Godawari -> another shared route -> Bhaktapur
        # 11 km, 1 transfer
        # Cost = 14 with penalty 3.

        intermediate = BusStop.objects.create(
            name="Intermediate",
            latitude=27.68,
            longitude=85.35,
        )

        self.create_route(
            self.operator_b,
            "D",
            "Godawari - Intermediate",
            [
                (self.godawari, 0),
                (intermediate, 5),
            ],
        )

        self.create_route(
            self.operator_b,
            "E",
            "Intermediate - Bhaktapur",
            [
                (intermediate, 0),
                (self.bhaktapur, 6),
            ],
        )

        path = find_shortest_path(
            self.godawari,
            self.bhaktapur,
            transfer_penalty=3.0,
        )

        self.assertIsNotNone(path)

        self.assertEqual(
            path.stops,
            [
                self.godawari,
                intermediate,
                self.bhaktapur,
            ],
        )

        self.assertEqual(
            path.total_distance,
            11.0,
        )

        self.assertEqual(
            path.transfers,
            1,
        )

        self.assertEqual(
            path.routing_cost,
            14.0,
        )