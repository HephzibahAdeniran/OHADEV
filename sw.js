const CACHE_VERSION = 'v2';
const CACHE_NAME = `oha-${CACHE_VERSION}`;
const CORE_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.svg',
  '/assets/css/main.css'
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

  // Navigation requests -> return cached index.html (app shell)
  if (event.request.mode === 'navigate') {
    event.respondWith(
      caches.match('/index.html').then(resp => resp || fetch('/index.html'))
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
