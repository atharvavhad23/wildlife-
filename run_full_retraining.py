"""
run_full_retraining.py
======================
ONE-CLICK script to retrain ALL models from scratch with the v2 pipeline.
Run from the project root: python run_full_retraining.py
"""
import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent
ML   = ROOT / "ml_logic"

steps = [
    ("Step 1/2 — Regression models (Animals, Birds, Insects, Plants)",
     [sys.executable, str(ML / "train_all_models_v2.py")]),
    ("Step 2/2 — Occurrence trend classifiers (balanced labels)",
     [sys.executable, str(ML / "train_occurrence_classifiers_v2.py")]),
]

print("=" * 65)
print("  WILDLIFE SANCTUARY — FULL RETRAINING PIPELINE")
print("=" * 65)

for label, cmd in steps:
    print(f"\n{'─'*65}")
    print(f"  {label}")
    print(f"{'─'*65}")
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"\n  ❌ FAILED: {label}")
        sys.exit(result.returncode)

print("\n" + "=" * 65)
print("  ✅ RETRAINING COMPLETE")
print("  Restart Django server to load new models:")
print("     python manage.py runserver")
print("=" * 65)
