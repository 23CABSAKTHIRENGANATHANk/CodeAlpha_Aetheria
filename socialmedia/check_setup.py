"""
Quick verification of Phase 1 implementations
Run from socialmedia directory: python manage.py shell < check_setup.py
"""

import os
from pathlib import Path

print("\n" + "="*70)
print("  AETHERIA PHASE 1 IMPLEMENTATION VERIFICATION")
print("="*70)

# Check 1: Base directory
base_dir = Path(__file__).resolve().parent
print(f"\n✓ Working directory: {base_dir}")

# Check 2: Static files
static_dir = base_dir / 'static'
js_dir = static_dir / 'js'

print(f"\nStatic Files:")
print(f"  ✓ Static directory exists: {static_dir.exists()}")
print(f"  ✓ JS directory exists: {js_dir.exists()}")

websocket_js = js_dir / 'websocket-client.js'
firebase_js = js_dir / 'firebase-notifications.js'

print(f"  {'✓' if websocket_js.exists() else '✗'} websocket-client.js: {websocket_js.exists()}")
print(f"  {'✓' if firebase_js.exists() else '✗'} firebase-notifications.js: {firebase_js.exists()}")

# Check 3: CSS
css_file = static_dir / 'css' / 'main.css'
if css_file.exists():
    css_content = css_file.read_text()
    has_indicator = 'connection-status-indicator' in css_content
    has_toast = 'notification-toast-container' in css_content
    print(f"\nCSS Styles:")
    print(f"  {'✓' if has_indicator else '✗'} Connection indicator styles: {has_indicator}")
    print(f"  {'✓' if has_toast else '✗'} Toast notification styles: {has_toast}")

# Check 4: Templates
template_dir = base_dir / 'templates'
base_html = template_dir / 'base.html'

print(f"\nTemplates:")
print(f"  ✓ Templates directory: {template_dir.exists()}")
print(f"  ✓ base.html exists: {base_html.exists()}")

if base_html.exists():
    content = base_html.read_text()
    has_ws = 'websocket-client.js' in content
    has_fb = 'firebase-notifications.js' in content
    has_toast = 'notification-toast-container' in content
    has_indicator = 'connection-status-indicator' in content
    
    print(f"  {'✓' if has_ws else '✗'} WebSocket script included: {has_ws}")
    print(f"  {'✓' if has_fb else '✗'} Firebase script included: {has_fb}")
    print(f"  {'✓' if has_toast else '✗'} Toast container: {has_toast}")
    print(f"  {'✓' if has_indicator else '✗'} Connection indicator: {has_indicator}")

# Check 5: Django Settings
print(f"\nDjango Settings:")

from django.conf import settings

has_logging = hasattr(settings, 'LOGGING')
print(f"  {'✓' if has_logging else '✗'} LOGGING configured: {has_logging}")

if has_logging:
    logging_config = settings.LOGGING
    handlers = logging_config.get('handlers', {})
    print(f"    - Total handlers: {len(handlers)}")
    for handler in handlers:
        print(f"      ✓ {handler}")

db_engine = settings.DATABASES['default'].get('ENGINE', '')
is_pg = 'postgresql' in db_engine
is_sqlite = 'sqlite' in db_engine
print(f"  ✓ Database engine: {db_engine}")
if is_sqlite:
    print(f"    ⚠  WARNING: SQLite is for development only!")

channels = hasattr(settings, 'CHANNEL_LAYERS')
print(f"  {'✓' if channels else '✗'} Django Channels configured: {channels}")

# Check 6: Android Files
print(f"\nAndroid Configuration:")

android_dir = base_dir.parent.parent / 'android'
if android_dir.exists():
    manifest = android_dir / 'app' / 'src' / 'main' / 'AndroidManifest.xml'
    activity = android_dir / 'app' / 'src' / 'main' / 'java' / 'com' / 'aetheria' / 'app' / 'MainActivity.java'
    channels_java = android_dir / 'app' / 'src' / 'main' / 'java' / 'com' / 'aetheria' / 'app' / 'NotificationChannels.java'
    
    print(f"  {'✓' if manifest.exists() else '✗'} AndroidManifest.xml: {manifest.exists()}")
    
    if manifest.exists():
        manifest_content = manifest.read_text()
        has_perm = 'POST_NOTIFICATIONS' in manifest_content
        print(f"    {'✓' if has_perm else '✗'} POST_NOTIFICATIONS permission: {has_perm}")
    
    print(f"  {'✓' if activity.exists() else '✗'} MainActivity.java: {activity.exists()}")
    print(f"  {'✓' if channels_java.exists() else '✗'} NotificationChannels.java: {channels_java.exists()}")

# Check 7: Documentation
print(f"\nDocumentation:")

docs = [
    'EXECUTIVE_SUMMARY.md',
    'PRODUCTION_AUDIT_REPORT.md',
    'IMPLEMENTATION_GUIDE.md',
    'PRODUCTION_CHECKLIST.md',
    'POSTGRESQL_CONFIG.md',
    'LOGGING_CONFIG.md',
    'INDEX.md',
]

for doc in docs:
    doc_path = base_dir.parent / doc
    exists = doc_path.exists()
    print(f"  {'✓' if exists else '✗'} {doc}: {exists}")

# Check 8: Logs directory
logs_dir = base_dir / 'logs'
print(f"\nLogs Directory:")
logs_dir.mkdir(exist_ok=True)
print(f"  ✓ logs/ directory ready: {logs_dir.exists()}")

print("\n" + "="*70)
print("  ✓ VERIFICATION COMPLETE")
print("="*70 + "\n")

print("Next Steps:")
print("1. Switch to PostgreSQL: Set DATABASE_URL environment variable")
print("2. Run migrations: python manage.py migrate")
print("3. Create superuser: python manage.py createsuperuser")
print("4. Run tests: python manage.py test")
print("5. Start server: python manage.py runserver")
print("\nThen check browser console for WebSocket connection status\n")
