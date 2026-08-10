/* Offline support. The app shell is precached; scripture data is cached the
 * first time you open a chapter, so anywhere you've read once stays readable
 * on a plane. API calls to Anthropic are never cached or intercepted. */

const VERSION = "berea-v1";
const SHELL = [
  "./",
  "index.html",
  "style.css",
  "app.js",
  "manifest.webmanifest",
  "icon.svg",
  "data/manifest.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(VERSION)
      .then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  // Anything off-origin (notably the Anthropic API) goes straight to the network.
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        // Refresh in the background so a redeploy is picked up next visit.
        event.waitUntil(
          fetch(request)
            .then((res) => res.ok && caches.open(VERSION).then((c) => c.put(request, res)))
            .catch(() => {})
        );
        return cached;
      }

      return fetch(request)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            event.waitUntil(caches.open(VERSION).then((c) => c.put(request, copy)));
          }
          return res;
        })
        .catch(() => caches.match("index.html"));
    })
  );
});
