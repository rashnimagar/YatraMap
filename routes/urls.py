from django.urls import path

from .views import route_search


urlpatterns = [
    path("", route_search, name="route_search"),
]