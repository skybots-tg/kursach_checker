#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=== Pulling latest code ==="
git fetch origin
git reset --hard origin/main

echo "=== Activating venv ==="
source venv/bin/activate

echo "=== Installing dependencies ==="
pip install -q -r requirements.txt

echo "=== Running migrations ==="
cd "$PROJECT_DIR"
PYTHONPATH="$PROJECT_DIR" alembic upgrade head

echo "=== Restarting services ==="
systemctl restart kursach_checker-api || echo "WARNING: kursach_checker-api restart failed"
systemctl restart kursach_checker-worker || echo "WARNING: kursach_checker-worker restart failed"
systemctl restart kursach_checker-bot || echo "WARNING: kursach_checker-bot restart failed"

echo "=== Deploy complete ==="
