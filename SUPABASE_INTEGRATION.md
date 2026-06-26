## Supabase integration for this Django project

Summary of work done:
- Added Supabase Python client helper: `socialmedia/supabase_client.py`
- Added token extraction and verification helper: `socialmedia/supabase_auth.py`
- Added Django auth backend: `users/backends.py`
- Added middleware to authenticate `Authorization: Bearer <token>`: `socialmedia/supabase_middleware.py`
- Added a minimal Supabase storage backend: `socialmedia/storage_backends.py` and enabled it when `SUPABASE_URL`/`SUPABASE_KEY` are set
- Updated `requirements.txt` to include `supabase`, `python-dotenv`, and `PyJWT`
- Added `.env.example` with required environment variables

Next steps to run locally:

1. Install dependencies

```bash
python -m pip install -r "requirements.txt"
python -m pip install -r "socialmedia/requirements.txt"
```

2. Create a `.env` file at the project root (copy from `.env.example`) and set:
- `DATABASE_URL` to your Supabase Postgres connection string (or set DB_* parts)
- `SUPABASE_URL` and `SUPABASE_KEY` (service-role or anon as appropriate)
- `SUPABASE_JWT_SECRET` if you plan to verify JWTs server-side

3. Run migrations and create a superuser

```bash
python socialmedia/manage.py migrate
python socialmedia/manage.py createsuperuser
```

4. Verify file uploads use Supabase storage by uploading a profile image in the UI; check Supabase Storage bucket.

Notes on realtime:
- For realtime features prefer client-side subscriptions using `@supabase/supabase-js`.
- If you need server-side listeners, I can implement a forwarding service using Django Channels that subscribes to Supabase Realtime and broadcasts to connected websocket clients.

Production migration & backup helpers
-----------------------------------

I added scripts under `scripts/` to help with production workflows:

- `scripts/backup_db.py`: Attempt to run `pg_dump --dbname=<DATABASE_URL>` and save a custom-format dump in `backups/`.
- `scripts/migrate_prod.py`: Load `.env` and run Django `migrate` against `DATABASE_URL` (non-interactive).
- `scripts/realtime_forwarder.py`: A placeholder that demonstrates subscribing to Supabase realtime events and printing payloads. Adapt it to your SDK version and forward to Channels as needed.

Run examples (from project root):

```bash
# Create a DB backup
python scripts/backup_db.py

# Run migrations against DATABASE_URL
python scripts/migrate_prod.py

# Run the realtime forwarder (dev/test)
python scripts/realtime_forwarder.py
```

Important: these scripts expect a valid `.env` containing `DATABASE_URL` and
Supabase credentials. Do not commit `.env` to source control.

Auth integration details:
- The `SupabaseAuthBackend` maps Supabase users to Django `User` records. It uses the Supabase client or JWT secret to validate tokens.
- The `SupabaseAuthMiddleware` will authenticate requests presenting `Authorization: Bearer <token>` and set `request.user`.
