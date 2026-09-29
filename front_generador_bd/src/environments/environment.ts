const wsPort = 8000;
const portJava = 7001;
export const environment = {
    production: false,
    wsPort,                // 👈 puerto configurable
    wsPath: '/ws/canvas/',        // 👈 path base
    //endpoint_python: `http://127.0.0.1:${wsPort}/`,
    //endpoint_python: `http://ec2-34-228-19-253.compute-1.amazonaws.com:${wsPort}/`,
    endpoint_python: `https://django-sw1.fournext.me/`,
    WebSocket_python: `django-sw1.fournext.me`,
    //endpoint_java: `http://127.0.0.1:${portJava}/`
    //endpoint_java: `http://ec2-34-228-19-253.compute-1.amazonaws.com:${portJava}/`
    endpoint_java: `https://spring-sw1.fournext.me/`,
    // Puerto del generador Spring para BackendGeneratorService. 7001 = acceso
    // directo (docker-compose.app.yml publica ese puerto). Vacío/null cuando
    // se sirve detrás de un reverse proxy de un solo origen (usa /generate relativo).
    springPort: 7001
};
