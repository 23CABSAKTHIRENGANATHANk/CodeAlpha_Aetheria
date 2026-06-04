"""
WSGI config for socialmedia project.
"""

import os
import sys
from pathlib import Path

# Add the socialmedia directory to the Python path so Django can find modules
# This is needed when running from Vercel's serverless environment
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "socialmedia.settings")

application = get_wsgi_application()
app = application
