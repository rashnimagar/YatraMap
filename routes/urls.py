from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.route_search,
        name="route_search",
    ),
    path(
        "operators/",
        views.operators,
        name="operators",
    ),
    path(
        "operators/<int:pk>/",
        views.operator_detail,
        name="operator_detail",
    ),
    path(
        "routes/<int:pk>/",
        views.route_detail,
        name="route_detail",
    ),
    path(
        "api/nearby-stops/",
        views.nearby_stops,
        name="nearby_stops",
    ),
]
