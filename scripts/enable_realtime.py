"""
Enable Supabase Realtime on required tables via SQL.
Also migrates local SQLite data to Supabase.
"""
import os, sys, json, urllib.request, urllib.error

env_file = r'e:\project\project\social media\.env'
with open(env_file, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

def run_sql(sql):
    """Execute SQL via Supabase REST API (pg_query endpoint)."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/exec_sql"
    # Use pg endpoint instead
    url = f"{SUPABASE_URL}/rest/v1/"
    # Use Management API for DDL
    mgmt_url = f"https://api.supabase.com/v1/projects/klzwqrecemqoquvcxsar/database/query"
    data = json.dumps({"query": sql}).encode()
    req = urllib.request.Request(mgmt_url, data=data, headers={
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

print("=" * 55)
print("Enabling Supabase Realtime on tables")
print("=" * 55)

# Tables to enable Realtime on
REALTIME_TABLES = ["users_notification", "users_message"]

for table in REALTIME_TABLES:
    sql = f"ALTER PUBLICATION supabase_realtime ADD TABLE {table};"
    status, resp = run_sql(sql)
    if status in (200, 201, 204):
        print(f"  [OK]  Realtime enabled: {table}")
    elif "already" in resp.lower() or "42710" in resp:
        print(f"  [--]  Already enabled : {table}")
    else:
        print(f"  [?]   {table}: {status} -> {resp[:120]}")

print()
print("[DONE] Realtime configuration attempted.")
print()
print("NOTE: If any tables failed, enable Realtime manually in:")
print("  Supabase Dashboard -> Database -> Replication -> supabase_realtime")
print("  Add tables: users_notification, users_message")
