const CACHE_VERSION = 'v2';
const CACHE_NAME = `oha-${CACHE_VERSION}`;
const CORE_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.svg',
  '/assets/css/main.css',
  '/assets/media/freepik-luxury-800.webp'
];

// During install, cache core assets for offline and faster repeat loads
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS))
  );
  self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
    ))
  );
  self.clients.claim();
});

// Helper: stale-while-revalidate for images
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const network = fetch(request).then(resp => {
    if (resp && resp.status === 200) cache.put(request, resp.clone());
    return resp;
  }).catch(() => null);
  return cached || network;
}

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Only handle GET requests
  if (event.request.method !== 'GET') return;

  // Navigation requests were previously intercepted for app-shell offline support.
  // Avoid intercepting navigation responses here so the browser can use the back/forward
  // cache (bfcache) and restore pages more reliably. Static caching of samples is still
  // handled by the install/activate steps above.

  // Styles: cache-first for CSS
  if (url.pathname.endsWith('.css') || event.request.destination === 'style') {
    event.respondWith(
      caches.match(event.request).then(resp => {
        if (resp) return resp;
        return fetch(event.request).then(net => {
          return caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, net.clone());
            return net;
          });
        });
      })
    );
    return;
  }

  // Images: stale-while-revalidate
  if (url.pathname.startsWith('/assets/media') || /\.(png|jpg|jpeg|webp|svg)$/.test(url.pathname)) {
    event.respondWith(staleWhileRevalidate(event.request));
    return;
  }

  // Default: try cache, fall back to network
  event.respondWith(
    caches.match(event.request).then(resp => resp || fetch(event.request))
  );
});
