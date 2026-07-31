const CACHE_NAME = "ark-terminal-v4";

const APP_SHELL = [
    "./",
    "./index.html",
    "./style.css",
    "./script.js",
    "./manifest.json",
    "./discovery/index.html",
    "./discovery/style.css",
    "./discovery/script.js",
    "./icons/icon-192.png",
    "./icons/icon-512.png"
];

self.addEventListener("install", function (event) {
    event.waitUntil(
        caches
            .open(CACHE_NAME)
            .then(function (cache) {
                return cache.addAll(APP_SHELL);
            })
            .then(function () {
                return self.skipWaiting();
            })
    );
});

self.addEventListener("activate", function (event) {
    event.waitUntil(
        caches
            .keys()
            .then(function (cacheNames) {
                return Promise.all(
                    cacheNames
                        .filter(function (cacheName) {
                            return cacheName !== CACHE_NAME;
                        })
                        .map(function (cacheName) {
                            return caches.delete(cacheName);
                        })
                );
            })
            .then(function () {
                return self.clients.claim();
            })
    );
});

function isLocalDevelopment() {
    return (
        self.location.hostname === "localhost" ||
        self.location.hostname === "127.0.0.1"
    );
}

async function networkFirst(request) {
    const cache = await caches.open(CACHE_NAME);

    try {
        const response = await fetch(request);

        if (response.ok) {
            await cache.put(request, response.clone());
        }

        return response;
    } catch (error) {
        const cachedResponse = await cache.match(request);

        if (cachedResponse) {
            return cachedResponse;
        }

        throw error;
    }
}

self.addEventListener("fetch", function (event) {
    const request = event.request;
    const url = new URL(request.url);

    if (request.method !== "GET" || url.origin !== self.location.origin) {
        return;
    }

    if (isLocalDevelopment()) {
        event.respondWith(fetch(request));
        return;
    }

    event.respondWith(networkFirst(request));
});
