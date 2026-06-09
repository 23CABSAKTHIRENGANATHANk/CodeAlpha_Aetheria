#!/usr/bin/env python
"""
Aetheria Production Deployment Script
Automates all pre-deployment verification checks and deployment steps

Usage:
    python deploy.py --check              # Run verification checks only
    python deploy.py --deploy             # Full deployment
    python deploy.py --rollback           # Rollback to previous version
    python deploy.py --test               # Run all tests
"""

import os
import sys
import django
import subprocess
import json
from datetime import datetime
import argparse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialmedia.settings')
django.setup()

from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.core.cache import cache

class DeploymentManager:
    def __init__(self):
        self.timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        self.checks_passed = []
        self.checks_failed = []
        
    def print_header(self, text):
        print(f"\n{'='*70}")
        print(f" {text}")
        print(f"{'='*70}\n")
        
    def print_check(self, name, status, details=""):
        symbol = "✅" if status else "❌"
        print(f"{symbol} {name}")
        if details:
            print(f"   {details}")
        if status:
            self.checks_passed.append(name)
        else:
            self.checks_failed.append(name)
    
    def run_checks(self):
        """Run all pre-deployment verification checks"""
        self.print_header("PRE-DEPLOYMENT VERIFICATION")
        
        # 1. Django checks
        print("Running Django security checks...")
        try:
            from io import StringIO
            import sys
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            call_command('check', '--deploy')
            sys.stdout = old_stdout
            self.print_check("Django security checks", True)
        except Exception as e:
            self.print_check("Django security checks", False, str(e))
        
        # 2. Database connection
        print("Testing database connection...")
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            self.print_check("Database connection", True)
        except Exception as e:
            self.print_check("Database connection", False, str(e))
        
        # 3. Cache configuration
        print("Testing cache configuration...")
        try:
            cache.set('test_key', 'test_value', 60)
            result = cache.get('test_key')
            cache.delete('test_key')
            self.print_check("Cache configuration", result == 'test_value')
        except Exception as e:
            self.print_check("Cache configuration", False, str(e))
        
        # 4. Environment variables
        print("Checking environment variables...")
        required_vars = [
            'SECRET_KEY', 'DEBUG', 'ALLOWED_HOSTS', 
            'DATABASE_URL', 'REDIS_URL'
        ]
        missing_vars = [v for v in required_vars if not os.environ.get(v)]
        self.print_check(
            "Environment variables",
            len(missing_vars) == 0,
            f"Missing: {missing_vars}" if missing_vars else "All required variables set"
        )
        
        # 5. Static files
        print("Checking static files...")
        try:
            static_dir = os.path.join('socialmedia', 'staticfiles')
            static_exists = os.path.exists(static_dir) and os.listdir(static_dir)
            self.print_check("Static files collected", static_exists)
        except Exception as e:
            self.print_check("Static files collected", False, str(e))
        
        # 6. Database migrations
        print("Checking database migrations...")
        try:
            from io import StringIO
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            call_command('showmigrations', '--plan')
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout
            
            # Check if there are any unapplied migrations
            has_unapplied = '[ ]' in output
            self.print_check(
                "Database migrations",
                not has_unapplied,
                "All migrations applied" if not has_unapplied else "Unapplied migrations found"
            )
        except Exception as e:
            self.print_check("Database migrations", False, str(e))
        
        # 7. Firebase configuration
        print("Checking Firebase configuration...")
        try:
            firebase_file = os.path.join('socialmedia', 'firebase-service-account.json')
            firebase_exists = os.path.exists(firebase_file)
            self.print_check("Firebase credentials", firebase_exists)
        except Exception as e:
            self.print_check("Firebase credentials", False, str(e))
        
        # 8. Database indexes
        print("Checking database indexes...")
        try:
            if connection.vendor == 'postgresql':
                cursor = connection.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public'
                """)
                index_count = cursor.fetchone()[0]
                cursor.close()
                self.print_check("Database indexes", index_count > 10, f"{index_count} indexes found")
            else:
                self.print_check("Database indexes", True, "Not PostgreSQL (skipped)")
        except Exception as e:
            self.print_check("Database indexes", False, str(e))
        
        # Summary
        self.print_header("CHECK SUMMARY")
        print(f"✅ Passed: {len(self.checks_passed)}")
        print(f"❌ Failed: {len(self.checks_failed)}")
        
        if self.checks_failed:
            print(f"\nFailed checks:")
            for check in self.checks_failed:
                print(f"  - {check}")
            return False
        else:
            print("\n✅ All checks passed! Ready for deployment.")
            return True
    
    def run_tests(self):
        """Run Django tests"""
        self.print_header("RUNNING TESTS")
        try:
            call_command('test', verbosity=2)
            self.print_check("Test suite", True)
            return True
        except Exception as e:
            self.print_check("Test suite", False, str(e))
            return False
    
    def collect_static(self):
        """Collect static files"""
        self.print_header("COLLECTING STATIC FILES")
        try:
            call_command('collectstatic', '--noinput', verbosity=0)
            self.print_check("Static files collection", True)
            return True
        except Exception as e:
            self.print_check("Static files collection", False, str(e))
            return False
    
    def backup_database(self):
        """Backup database before deployment"""
        self.print_header("BACKING UP DATABASE")
        try:
            if connection.vendor == 'postgresql':
                backup_file = f"backups/aetheria_backup_{self.timestamp}.sql"
                os.makedirs("backups", exist_ok=True)
                
                db_name = connection.settings_dict['NAME']
                db_user = connection.settings_dict['USER']
                db_host = connection.settings_dict['HOST']
                
                cmd = f"pg_dump -U {db_user} -h {db_host} {db_name} > {backup_file}"
                result = subprocess.run(cmd, shell=True, capture_output=True)
                
                if result.returncode == 0:
                    self.print_check("Database backup", True, f"Backed up to {backup_file}")
                    return True
                else:
                    self.print_check("Database backup", False, result.stderr.decode())
                    return False
            else:
                self.print_check("Database backup", True, "Not PostgreSQL (skipped)")
                return True
        except Exception as e:
            self.print_check("Database backup", False, str(e))
            return False
    
    def run_migrations(self):
        """Run pending database migrations"""
        self.print_header("RUNNING MIGRATIONS")
        try:
            call_command('migrate', verbosity=1)
            self.print_check("Database migrations", True)
            return True
        except Exception as e:
            self.print_check("Database migrations", False, str(e))
            return False
    
    def create_indexes(self):
        """Create database indexes"""
        self.print_header("CREATING DATABASE INDEXES")
        try:
            call_command('create_database_indexes', verbosity=1)
            self.print_check("Database indexes creation", True)
            return True
        except Exception as e:
            self.print_check("Database indexes creation", False, str(e))
            return False
    
    def deploy(self):
        """Full deployment process"""
        self.print_header("AETHERIA PRODUCTION DEPLOYMENT")
        print(f"Deployment started: {self.timestamp}\n")
        
        # Run verification checks
        if not self.run_checks():
            print("\n❌ Pre-deployment checks failed. Aborting deployment.")
            return False
        
        # Backup database
        if not self.backup_database():
            print("\n⚠️  Database backup failed. Continue anyway? (y/n)")
            if input().lower() != 'y':
                return False
        
        # Run tests
        print("\nRun tests before deployment? (y/n)")
        if input().lower() == 'y':
            if not self.run_tests():
                print("\n❌ Tests failed. Aborting deployment.")
                return False
        
        # Collect static files
        if not self.collect_static():
            print("\n❌ Static file collection failed. Aborting deployment.")
            return False
        
        # Run migrations
        if not self.run_migrations():
            print("\n❌ Database migrations failed. Aborting deployment.")
            return False
        
        # Create indexes
        if not self.create_indexes():
            print("\n⚠️  Index creation failed but continuing deployment.")
        
        # Deployment complete
        self.print_header("DEPLOYMENT COMPLETE ✅")
        print(f"""
✅ Deployment successful!

What's next:
1. Monitor logs: tail -f logs/aetheria_errors.log
2. Check status: curl https://yourdomain.com/health/
3. Test notifications: firebase console
4. Monitor metrics: Datadog/Sentry

If issues occur:
python deploy.py --rollback
        """)
        return True
    
    def rollback(self):
        """Rollback to previous deployment"""
        self.print_header("ROLLING BACK DEPLOYMENT")
        
        try:
            # Get previous commit
            result = subprocess.run(
                "git log --oneline -n 2 --pretty=format:%H",
                shell=True,
                capture_output=True,
                text=True
            )
            commits = result.stdout.strip().split('\n')
            
            if len(commits) < 2:
                print("❌ No previous commit to rollback to")
                return False
            
            previous_commit = commits[1]
            print(f"Rolling back to commit: {previous_commit}")
            
            # Revert changes
            subprocess.run(f"git revert {commits[0]} --no-edit", shell=True)
            subprocess.run("git push origin main", shell=True)
            
            print("✅ Rollback complete. Please verify the deployment.")
            return True
            
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Aetheria Deployment Manager')
    parser.add_argument('--check', action='store_true', help='Run verification checks only')
    parser.add_argument('--deploy', action='store_true', help='Full deployment')
    parser.add_argument('--rollback', action='store_true', help='Rollback to previous version')
    parser.add_argument('--test', action='store_true', help='Run tests only')
    
    args = parser.parse_args()
    
    manager = DeploymentManager()
    
    if args.check:
        manager.run_checks()
    elif args.test:
        manager.run_tests()
    elif args.rollback:
        manager.rollback()
    elif args.deploy:
        success = manager.deploy()
        sys.exit(0 if success else 1)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
