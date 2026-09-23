from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Operator(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    contact = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class BusStop(models.Model):
    name = models.CharField(max_length=150)
    latitude = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        validators=[
            MinValueValidator(Decimal("-90")),
            MaxValueValidator(Decimal("90")),
        ],
    )
    longitude = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        validators=[
            MinValueValidator(Decimal("-180")),
            MaxValueValidator(Decimal("180")),
        ],
    )
    location_description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional landmark or additional location information.",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class BusRoute(models.Model):
    operator = models.ForeignKey(
        Operator,
        on_delete=models.PROTECT,
        related_name="routes",
    )
    route_number = models.CharField(max_length=30)
    name = models.CharField(
        max_length=200,
        help_text="Example: Lagankhel - Gongabu",
    )
    description = models.TextField(blank=True)

    base_fare = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0")),
        ],
        help_text="Optional base/estimated fare in NPR.",
    )

    is_bidirectional = models.BooleanField(
        default=True,
        help_text="Whether the route can be travelled in both directions.",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["route_number", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["operator", "route_number", "name"],
                name="unique_operator_route",
            )
        ]

    def __str__(self):
        return f"{self.route_number} - {self.name}"


class RouteStop(models.Model):
    route = models.ForeignKey(
        BusRoute,
        on_delete=models.CASCADE,
        related_name="route_stops",
    )
    stop = models.ForeignKey(
        BusStop,
        on_delete=models.PROTECT,
        related_name="route_stops",
    )
    sequence = models.PositiveIntegerField(
        help_text="Order of this stop within the route.",
    )
    distance_from_previous = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0")),
        ],
        help_text="Distance from the previous stop in kilometres.",
    )

    class Meta:
        ordering = ["route", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["route", "sequence"],
                name="unique_route_sequence",
            ),
            models.UniqueConstraint(
                fields=["route", "stop"],
                name="unique_route_stop",
            ),
        ]

    def __str__(self):
        return f"{self.route} - {self.sequence}. {self.stop.name}"