from django.contrib import admin

from .models import BusRoute, BusStop, Operator, RouteStop


@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ("name", "contact", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "contact")
    ordering = ("name",)


@admin.register(BusStop)
class BusStopAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "latitude",
        "longitude",
        "location_description",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "location_description")
    ordering = ("name",)


class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 1
    ordering = ("sequence",)
    autocomplete_fields = ("stop",)


@admin.register(BusRoute)
class BusRouteAdmin(admin.ModelAdmin):
    list_display = (
        "route_number",
        "name",
        "operator",
        "base_fare",
        "is_bidirectional",
        "is_active",
    )
    list_filter = (
        "operator",
        "is_bidirectional",
        "is_active",
    )
    search_fields = (
        "route_number",
        "name",
        "operator__name",
    )
    autocomplete_fields = ("operator",)
    inlines = (RouteStopInline,)
    ordering = ("route_number", "name")


@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    list_display = (
        "route",
        "sequence",
        "stop",
        "distance_from_previous",
    )
    list_filter = ("route",)
    search_fields = (
        "route__name",
        "route__route_number",
        "stop__name",
    )
    autocomplete_fields = ("route", "stop")
    ordering = ("route", "sequence")