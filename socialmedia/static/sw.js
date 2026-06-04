const CACHE_NAME = 'aetheria-cache-v7';
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
