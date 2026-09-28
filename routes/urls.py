from django.urls import path

from . import views


urlpatterns = [
    path("", views.route_search, name="route_search"),
    path(
        "api/nearby-stops/",
        views.nearby_stops,
        name="nearby_stops",
    ),
]