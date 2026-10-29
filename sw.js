// 오프라인 캐시: 홈 화면 앱이 인터넷 없이도 마지막으로 본 데이터를 보여줍니다.
const CACHE = "trust-dash-v1";
const SHELL = [
  "./", "index.html", "manifest.webmanifest",
  "icons/icon-192.png", "icons/apple-touch-icon.png", "icons/favicon-32.png",
  "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  // 외부 라이브러리(버전 고정): 캐시 우선
  if (url.origin !== location.origin) {
    e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
    return;
  }
  // 내 사이트 파일(화면·데이터): 네트워크 우선 → 새 버전이 바로 반영되고, 오프라인이면 마지막 사본
  e.respondWith(
    fetch(e.request).then((r) => {
      if (r.ok) {
        const copy = r.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
      }
      return r;
    }).catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
