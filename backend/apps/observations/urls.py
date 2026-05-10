from django.urls import path

from .views import observation_list


urlpatterns = [
    path('', observation_list, name='observation-list'),
]