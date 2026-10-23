# Despliegue en AWS (EC2) con dominio y HTTPS

Estado verificado el **2026-10-21**. Sitio: **https://diagramador.dev**

## 1. Resumen

Todo corre en **una instancia EC2** (Ubuntu 24.04, 2 vCPU, ~2 GB de RAM) con Docker Compose. **nginx** recibe el tráfico en los puertos 80/443, termina HTTPS (certificado de Let's Encrypt) y reparte hacia los servicios. El dominio lo gestiona name.com (registro `A` hacia la IP pública de la instancia).

```mermaid
%% ea:despliegue-flujo
flowchart LR
  U[Usuarios] -->|HTTPS 443| N[nginx + Let's Encrypt]
  N -->|/| F[angular-app :4200]
  N -->|/api  /ws| D[django :8000]
  N -->|/generate| S[spring-backend :7001]
  D --- R[(redis)]
  D --- P[(postgres)]
  T[Quick Tunnel de Cloudflare<br/>respaldo, nginx :8080] -.-> N
```

El frontend decide sus direcciones al abrirse la página (`front_generador_bd/src/environments/environment.ts`): con HTTPS usa el mismo origen (`/api`, `/ws`, `/generate`), con HTTP directo (solo en local, donde esos puertos están publicados) usa los puertos 8000 y 7001. Por eso un mismo build sirve para el dominio, el túnel y el acceso directo.

## 2. Componentes

| Servicio | Contenedor | Puerto interno | Notas |
|---|---|---|---|
| Frontend Angular SSR | `angular_frontend` | 4000 (publicado como 4200) | Imagen construida desde `front_generador_bd/Dockerfile` |
| API + WebSockets | `django_backend_UML` | 8000 | Django 5, Channels, Daphne |
| Generador | `spring_backend` | 7001 | Spring Boot 3.5, Java 21 |
| Redis | `redis_server` | 6379 | Capa de canales y roles de sala |
| PostgreSQL | `postgres_db` | 5432 (publicado como 5433) | Respaldo de diagramas |
| pgAdmin | `pgadmin` | 80 (publicado como 5050) | Solo administración |

Todos los contenedores tienen política de reinicio `unless-stopped`; Docker y nginx arrancan con la máquina.

## 3. Configuración (nombres de variables, nunca valores)

- `back_generador_bd/.env` (no versionado): `DJANGO_SECRET_KEY`, `DEBUG` (**debe ser `False`**), `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `POSTGRES_*`, `REDIS_*`, `GEMINI_API_KEY`, `GEMINI_MODEL`. El dominio nuevo debe agregarse a las tres listas.
- `.env` en la raíz del repositorio (no versionado): `APP_CORS_ALLOWED_ORIGINS`, orígenes extra separados por comas que Spring **suma** a los suyos (ver `SecurityConfiguration`). Se pasa al contenedor desde `docker-compose.app.yml`.
- Los archivos `.env` nunca se suben a git.

## 4. Desplegar un cambio

El servidor usa `docker-compose` (binario independiente), no `docker compose`. Se actualiza **un servicio a la vez** para no cortar el resto:

1. Respaldar la imagen actual por su identificador (`docker tag <id> <imagen>:antes-<fecha>`).
2. Traer el código: `git pull --ff-only <url-del-repositorio> develop` (si hay ediciones sin guardar, se detiene).
3. Reconstruir solo ese servicio: `docker-compose -f docker-compose.app.yml build <servicio>` (`angular-app` o `spring-backend`). Los contenedores actuales siguen funcionando durante el build.
4. Comprobar que la imagen cambió y reiniciar solo ese servicio: `docker-compose -f docker-compose.app.yml up -d --no-deps <servicio>`.
5. Pruebas de humo (sección 6).

Una instancia pequeña puede tardar varios minutos construyendo el frontend; conviene hacerlo sin usuarios conectados. Al reiniciar `django` se ejecuta `manage.py clear_room_state` (antes de `daphne`): borra de Redis los grupos de salas, así que nadie queda "fantasma"; quienes estaban conectados deben volver a entrar.

### Volver atrás

```bash
docker tag <id-imagen-anterior> <imagen>:latest
docker-compose -f docker-compose.app.yml up -d --no-deps --no-build <servicio>
```

Para el `.env` de Django, restaurar la copia `.env.bak-<fecha>` y recrear el servicio con `up -d --no-deps --force-recreate django`.

## 5. Dominio y HTTPS

1. Dominio registrado en name.com (oferta de GitHub Student Developer Pack, primer año gratis). **La renovación automática está apagada: vence el 2027-10-21** y hay que renovarlo a mano o cambiar de nombre antes.
2. Registro `A` (host vacío) hacia la IP pública de la instancia, TTL 300.
3. Sitio nginx propio para el dominio en el puerto 80 con el mismo reparto de rutas que el del túnel (`/api/`, `/ws/` con Upgrade, `/generate`, `/`).
4. Certificado: `sudo certbot --nginx -d <dominio> --redirect -m <correo> --agree-tos --no-eff-email --non-interactive`. Certbot agrega el servidor 443 y la redirección 301. La renovación la hace el temporizador `certbot.timer`.
5. Si la IP pública de la instancia puede cambiar (apagado y encendido), asignar una IP elástica.

## 6. Pruebas de humo

**Un solo comando:** `scripts/smoke-test.sh [dominio]` ejecuta todas las comprobaciones siguientes (más el cierre de los puertos 4200, 7001 y 8000) y termina con código 0 si todo está bien. Solo lee, no modifica nada. Última corrida: 2026-10-22, todo en orden.

Desde cualquier equipo, sustituyendo el dominio:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://<dominio>/                       # 200
curl -s -w ' %{http_code}\n' https://<dominio>/api/get_backup_uml/00000000-0000-0000-0000-000000000000/   # JSON de error, 404
curl -s -o /dev/null -w '%{http_code}\n' http://<dominio>/                         # 301 hacia https
curl -s -X POST https://<dominio>/generate -H 'Content-Type: application/json' \
  --data '{"classes":[{"id":"c1","name":"Persona","attributes":[{"name":"id","type":"int"}],"methods":[]}],"relationships":[]}' \
  -o /tmp/prueba.zip -w '%{http_code}\n'                                           # 200 y un ZIP
```

WebSocket: una petición HTTP/1.1 con `Upgrade: websocket` a `/ws/canvas/<sala>/` debe responder `101 Switching Protocols`.

## 7. Seguridad y estado conocido

- `DEBUG=False` en Django. Los secretos viven en archivos `.env` fuera de git. La contraseña de PostgreSQL se rotó el 2026-10-22 (la anterior estaba en el historial público de git); para rotarla de nuevo: `ALTER USER … PASSWORD …` dentro del contenedor de Postgres, actualizar `POSTGRES_PASSWORD` en `back_generador_bd/.env` y recrear `django` (`up -d --no-deps --force-recreate django`). Cambiar solo la variable **no** cambia la clave guardada dentro de la base.
- El grupo de seguridad deja abiertos **solo 22, 80 y 443** (los puertos directos 4200, 7001 y 8000 se cerraron el 2026-10-21; todo entra por nginx). **Pendiente recomendado:** limitar el 22 a la IP del administrador (riesgo: si esa IP cambia, hay que editar la regla desde la consola de AWS).
- Redis, PostgreSQL y pgAdmin están publicados en el host (6379, 5433, 5050) pero el grupo de seguridad no los abre al exterior. No abrirlos.
- **Modelo de acceso (decisión de diseño, RF-17):** no hay cuentas; el **código de la sala es la capacidad**. Quien lo conoce puede editar, expulsar (si es host) y leer el historial y la actividad de esa sala. La vista móvil de seguimiento (`/sala/<id>/seguir`) es de **solo lectura por diseño de la interfaz y del servidor para esa conexión**, pero **no es un límite de seguridad**: el enlace contiene el mismo código y quien lo recibe puede abrir la sala como editor. Si algún día hiciera falta separar permisos habría que emitir códigos distintos de lectura y de edición.
- **Atribución a la IA:** las operaciones marcadas `via_ia` las envía el navegador de quien pidió el cambio; el servidor las registra como "IA, a pedido de X" pero no puede demostrar que vengan de una respuesta real de la IA. Es un registro de transparencia, no una auditoría a prueba de manipulación.
- **Costo de la IA:** el servidor limita los pedidos por participante (12/min), por sala (30/min) y en total (60/min), y cada conexión puede cambiar de identidad como máximo 5 veces. El cupo se **reserva antes de llamar al proveedor** y se cuenta aunque el proveedor falle, así que ni los pedidos simultáneos ni una IA caída permiten pasar el tope. El tope global y el de sala no dependen de identificadores elegidos por el cliente. La validación del modelo (`/ws/uml/`) tiene además un tope del servicio: 3 validaciones a la vez y 20 por minuto, y una ráfaga de pedidos de una conexión se reduce a la primera y a una última con el diagrama más reciente.
- **Observadores (vista móvil):** el pedido de estado completo de un observador llega solo al host (no a todos los editores), con un pedido por segundo por sala y como máximo 10 observadores por sala. Estos topes, y los de actividad por conexión, se cuentan **en el proceso**: con varios procesos de Django se multiplicarían por la cantidad de procesos. Hoy corre un solo proceso (daphne).
- **Cambios de la IA:** el servidor rechaza cambios enormes y la interfaz pide confirmación antes de aplicar uno que elimina elementos (el modelo lee el contenido del diagrama, que puede venir de una importación). Cuenta como eliminación lo marcado con `eliminar` y también lo que la respuesta deja fuera de una clase que ya existía (el editor reemplaza los atributos y métodos de una clase existente por los que trae el cambio), comparando con el diagrama que envió el navegador.
- **Ideas de la revisión:** aplicar una idea tiene tres pasos (reservar, confirmar o liberar). La reserva vence a los 150 s si nadie la confirma ni la libera (por ejemplo, se cerró la pestaña), y la confirmación y la liberación se reintentan si falla la red. Quien fue **expulsado** se va sin guardar el respaldo final: su copia pudo quedar atrasada.
- No hay CI/CD ni infraestructura como código: el despliegue es manual y repetible con los pasos de la sección 4.
- El **Quick Tunnel de Cloudflare** sigue como respaldo, pero es un proceso manual (no un servicio) y su dirección cambia si se reinicia. Si cambia, agregarla a `APP_CORS_ALLOWED_ORIGINS` y reiniciar Spring.
