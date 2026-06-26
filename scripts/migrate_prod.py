"""Run Django migrations against the production DATABASE_URL.

This script loads `.env` and invokes Django management `migrate` with the
current environment. Intended to be run from the project root.

Usage:
  python scripts/migrate_prod.py
"""
import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

def main():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print('DATABASE_URL not set. Aborting.')
        return 1

    env = os.environ.copy()
    # Run migrations with environment loaded
    cmd = ['python', 'socialmedia/manage.py', 'migrate', '--noinput']
    print('Running migrations:',' '.join(cmd))
    try:
        subprocess.check_call(cmd, env=env)
        print('Migrations completed successfully')
        return 0
    except subprocess.CalledProcessError as e:
        print('Migrations failed with exit code', e.returncode)
        return e.returncode

if __name__ == '__main__':
    raise SystemExit(main())
