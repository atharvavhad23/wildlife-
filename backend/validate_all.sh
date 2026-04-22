#!/bin/bash
# Final Import Validation and Test Script
# Run all checks to ensure the refactored structure works correctly

echo "=========================================="
echo "IMPORT VALIDATION & DJANGO CHECK"
echo "=========================================="

cd /e/miniproject_wildlfie/wildlife-/backend

echo ""
echo "[1] Running Python import validation..."
python validate_imports.py

if [ $? -ne 0 ]; then
    echo "✗ Import validation failed!"
    exit 1
fi

echo ""
echo "[2] Running Django system check..."
python manage.py check

if [ $? -ne 0 ]; then
    echo "✗ Django check failed!"
    exit 1
fi

echo ""
echo "✓ ALL VALIDATIONS PASSED!"
echo "=========================================="
