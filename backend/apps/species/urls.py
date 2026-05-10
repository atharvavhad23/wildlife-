from django.urls import path

from .views import species_detail, species_list, species_observations, species_photos


urlpatterns = [
    path('', species_list, name='species-list'),
    path('<str:species_id>/', species_detail, name='species-detail'),
    path('<str:species_id>/observations/', species_observations, name='species-observations'),
    path('<str:species_id>/photos/', species_photos, name='species-photos'),
]