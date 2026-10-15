const wsPort = 8000;
const portJava = 7001;

// Un mismo build sirve para tres formas de desplegar, sin editar este archivo:
//  - https (túnel de Cloudflare o proxy de un solo origen): /api, /ws y /generate
//    relativos al propio origen, y el WebSocket en el host de la propia página.
//  - http (acceso directo, p. ej. docker compose local o una EC2 sin proxy): Django en
//    :8000 y Spring en :7001 del mismo host que sirve la página.
//  - servidor (SSR): no hay ventana, se usan rutas relativas.
const loc = typeof window !== 'undefined' ? window.location : undefined;
const sameOrigin = !loc || loc.protocol === 'https:';

export const environment = {
    production: false,
    wsPort,                       // puerto directo de Django (solo acceso http)
    wsPath: '/ws/canvas/',        // path base del WebSocket
    endpoint_python: sameOrigin ? '/' : `http://${loc?.hostname}:${wsPort}/`,
    // Vacío = usar el host de la propia página (ver resolveWsHost).
    WebSocket_python: '',
    endpoint_java: sameOrigin ? '/' : `http://${loc?.hostname}:${portJava}/`,
    // Puerto del generador Spring para BackendGeneratorService. null = ruta relativa
    // /generate (detrás de un reverse proxy o túnel de un solo origen).
    springPort: sameOrigin ? null : portJava
};
