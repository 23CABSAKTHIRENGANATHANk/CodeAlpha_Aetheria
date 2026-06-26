import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "socialmedia.settings")
import django
import sys
# Ensure the inner `socialmedia` package (where manage.py lives) is on sys.path
sys.path.insert(0, str(ROOT / 'socialmedia'))
django.setup()

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

User = get_user_model()

def ensure_superuser(username='admin', email='admin@example.com', password='adminpass'):
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        print('Created superuser', username)
    else:
        print('Superuser already exists')

def test_storage():
    content = ContentFile(b'hello from local smoke test')
    name = default_storage.save('test_uploads/hello.txt', content)
    try:
        url = default_storage.url(name)
    except Exception:
        url = name
    print('Saved test file:', name, ' URL:', url)

if __name__ == '__main__':
    ensure_superuser()
    test_storage()
