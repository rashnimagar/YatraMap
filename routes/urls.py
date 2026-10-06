from django.urls import path

from .views import (
    NearbyStopsView,
    OperatorDetailView,
    OperatorListView,
    RouteDetailView,
    RouteSearchView,
)


urlpatterns = [
    path(
        "",
        RouteSearchView.as_view(),
        name="route_search",
    ),
    path(
        "operators/",
        OperatorListView.as_view(),
        name="operators",
    ),
    path(
        "operators/<int:pk>/",
        OperatorDetailView.as_view(),
        name="operator_detail",
    ),
    path(
        "routes/<int:pk>/",
        RouteDetailView.as_view(),
        name="route_detail",
    ),
    path(
        "api/nearby-stops/",
        NearbyStopsView.as_view(),
        name="nearby_stops",
    ),
]
