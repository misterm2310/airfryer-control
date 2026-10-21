// 📱 Airfryer Control – Speicher nur für das Programm (damit die App schnell startet).
// Die Fritteuse selbst funktioniert nur mit Netz: Befehle werden bewusst NICHT gemerkt und später gesendet.
const CACHE = "airfryer-control-app-__AC_VERSION__";
const FILES = [
  "./", "manifest.webmanifest", "icon-192.png", "icon-512.png",
  "/airfryer_control_files/airfryer-control-card.js?v=__AC_VERSION__",
  "/airfryer_control_files/mister-m.webp?v=__AC_VERSION__",
  "/airfryer_control_files/icon.png?v=__AC_VERSION__",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => Promise.allSettled(FILES.map((f) => c.add(f)))).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith("airfryer-control-app-") && k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// Erst das Netz fragen (dann ist alles aktuell); ohne Netz das Gespeicherte nehmen.
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  const ours = url.pathname.startsWith("/airfryer_control/app/") || url.pathname.startsWith("/airfryer_control_files/");
  if (e.request.method !== "GET" || url.origin !== location.origin || !ours || url.pathname.endsWith("sw.js")) return;
  const lookup = () => caches.match(e.request).then((r) => r || caches.match(e.request, { ignoreSearch: true }))
    .then((r) => r || (url.pathname.startsWith("/airfryer_control/app/") ? caches.match("./") : undefined));
  const net = fetch(e.request).then((resp) => {
    // Eine Anmeldeseite vom fremden WLAN (HTML statt Programm) darf nie gespeichert oder ausgeliefert werden
    if (/\.(js|webp|png)$/.test(url.pathname) && /text\/html/.test(resp.headers.get("content-type") || "")) throw new Error("html");
    if (resp.ok && resp.type === "basic" && !resp.redirected) {
      const copy = resp.clone();
      caches.open(CACHE).then((c) => c.put(url.pathname === "/airfryer_control/app/" || url.pathname === "/airfryer_control/app/index.html" ? "./" : e.request, copy)).catch(() => {});
    }
    return resp;
  });
  const guarded = net.catch(() => lookup().then((r) => r || new Response("offline", { status: 503 })));
  const slow = new Promise((res) => setTimeout(() => lookup().then((r) => res(r || null), () => res(null)), 4000));
  e.waitUntil(net.catch(() => {}));
  e.respondWith(Promise.race([guarded, slow]).then((r) => r || guarded));
});
