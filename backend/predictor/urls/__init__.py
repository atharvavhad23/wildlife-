"""
URL routing module initialization.
Combines all modular URL patterns for the predictor app.
"""

from django.urls import path, include

# Import individual URL modules
from . import system_urls, animal_urls, bird_urls, insect_urls, plant_urls, analytics_urls

# Combine all URL patterns
urlpatterns = [
    path('', include(system_urls)),
    path('', include(animal_urls)),
    path('', include(bird_urls)),
    path('', include(insect_urls)),
    path('', include(plant_urls)),
    path('', include(analytics_urls)),
]

__all__ = ['urlpatterns']
