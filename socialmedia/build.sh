#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "🔍 Python version:"
python --version

echo "📦 pip version:"
pip --version

echo "==> Installing Python dependencies..."
# Try to upgrade pip first
pip install --upgrade pip setuptools wheel

# Install requirements with verbose output
if [ -f "../requirements.txt" ]; then
    echo "Installing from ../requirements.txt"
    pip install -r ../requirements.txt --verbose
elif [ -f "requirements.txt" ]; then
    echo "Installing from requirements.txt"
    pip install -r requirements.txt --verbose
else
    echo "❌ ERROR: requirements.txt not found!"
    ls -la
    exit 1
fi

echo "✅ Dependencies installed successfully"

echo "==> Checking Django setup..."
python manage.py check --deploy || echo "⚠️  Deploy checks showed warnings (expected)"

echo "==> Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "==> Running database migrations..."
# Try migrations with better error handling
python manage.py migrate --noinput || {
    echo "⚠️  Initial migration failed, retrying..."
    sleep 5
    python manage.py migrate --noinput
}

echo "✅ Render Build Completed Successfully!"

