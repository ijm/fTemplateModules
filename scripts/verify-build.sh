#!/bin/bash
# Build verification script - validates package builds correctly in isolated environment
# Run from repo root: bash scripts/verify-build.sh

set -e

VENV_DIR=".venv-verify"

echo "Building distribution packages..."
python -m build

echo ""
echo "Checking metadata with twine..."
python -m twine check dist/*

echo ""
echo "Verifying package contents..."
unzip -l dist/*.whl | grep -E "(ftemplatemodules/|Name)" | head -20

echo ""
echo "Creating isolated test environment..."
python -m venv --clear "$VENV_DIR"

# Run test in venv
(
    . "$VENV_DIR/bin/activate"
    echo "Testing installation in isolated venv..."
    pip install dist/*.whl --quiet
    python -c "import ftemplatemodules; import ftemplatemodules.auto; print(f'OK: ftemplatemodules installed successfully')"
)

echo ""
echo "Build verification complete."
