"""
Analytics URL routing: clustering, dashboards, and analytics.
"""

from django.urls import path
from predictor.views.analytics_views import (
    get_cluster_heatmap,
    get_cluster_details,
    get_cluster_timeline,
    get_seasonal_activity,
    get_conservation_alerts,
    get_top_observers,
    wildlife_dashboard,
)

urlpatterns = [
    # Generic analytics endpoints (support ?category parameter)
    path('api/cluster-heatmap/', get_cluster_heatmap, name='cluster_heatmap_api'),
    path('api/cluster-details/', get_cluster_details, name='cluster_details_api'),
    path('api/cluster-timeline/', get_cluster_timeline, name='cluster_timeline_api'),
    path('api/seasonal-activity/', get_seasonal_activity, name='seasonal_api'),
    path('api/conservation-alerts/', get_conservation_alerts, name='alerts_api'),
    path('api/top-observers/', get_top_observers, name='observers_api'),
    # Wildlife dashboard
    path('wildlife/dashboard/', wildlife_dashboard, name='wildlife_dashboard'),
]
