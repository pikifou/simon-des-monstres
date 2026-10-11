// Simon des Monstres: offline cache. The version changes with every build, which refreshes the cache.
const VERSION = 'simon-39fe2d8bbe';
const FILES = [
 "./",
 "assets/bg-land.webp",
 "assets/bg-port.webp",
 "assets/i-crown.webp",
 "assets/i-note.webp",
 "assets/i-star.webp",
 "assets/i-trophy.webp",
 "assets/m-blue-oops.webp",
 "assets/m-blue-sing.webp",
 "assets/m-blue.webp",
 "assets/m-green-oops.webp",
 "assets/m-green-sing.webp",
 "assets/m-green.webp",
 "assets/m-purple-oops.webp",
 "assets/m-purple-sing.webp",
 "assets/m-purple.webp",
 "assets/m-red-oops.webp",
 "assets/m-red-sing.webp",
 "assets/m-red.webp",
 "assets/m-yellow-oops.webp",
 "assets/m-yellow-sing.webp",
 "assets/m-yellow.webp",
 "fonts/andika-latin-400-normal.woff2",
 "fonts/andika-latin-700-normal.woff2",
 "fonts/grandstander-latin-600-normal.woff2",
 "fonts/grandstander-latin-800-normal.woff2",
 "fonts/grandstander-latin-900-normal.woff2",
 "icons/apple-touch-icon.png",
 "icons/favicon-64.png",
 "icons/icon-192.png",
 "icons/icon-512.png",
 "icons/icon-maskable-192.png",
 "icons/icon-maskable-512.png",
 "index.html",
 "manifest.webmanifest",
 "screens/jeu-paysage.webp",
 "screens/jeu-portrait.webp"
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // The page itself: try the network first (to pick up updates), fall back to the cached copy offline.
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) { const copy = res.clone(); caches.open(VERSION).then((c) => c.put('./', copy)); }
          return res;
        })
        .catch(() => caches.match('./').then((hit) => hit || caches.match('index.html')))
    );
    return;
  }

  // Images, fonts, icons: cache first.
  e.respondWith(
    caches.match(req, { ignoreSearch: true }).then((hit) => hit || fetch(req).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(VERSION).then((c) => c.put(req, copy)); }
      return res;
    }))
  );
});
