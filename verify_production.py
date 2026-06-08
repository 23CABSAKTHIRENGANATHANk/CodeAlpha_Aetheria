#!/usr/bin/env python
"""
AETHERIA Production Verification Script
Tests all critical Phase 1 implementations
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialmedia.settings')
django.setup()

from django.conf import settings
from django.core.management import call_command
import logging

logger = logging.getLogger('aetheria')

class ProductionVerifier:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        
    def test(self, name, condition, error_msg=""):
        """Test a condition and print result"""
        status = "✓" if condition else "✗"
        result = "PASS" if condition else "FAIL"
        
        print(f"  {status} {name:<50} [{result}]")
        
        if condition:
            self.passed += 1
        else:
            self.failed += 1
            if error_msg:
                print(f"    └─ Error: {error_msg}")
        
        return condition
    
    def warn(self, name, message):
        """Print a warning"""
        print(f"  ⚠ {name:<50} [WARN]")
        print(f"    └─ {message}")
        self.warnings += 1
    
    def section(self, title):
        """Print a section header"""
        print(f"\n{'═' * 70}")
        print(f"  {title}")
        print(f"{'═' * 70}")
    
    def summary(self):
        """Print summary"""
        total = self.passed + self.failed
        print(f"\n{'═' * 70}")
        print(f"  VERIFICATION SUMMARY")
        print(f"{'═' * 70}")
        print(f"  Passed:  {self.passed}/{total}")
        print(f"  Failed:  {self.failed}/{total}")
        print(f"  Warnings: {self.warnings}")
        
        if self.failed == 0:
            print(f"\n  ✓ ALL TESTS PASSED! Ready for Phase 2 implementation.")
        else:
            print(f"\n  ✗ FAILED: Fix {self.failed} issues before proceeding.")
        
        print(f"{'═' * 70}\n")
        
        return self.failed == 0
    
    def run_all_tests(self):
        """Run all verification tests"""
        
        # 1. Database Configuration
        self.section("1. DATABASE CONFIGURATION")
        
        db_config = settings.DATABASES['default']
        is_postgresql = db_config.get('ENGINE') == 'django.db.backends.postgresql'
        is_sqlite = db_config.get('ENGINE') == 'django.db.backends.sqlite3'
        
        self.test(
            "Database Engine",
            is_postgresql or is_sqlite,
            f"Engine: {db_config.get('ENGINE')}"
        )
        
        if is_sqlite:
            self.warn(
                "SQLite in Production",
                "SQLite is only for development. Use PostgreSQL for production!"
            )
        
        # 2. Logging Configuration
        self.section("2. LOGGING CONFIGURATION")
        
        has_logging = hasattr(settings, 'LOGGING') and settings.LOGGING
        self.test(
            "Logging Configuration Exists",
            has_logging,
            "LOGGING not found in settings"
        )
        
        if has_logging:
            logs_dir = Path(settings.BASE_DIR) / 'logs'
            logs_dir.mkdir(exist_ok=True)
            
            self.test(
                "Logs Directory Exists",
                logs_dir.exists(),
                f"Cannot create {logs_dir}"
            )
            
            for log_name in ['file', 'error_file', 'websocket_file', 'firebase_file']:
                handler_exists = log_name in settings.LOGGING.get('handlers', {})
                self.test(
                    f"Logger Handler: {log_name}",
                    handler_exists,
                    f"Handler {log_name} not configured"
                )
        
        # 3. Static Files
        self.section("3. FRONTEND RESOURCES")
        
        static_dir = Path(settings.BASE_DIR) / 'static'
        
        self.test(
            "Static Files Directory",
            static_dir.exists(),
            f"Directory not found: {static_dir}"
        )
        
        websocket_js = static_dir / 'js' / 'websocket-client.js'
        firebase_js = static_dir / 'js' / 'firebase-notifications.js'
        
        self.test(
            "WebSocket Client (websocket-client.js)",
            websocket_js.exists(),
            f"Missing: {websocket_js}"
        )
        
        self.test(
            "Firebase Notifications (firebase-notifications.js)",
            firebase_js.exists(),
            f"Missing: {firebase_js}"
        )
        
        # 4. Template Configuration
        self.section("4. TEMPLATE CONFIGURATION")
        
        template_dir = Path(settings.BASE_DIR) / 'templates'
        base_html = template_dir / 'base.html'
        
        self.test(
            "Base Template Exists",
            base_html.exists(),
            f"Missing: {base_html}"
        )
        
        if base_html.exists():
            content = base_html.read_text()
            
            self.test(
                "WebSocket Script Included",
                'websocket-client.js' in content,
                "Missing: <script src='...websocket-client.js'></script>"
            )
            
            self.test(
                "Firebase Script Included",
                'firebase-notifications.js' in content,
                "Missing: <script src='...firebase-notifications.js'></script>"
            )
            
            self.test(
                "Toast Container Present",
                'notification-toast-container' in content,
                "Missing: <div id='notification-toast-container'></div>"
            )
            
            self.test(
                "Connection Indicator Present",
                'connection-status-indicator' in content,
                "Missing: <div class='connection-status-indicator'></div>"
            )
        
        # 5. CSS Configuration
        self.section("5. CSS STYLES")
        
        css_file = static_dir / 'css' / 'main.css'
        
        self.test(
            "Main CSS File Exists",
            css_file.exists(),
            f"Missing: {css_file}"
        )
        
        if css_file.exists():
            css_content = css_file.read_text()
            
            self.test(
                "Connection Status Styles",
                'connection-status-indicator' in css_content,
                "Missing CSS for connection indicator"
            )
            
            self.test(
                "Toast Notification Styles",
                'notification-toast-container' in css_content,
                "Missing CSS for notification toast"
            )
            
            self.test(
                "Animation Styles",
                'slideIn' in css_content and 'slideOut' in css_content,
                "Missing animation styles"
            )
        
        # 6. Android Configuration
        self.section("6. ANDROID CONFIGURATION")
        
        android_dir = Path(settings.BASE_DIR).parent / 'android'
        
        notification_channels = android_dir / 'app' / 'src' / 'main' / 'java' / 'com' / 'aetheria' / 'app' / 'NotificationChannels.java'
        main_activity = android_dir / 'app' / 'src' / 'main' / 'java' / 'com' / 'aetheria' / 'app' / 'MainActivity.java'
        manifest = android_dir / 'app' / 'src' / 'main' / 'AndroidManifest.xml'
        
        self.test(
            "NotificationChannels.java Exists",
            notification_channels.exists(),
            f"Missing: {notification_channels}"
        )
        
        self.test(
            "MainActivity.java Exists",
            main_activity.exists(),
            f"Missing: {main_activity}"
        )
        
        self.test(
            "AndroidManifest.xml Exists",
            manifest.exists(),
            f"Missing: {manifest}"
        )
        
        if main_activity.exists():
            activity_content = main_activity.read_text()
            
            self.test(
                "MainActivity imports NotificationChannels",
                'NotificationChannels' in activity_content,
                "Missing import or usage of NotificationChannels"
            )
            
            self.test(
                "MainActivity initializes notification channels",
                'createNotificationChannels' in activity_content,
                "Missing call to createNotificationChannels()"
            )
            
            self.test(
                "MainActivity requests notification permission",
                'requestNotificationPermission' in activity_content or 'POST_NOTIFICATIONS' in activity_content,
                "Missing notification permission request"
            )
        
        if manifest.exists():
            manifest_content = manifest.read_text()
            
            self.test(
                "POST_NOTIFICATIONS permission in manifest",
                'POST_NOTIFICATIONS' in manifest_content,
                "Missing: <uses-permission android:name='android.permission.POST_NOTIFICATIONS' />"
            )
        
        # 7. Firebase Configuration
        self.section("7. FIREBASE CONFIGURATION")
        
        firebase_key = Path(settings.BASE_DIR) / 'firebase-service-account.json'
        has_firebase_env = os.environ.get('FIREBASE_CREDENTIALS_JSON')
        
        firebase_configured = firebase_key.exists() or has_firebase_env
        
        self.test(
            "Firebase Configured",
            firebase_configured,
            "Missing Firebase credentials (firebase-service-account.json or FIREBASE_CREDENTIALS_JSON env var)"
        )
        
        # 8. Redis Configuration
        self.section("8. REDIS CONFIGURATION")
        
        channel_layers = getattr(settings, 'CHANNEL_LAYERS', {})
        has_channels = bool(channel_layers)
        
        self.test(
            "Django Channels Configured",
            has_channels,
            "CHANNEL_LAYERS not configured"
        )
        
        if has_channels:
            backend = channel_layers.get('default', {}).get('BACKEND', '')
            is_redis = 'redis' in backend.lower()
            
            if is_redis:
                self.test(
                    "Redis Channel Layer",
                    True,
                    "Using Redis for real-time communication"
                )
            else:
                self.warn(
                    "In-Memory Channel Layer",
                    "Using in-memory channel layer. Set REDIS_URL for production."
                )
        
        # 9. Required Python Packages
        self.section("9. PYTHON DEPENDENCIES")
        
        required_packages = {
            'django': 'Django',
            'channels': 'Django Channels',
            'daphne': 'Daphne ASGI',
            'firebase_admin': 'Firebase Admin SDK',
            'cloudinary': 'Cloudinary',
        }
        
        for package, name in required_packages.items():
            try:
                __import__(package)
                self.test(f"Package: {name}", True)
            except ImportError:
                self.test(f"Package: {name}", False, f"Install with: pip install {package}")
        
        # 10. Documentation Files
        self.section("10. DOCUMENTATION FILES")
        
        docs = {
            'EXECUTIVE_SUMMARY.md': 'Executive Summary',
            'PRODUCTION_AUDIT_REPORT.md': 'Audit Report',
            'IMPLEMENTATION_GUIDE.md': 'Implementation Guide',
            'PRODUCTION_CHECKLIST.md': 'Checklist',
            'POSTGRESQL_CONFIG.md': 'PostgreSQL Config',
            'LOGGING_CONFIG.md': 'Logging Config',
            'INDEX.md': 'Documentation Index',
        }
        
        for filename, name in docs.items():
            filepath = Path(settings.BASE_DIR) / filename
            self.test(
                f"Doc: {name}",
                filepath.exists(),
                f"Missing: {filepath}"
            )
        
        # Final Summary
        return self.summary()

if __name__ == '__main__':
    verifier = ProductionVerifier()
    success = verifier.run_all_tests()
    sys.exit(0 if success else 1)
