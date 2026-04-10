const CACHE_NAME = "uschat-v1";
const urlsToCache = [
    "/",
    "/static/style.css",
    "/static/chat.js",
    "/static/icon-192.png",
    "/static/icon-512.png",
    "/manifest.json"
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
    );
});

self.addEventListener("fetch", event => {
    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request);
        })
    );
});