#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=== Pulling latest code ==="
git pull

echo "=== Activating venv ==="
source venv/bin/activate

echo "=== Installing dependencies ==="
pip install -q -r requirements.txt

echo "=== Running migrations ==="
cd "$PROJECT_DIR"
PYTHONPATH="$PROJECT_DIR" alembic upgrade head

echo "=== Restarting services ==="
systemctl restart kursach-api || echo "WARNING: kursach-api restart failed"
systemctl restart kursach-worker || echo "WARNING: kursach-worker restart failed"
systemctl restart kursach-bot || echo "WARNING: kursach-bot restart failed"

echo "=== Deploy complete ==="
