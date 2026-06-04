#!/bin/bash
set -e
echo "BUILD START"

cd socialmedia

echo "==> Installing dependencies..."
pip install --break-system-packages -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "BUILD END"
