"""Basic placeholder for a Supabase -> Django Channels forwarder.

This is a minimal example that attempts to subscribe to a table's realtime
changes via the Supabase Python client. Many production setups prefer
client-side `@supabase/supabase-js` subscriptions; use this only when the
server must receive row events and forward them to connected websocket clients.

Requirements: `supabase` client with realtime support and Django Channels.
"""
import os
import time
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client


def main():
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    if not url or not key:
        print('SUPABASE_URL or SUPABASE_KEY not set. Aborting.')
        return

    client = create_client(url, key)

    # Many versions of supabase-py expose realtime via client.realtime
    realtime = getattr(client, 'realtime', None)
    if realtime is None:
        print('Realtime not available in this Supabase client; check SDK version.')
        return

    print('Subscribing to realtime changes on table: posts (public schema)')

    def handle_payload(payload):
        print('Realtime event:', payload)
        # TODO: forward to Django Channels or other websocket layer

    # Example subscription expression — adapt to the SDK version in use.
    try:
        subscription = realtime.subscribe('realtime:public:posts', handle_payload)
        print('Subscription created. Listening...')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print('Stopping listener...')
            realtime.unsubscribe(subscription)
    except Exception as e:
        print('Could not create realtime subscription:', e)


if __name__ == '__main__':
    main()
