import os
import sys
from pathlib import Path

# Add the socialmedia Django project to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "socialmedia"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "socialmedia.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
app = application
