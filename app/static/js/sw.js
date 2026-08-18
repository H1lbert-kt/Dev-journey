const CACHE_NAME = 'devjourney-v2';
const STATIC_ASSETS = [
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/js/session-timer.js',
    '/static/manifest.json'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;
    if (event.request.url.includes('/api/') || event.request.url.includes('/timer/save') || event.request.url.includes('/timer/ping')) return;

    event.respondWith(
        fetch(event.request)
            .then(response => {
                if (response.ok && event.request.url.startsWith(self.location.origin)) {
                    const clone = response.clone();
                    event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone)));
                }
                return response;
            })
            .catch(() => caches.match(event.request).then(r => r || new Response('Offline', {status: 503, headers: {'Content-Type': 'text/plain'}})))
    );
});
