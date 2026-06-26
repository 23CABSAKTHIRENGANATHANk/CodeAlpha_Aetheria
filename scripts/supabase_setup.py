"""
Setup script: Creates Supabase storage buckets.
Run from: project root.
"""

import os
import sys
import json
import urllib.request
import urllib.error

# ── Load .env ──────────────────────────────────────────────────────────
env_file = r'e:\project\project\social media\.env'
with open(env_file, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

print(f"SUPABASE_URL : {SUPABASE_URL}")
print(f"KEY set      : {bool(SUPABASE_KEY)}")
print(f"DB URL set   : {bool(os.environ.get('SUPABASE_DB_URL'))}")
print()

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL or SUPABASE_KEY not set in .env")
    sys.exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

def api_request(method, path, body=None):
    url = f"{SUPABASE_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

# ── Create Storage Buckets ──────────────────────────────────────────────
BUCKETS = [
    {"id": "avatars",  "name": "avatars",  "public": True},
    {"id": "posts",    "name": "posts",    "public": True},
    {"id": "stories",  "name": "stories",  "public": True},
    {"id": "media",    "name": "media",    "public": True},
    {"id": "messages", "name": "messages", "public": False},  # private — signed URLs
]

print("=" * 50)
print("Creating Supabase Storage Buckets...")
print("=" * 50)

for bucket in BUCKETS:
    status, resp = api_request("POST", "/storage/v1/bucket", bucket)
    if status == 200:
        print(f"  [OK]  Created  : {bucket['id']} ({'public' if bucket['public'] else 'private'})")
    elif status == 409 or (isinstance(resp, dict) and 'already exists' in str(resp).lower()):
        print(f"  [--]  Exists   : {bucket['id']} (already created)")
    else:
        print(f"  [ERR] Failed   : {bucket['id']} -> {status} {resp}")

print()
print("=" * 50)
print("Summary")
print("=" * 50)
print(f"  SUPABASE_URL : {SUPABASE_URL}")
print(f"  Buckets      : avatars, posts, stories, media (public) | messages (private)")
print()
print("[DONE] Storage setup complete!")
print()
print("Next steps:")
print("  1. Run: python manage.py migrate")
print("  2. Run: python manage.py migrate_to_supabase --dry-run --verbose")
