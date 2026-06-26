"""Create a PostgreSQL backup (custom format) using `pg_dump`.

Usage:
  python scripts/backup_db.py

This script expects `DATABASE_URL` to be set in the environment or in a .env file.
It will attempt to call the `pg_dump` binary with `--dbname=<DATABASE_URL>`.
If `pg_dump` is not available, it will print instructions.
"""
import os
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

def main():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print('DATABASE_URL not set. Please set it in the environment or .env.')
        return 1

    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    backups_dir = Path('backups')
    backups_dir.mkdir(exist_ok=True)
    backup_file = backups_dir / f'db_backup_{timestamp}.dump'

    cmd = ['pg_dump', f'--dbname={db_url}', '--format=custom', f'--file={str(backup_file)}']
    print('Running:', ' '.join(cmd))
    try:
        subprocess.check_call(cmd)
        print('Backup saved to:', backup_file)
        return 0
    except FileNotFoundError:
        print('pg_dump not found on PATH. Install PostgreSQL client tools.')
        print('Alternatively, run: pg_dump --dbname="<DATABASE_URL>" --format=custom --file=backups/db_backup.dump')
        return 2
    except subprocess.CalledProcessError as e:
        print('pg_dump failed with exit code', e.returncode)
        return e.returncode

if __name__ == '__main__':
    raise SystemExit(main())
