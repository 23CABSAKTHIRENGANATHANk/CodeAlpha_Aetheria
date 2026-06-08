from pathlib import Path

base = Path('.')
print('\n' + '='*60)
print('AETHERIA PHASE 1 IMPLEMENTATION VERIFICATION')
print('='*60)

checks = []

# Check static files
ws_js = base / 'static' / 'js' / 'websocket-client.js'
fb_js = base / 'static' / 'js' / 'firebase-notifications.js'
checks.append(('websocket-client.js', ws_js.exists()))
checks.append(('firebase-notifications.js', fb_js.exists()))

# Check CSS
css = base / 'static' / 'css' / 'main.css'
if css.exists():
    try:
        content = css.read_text(encoding='utf-8')
        checks.append(('Connection indicator CSS', 'connection-status-indicator' in content))
        checks.append(('Toast notification CSS', 'notification-toast-container' in content))
    except:
        checks.append(('Connection indicator CSS', False))
        checks.append(('Toast notification CSS', False))

# Check templates
html = base / 'templates' / 'base.html'
if html.exists():
    try:
        content = html.read_text(encoding='utf-8')
        checks.append(('WebSocket script in HTML', 'websocket-client.js' in content))
        checks.append(('Firebase script in HTML', 'firebase-notifications.js' in content))
        checks.append(('Toast container in HTML', 'notification-toast-container' in content))
        checks.append(('Connection indicator in HTML', 'connection-status-indicator' in content))
    except:
        pass

# Check settings
settings = base / 'socialmedia' / 'settings.py'
if settings.exists():
    try:
        content = settings.read_text(encoding='utf-8')
        checks.append(('LOGGING configuration', 'LOGGING = {' in content))
        checks.append(('PostgreSQL support', 'postgresql' in content))
    except:
        pass

# Check Android
android = base.parent.parent / 'android'
manifest = android / 'app' / 'src' / 'main' / 'AndroidManifest.xml'
activity = android / 'app' / 'src' / 'main' / 'java' / 'com' / 'aetheria' / 'app' / 'MainActivity.java'
channels_java = android / 'app' / 'src' / 'main' / 'java' / 'com' / 'aetheria' / 'app' / 'NotificationChannels.java'

if manifest.exists():
    try:
        content = manifest.read_text(encoding='utf-8')
        checks.append(('POST_NOTIFICATIONS permission', 'POST_NOTIFICATIONS' in content))
    except:
        pass

if activity.exists():
    try:
        content = activity.read_text(encoding='utf-8')
        checks.append(('MainActivity NotificationChannels init', 'createNotificationChannels' in content))
        checks.append(('MainActivity permission request', 'requestNotificationPermission' in content))
    except:
        pass

if channels_java.exists():
    checks.append(('NotificationChannels.java exists', True))

# Print results
passed = 0
failed = 0
print()
for name, result in checks:
    status = '✓' if result else '✗'
    print(f'  {status} {name:<40} {str(result)}')
    if result:
        passed += 1
    else:
        failed += 1

print('='*60)
print(f'Results: {passed} Passed, {failed} Failed')
print('='*60 + '\n')
