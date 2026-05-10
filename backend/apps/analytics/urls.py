from django.urls import path

from .views import alerts_view, cluster_list, dashboard_view


urlpatterns = [
    path('dashboard/', dashboard_view, name='dashboard'),
    path('clusters/', cluster_list, name='clusters'),
    path('alerts/', alerts_view, name='alerts'),
]