from django.contrib import admin
from django.urls import path
from predictor import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='home'),
    path('animals/', views.animals_prediction, name='animals'),
    path('birds/', views.birds_prediction, name='birds'),
    path('predict/animals/', views.predict_animals, name='predict_animals'),
    path('predict/animals/result/', views.animals_result, name='animals_result'),
    path('dashboard/animals/', views.animals_dashboard, name='animals_dashboard'),
    path('predict/birds/', views.predict_birds, name='predict_birds'),
    path('predict/birds/result/', views.birds_result, name='birds_result'),
    path('dashboard/birds/', views.birds_dashboard, name='birds_dashboard'),
    path('features/animals/', views.get_animals_features, name='animals_features'),
    path('features/birds/', views.get_birds_features, name='birds_features'),
]
