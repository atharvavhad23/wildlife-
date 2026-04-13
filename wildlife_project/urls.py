from django.contrib import admin
from django.urls import path
from predictor import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='home'),
    path('animals/', views.animals_prediction, name='animals'),
    path('birds/', views.birds_prediction, name='birds'),
    path('predict/animals/', views.predict_animals, name='predict_animals'),
    path('predict/birds/', views.predict_birds, name='predict_birds'),
    path('features/animals/', views.get_animals_features, name='animals_features'),
    path('features/birds/', views.get_birds_features, name='birds_features'),
]
