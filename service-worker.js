const CACHE_NAME = "ark-terminal-v25";

const APP_SHELL = [
    "./",
    "./index.html",
    "./style.css",
    "./script.js",
    "./real-account-home.js",
    "./real-account-home.css",
    "./predict/broker/real-account-home-view-v1.js",
    "./predict/broker/readonly-broker-normalizer.js",
    "./manifest.json",
    "./discovery/index.html",
    "./discovery/style.css",
    "./discovery/script.js",
    "./predict/index.html",
    "./predict/style.css",
    "./predict/script.js",
    "./predict/cloud-sync.html",
    "./predict/cloud/cloud-sync-page.js",
    "./predict/cloud/cloud-sync-controller.js",
    "./predict/cloud/cloud-sync-client.js",
    "./predict/cloud/prediction-cloud-repository.js",
    "./predict/cloud/automatic-cloud-sync.js",
    "./predict/cloud/learning-cloud-repository.js",
    "./predict/cloud/learning-cloud-auto-sync.js",
    "./predict/trading/intraday-market.js",
    "./predict/trading/short-term-core.js",
    "./predict/trading/intraday-trading-decision.js",
    "./predict/trading/intraday-trading-ui.js",
    "./predict/trading/ai-trade-gate.js",
    "./predict/trading/trade-memory.js",
    "./predict/trading/intraday-paper-backtest.js",
    "./predict/trading/intraday-backtest-modes.js",
    "./predict/trading/intraday-paper-backtest-ui.js",
    "./predict/global-evaluation.js",
    "./predict/global-evaluation-ui.js",
    "./predict/performance.html",
    "./predict/performance.css",
    "./predict/performance.js",
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
