const CACHE="envirochem-studio-v2.23-alpha3.2.3-trust-release-patch";
const STATIC=[
  "/",
  "/static/styles.css?v=guided-v2.23-alpha3.2.3-trust-release-patch",
  "/static/app.js?v=guided-v2.23-alpha3.2.3-trust-release-patch",
  "/static/carbamazepine.svg",
  "/static/chemical-placeholder.svg",
  "/static/icon.svg",
  "/static/manifest.webmanifest"
];
self.addEventListener("install",event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(STATIC)).then(()=>self.skipWaiting())));
self.addEventListener("activate",event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener("fetch",event=>{
  if(event.request.method!=="GET"||new URL(event.request.url).pathname.startsWith("/api/")) return;
  event.respondWith(fetch(event.request).then(response=>{
    const copy=response.clone(); caches.open(CACHE).then(cache=>cache.put(event.request,copy)); return response;
  }).catch(()=>caches.match(event.request)));
});
