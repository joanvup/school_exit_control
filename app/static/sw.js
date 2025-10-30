const CACHE_NAME = 'school-exit-control-v1';
// Lista de archivos para cachear.
const urlsToCache = [
    '/',
    '/static/js/scanner.js',
    '/static/audio/success.mp3',
    '/static/audio/error.mp3',
    'https://cdn.tailwindcss.com',
    'https://unpkg.com/html5-qrcode/html5-qrcode.min.js',
    'https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js'
];

// Evento 'install': Se dispara cuando el service worker se instala.
self.addEventListener('install', event => {
  console.log('Service Worker: Instalando...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Service Worker: Abriendo caché y añadiendo archivos principales');
        return cache.addAll(urlsToCache);
      })
      .then(() => self.skipWaiting()) // Forzar la activación del nuevo SW
  );
});

// Evento 'activate': Se dispara cuando el service worker se activa.
// Limpia cachés antiguos.
self.addEventListener('activate', event => {
  console.log('Service Worker: Activando...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            console.log('Service Worker: Limpiando caché antiguo', cache);
            return caches.delete(cache);
          }
        })
      );
    })
  );
  return self.clients.claim();
});

// Evento 'fetch': Intercepta las solicitudes de red.
// Estrategia: "Cache first" para los recursos cacheados.
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Si el recurso está en el caché, lo devolvemos desde allí.
        if (response) {
          return response;
        }
        // Si no, lo pedimos a la red.
        return fetch(event.request);
      }
    )
  );
});