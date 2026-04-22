# REFACTORED: URL routing has been moved to predictor/urls/ directory.
# All URL patterns are now organized in modular files:
#   - system_urls.py: Authentication & home routes
#   - animal_urls.py: Animal prediction routes
#   - bird_urls.py: Bird prediction routes
#   - insect_urls.py: Insect prediction routes
#   - plant_urls.py: Plant prediction routes
#   - analytics_urls.py: Clustering & analytics routes
#
# This file is kept for compatibility but is no longer used.
# All patterns are combined in predictor/urls/__init__.py
