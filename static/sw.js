// Service Worker - SIS LOGÍSTICA 2º BAEP
const CACHE_NAME = 'sis-logistica-v1';
const OFFLINE_URL = '/static/offline.html';

// Recursos essenciais para cache inicial
const PRECACHE_URLS = [
    '/',
    '/dashboard/',
    '/static/img/icon-192.png',
    '/static/img/icon-512.png',
    '/static/manifest.json',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
];

// Instalação: cachear recursos essenciais
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[SW] Pré-cacheando recursos essenciais');
            return cache.addAll(PRECACHE_URLS).catch((err) => {
                console.warn('[SW] Falha ao cachear alguns recursos:', err);
            });
        })
    );
    self.skipWaiting();
});

// Ativação: limpar caches antigos
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => {
                        console.log('[SW] Removendo cache antigo:', name);
                        return caches.delete(name);
                    })
            );
        })
    );
    self.clients.claim();
});

// Estratégia: Network First com fallback para cache
self.addEventListener('fetch', (event) => {
    const request = event.request;

    // Ignorar requisições não-GET (POST de formulários, etc.)
    if (request.method !== 'GET') return;

    // Ignorar requisições do admin
    if (request.url.includes('/admin/')) return;

    // Para navegação (páginas HTML): Network First
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    // Cachear a página para uso offline
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(request, clone);
                    });
                    return response;
                })
                .catch(() => {
                    // Tentar servir do cache
                    return caches.match(request).then((cached) => {
                        return cached || caches.match(OFFLINE_URL);
                    });
                })
        );
        return;
    }

    // Para assets estáticos (CSS, JS, imagens): Cache First
    if (
        request.url.includes('/static/') ||
        request.url.includes('cdn.jsdelivr.net') ||
        request.url.includes('cdnjs.cloudflare.com') ||
        request.url.includes('fonts.googleapis.com') ||
        request.url.includes('fonts.gstatic.com')
    ) {
        event.respondWith(
            caches.match(request).then((cached) => {
                if (cached) return cached;
                return fetch(request).then((response) => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(request, clone);
                    });
                    return response;
                });
            })
        );
        return;
    }

    // Para API/dados: Network Only (sempre buscar do servidor)
    event.respondWith(fetch(request));
});
