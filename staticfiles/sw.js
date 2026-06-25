const CACHE_NAME = 'aetheria-cache-v8';
const ASSETS = [
  '/static/css/main.css',
  '/static/js/main.js',
  '/static/images/default_profile.png'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    }).catch(err => console.log("Cache installation warning:", err))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET' || !event.request.url.startsWith(self.location.origin)) {
    return;
  }

  // Network-only for HTML navigations to prevent redirect loop or ERR_FAILED crashes
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(err => {
        return new Response("<html><body><h1>You are offline. Please check your network connection.</h1></body></html>", {
          status: 503,
          headers: {'Content-Type': 'text/html'}
        });
      })
    );
    return;
  }

  // Cache-first for static assets
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      return cachedResponse || fetch(event.request).then(response => {
        if (event.request.url.includes('/static/')) {
          const resClone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, resClone));
        }
        return response;
      });
    })
  );
});

// ──────────────────────────────────────────────
// Push Notifications Background Handler
// ──────────────────────────────────────────────
self.addEventListener('push', (event) => {
  let payload = {};
  if (event.data) {
    try {
      payload = event.data.json();
    } catch (e) {
      payload = { title: 'Aetheria', body: event.data.text() };
    }
  }

  const title = payload.title || 'Aetheria';
  const options = {
    body: payload.body || '',
    icon: '/static/images/default_profile.png',
    badge: '/static/images/default_profile.png',
    data: payload.data || {}
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const data = event.notification.data;
  let targetUrl = '/';

  if (data) {
    if (data.notification_type === 'message' && data.room_id) {
      targetUrl = `/messages/room/${data.room_id}/`;
    } else if (data.notification_type === 'message' && data.sender_id) {
      targetUrl = `/messages/${data.sender_id}/`;
    } else if (data.post_id) {
      targetUrl = `/post/${data.post_id}/`;
    } else if (data.sender_id) {
      targetUrl = `/profile/${data.sender_id}/`;
    }
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes(targetUrl) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});
