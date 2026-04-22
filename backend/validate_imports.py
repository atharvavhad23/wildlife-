#!/usr/bin/env python3
"""
Import validation script for the refactored Django predictor app.
Checks all critical imports to ensure no broken references after refactoring.
"""

import sys
import traceback

print("=" * 80)
print("IMPORT VALIDATION CHECK - Refactored Django Predictor App")
print("=" * 80)

checks = []

# Test 1: Constants imports
print("\n[1/8] Checking constants imports...")
try:
    from predictor.constants import (
        BASE_ANIMALS_FEATURES,
        BASE_BIRDS_FEATURES,
        BASE_INSECTS_FEATURES,
        BASE_PLANTS_FEATURES,
        OTP_TTL_SECONDS,
        DEFAULT_N_CLUSTERS,
    )
    print("✓ Constants module imports OK")
    checks.append(True)
except Exception as e:
    print(f"✗ Constants import FAILED: {e}")
    traceback.print_exc()
    checks.append(False)

# Test 2: Services imports
print("\n[2/8] Checking services imports...")
try:
    from predictor.services import (
        predict_animals,
        predict_birds,
        extract_feature_importance,
        model_display_name,
        safe_text,
        paginate_results,
        ModelLoader,
    )
    print("✓ Services module imports OK")
    checks.append(True)
except Exception as e:
    print(f"✗ Services import FAILED: {e}")
    traceback.print_exc()
    checks.append(False)

# Test 3: Schemas imports
print("\n[3/8] Checking schemas imports...")
try:
    from predictor.schemas import (
        PredictionRequestSchema,
        ApiResponse,
    )
    print("✓ Schemas module imports OK")
    checks.append(True)
except Exception as e:
    print(f"✗ Schemas import FAILED: {e}")
    traceback.print_exc()
    checks.append(False)

# Test 4: System views imports
print("\n[4/8] Checking system_views imports...")
try:
    from predictor.views.system_views import (
        send_email_otp,
        verify_email_otp,
        index,
        photo_proxy,
    )
    print("✓ System views imports OK")
    checks.append(True)
except Exception as e:
    print(f"✗ System views import FAILED: {e}")
    traceback.print_exc()
    checks.append(False)

# Test 5: Animal views imports
print("\n[5/8] Checking animal_views imports...")
try:
    from predictor.views.animal_views import (
        animals_prediction,
        predict_animals_api,
        get_animals_features,
        get_animals_clustering,
    )
    print("✓ Animal views imports OK")
    checks.append(True)
except Exception as e:
    print(f"✗ Animal views import FAILED: {e}")
    traceback.print_exc()
    checks.append(False)

# Test 6: Analytics views imports
print("\n[6/8] Checking analytics_views imports...")
try:
    from predictor.views.analytics_views import (
        perform_clustering_api,
        get_cluster_heatmap,
        wildlife_dashboard,
    )
    print("✓ Analytics views imports OK")
    checks.append(True)
except Exception as e:
    print(f"✗ Analytics views import FAILED: {e}")
    traceback.print_exc()
    checks.append(False)

# Test 7: URLs package imports
print("\n[7/8] Checking URLs package imports...")
try:
    from predictor.urls import urlpatterns
    assert urlpatterns is not None
    print(f"✓ URLs package imports OK ({len(urlpatterns)} patterns)")
    checks.append(True)
except Exception as e:
    print(f"✗ URLs import FAILED: {e}")
    traceback.print_exc()
    checks.append(False)

# Test 8: Views package imports
print("\n[8/8] Checking views package imports...")
try:
    from predictor.views import (
        animals_prediction,
        birds_prediction,
        insects_prediction,
        predict_animals_api,
        predict_birds_api,
        predict_insects_api,
        predict_plants_api,
    )
    print("✓ Views package imports OK")
    checks.append(True)
except Exception as e:
    print(f"✗ Views package import FAILED: {e}")
    traceback.print_exc()
    checks.append(False)

print("\n" + "=" * 80)
print(f"SUMMARY: {sum(checks)}/{len(checks)} checks passed")
print("=" * 80)

if all(checks):
    print("\n✓ ALL IMPORTS VALIDATED SUCCESSFULLY!")
    sys.exit(0)
else:
    print("\n✗ SOME IMPORTS FAILED - See details above")
    sys.exit(1)
