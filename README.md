# TeiTraining

Base ejecutable para la aplicación de entrenamiento del club. Las reglas objetivo están en [REQUIREMENTS.md](REQUIREMENTS.md), [ARCHITECTURE.md](ARCHITECTURE.md) y [MVP.md](MVP.md).

## Estado actual

La web permite iniciar sesión, gestionar miembros y grupos, conceder y retirar permisos, planificar temporadas/fases/planes/microciclos/días y publicar sesiones con asignaciones individuales. Antes de publicar muestra los destinatarios autorizados, sin duplicados; si cambian, exige una nueva previsualización.

El entrenador dispone de calendario, planificación, organización y consulta de deportistas. El deportista ve el calendario, el siguiente entreno, los demás entrenos pendientes en un desplegable, recuperación y evolución, y el historial completo en otro desplegable. Desde su calendario puede descargar un archivo `.ics` con sesiones pendientes para importarlo en Google Calendar; las sesiones que ya proceden de Google quedan excluidas por defecto. Los entrenos pueden ser en casa con pasos detallados o en el club; completar una sesión de agua requiere sensaciones, trabajo realizado, lo mejor y lo peor. La recuperación conserva versiones y motivo de las correcciones; solo la consultan su titular y entrenadores autorizados.

La administración permite desactivar membresías conservando el histórico, editar y archivar grupos, retirar y reincorporar deportistas por períodos y revisar acciones auditadas. Cerrar una temporada bloquea nuevas publicaciones vinculadas a sus planes. Los entrenadores solo gestionan sus propios planes.

**El MVP sigue en desarrollo.** El estado verificable y las funciones pendientes están en [IMPLEMENTATION.md](IMPLEMENTATION.md). Esta actualización incorpora bloques/ejercicios, plantillas versionadas, adaptaciones, resultados/borradores/correcciones y seguimiento por fechas reales. También añade invitaciones y recuperación con cola SMTP. Siguen pendientes perfiles/categorías, edición de destinatarios/recurrencias, filtros/evolución completa y preparación operativa para datos reales. La referencia de finalización sigue siendo E1–E7 y A01–A22 de `MVP.md`.

## Arranque local

Los comandos completos y las cuentas de prueba están en [COMMANDS.md](COMMANDS.md).

Para probar las vistas sin Docker puedes usar SQLite. Desde la raíz, instala dependencias y prepara una base local:

```sh
python3 -m venv .venv
.venv/bin/pip install -e 'apps/api[test]'
cd apps/api
DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/alembic upgrade head
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/python -m app.bootstrap admin@example.org 'clave-inicial-larga' 'Mi club'
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/python -m app.demo_seed
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/python -m app.dev_passwords 12345678
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/uvicorn app.main:app --reload
```

Si la cuenta de administrador ya existe, omite `app.bootstrap`. El reset local pone `12345678` a todas las cuentas existentes y se puede repetir. `app.demo_seed` se puede repetir: conserva los datos que ya creó. También añade una jerarquía de planificación y tres registros de recuperación ficticios para la cuenta de deportista, sin sobrescribir registros existentes. La base `apps/api/dev.db` se ignora en Git. En este espacio de trabajo ya está preparada con el grupo de prueba.

Con Docker y PostgreSQL disponibles, el arranque estándar es:

```sh
docker compose up -d db
python3 -m venv .venv
.venv/bin/pip install -e 'apps/api[test]'
cd apps/api
DATABASE_URL=postgresql+psycopg://tei:tei@localhost:5432/tei ../../.venv/bin/alembic upgrade head
APP_ENV=development DATABASE_URL=postgresql+psycopg://tei:tei@localhost:5432/tei ../../.venv/bin/python -m app.bootstrap admin@example.org 'cambia-esta-clave-larga' 'Mi club'
APP_ENV=development DATABASE_URL=postgresql+psycopg://tei:tei@localhost:5432/tei ../../.venv/bin/uvicorn app.main:app --reload
```

En otra terminal:

```sh
cd apps/web
npm ci
npm run dev
```

Abre `http://localhost:5173`. La API está en `http://localhost:8000/api/v1` y su contrato interactivo en `http://localhost:8000/docs`. El ID del club se muestra al crear el administrador; la interfaz lo obtiene automáticamente de su membresía. Para probar el flujo: entra como `admin@example.org` / `12345678` después del reset local; la cuenta también tiene rol de entrenador. Verás **Grupo Demo · Cadete K1** con seis deportistas y seis sesiones, incluida una rutina de estiramientos en casa. Usa **Calendario** para revisar las sesiones y **Organizar entreno** para publicar una nueva. En **Deportistas y grupos** puedes abrir la vista de cualquier deportista autorizado en modo consulta. Para registrar un entreno y responder al feedback, entra como `demo.vista@example.org` / `12345678`. En **Planes y temporadas** puedes explorar la jerarquía y programar sesiones desde un día. En **Administración** se gestionan grupos, bajas y permisos. La cuenta de deportista tiene **Recuperación**, con valoraciones opcionales y correcciones trazables. Los datos de la demo son ficticios.

Si ya tenías la aplicación instalada, detén la API y ejecuta desde `apps/api`:

```sh
DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/alembic upgrade head
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/python -m app.demo_seed
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/python -m app.dev_passwords 12345678
```

Después vuelve a arrancar la API. En esta base local la migración ya está aplicada. Para PostgreSQL, utiliza su `DATABASE_URL`.

`APP_ENV=development` es obligatorio para el alta directa de cuentas y permite la cookie de sesión sin HTTPS en localhost. No uses estas credenciales de ejemplo fuera de un entorno local. En un despliegue real hay que configurar y verificar el correo de invitación/recuperación, HTTPS y las condiciones de privacidad descritas en `MVP.md`.

## Código del front

El punto de entrada es `apps/web/src/main.tsx`; `App.tsx` coordina autenticación y navegación. Las vistas están en `apps/web/src/components/`, las llamadas HTTP en `api.ts`, los tipos en `types.ts` y los estilos en `style.css`. Edita estos archivos fuente. `apps/web/dist/` se genera con `npm run build` y Vite compacta sus archivos para distribución, por eso los recursos de `dist/assets` pueden verse en una sola línea.

## Comprobaciones

```sh
.venv/bin/pytest -q apps/api/tests
cd apps/web && npm run build
```

Las pruebas de integración usan SQLite en memoria. Cubren el flujo de entrenamiento, permisos, planificación y fechas, recuperación y versiones, retirada/reincorporación a grupos, desactivación y publicación con previsualización. Las nuevas pruebas activan claves foráneas. Se ha comprobado la migración, su reversión sobre una copia previa y su reaplicación con SQLite; falta probarla sobre PostgreSQL en un entorno con el servidor disponible. El despliegue de producción y la restauración de copias todavía no se han probado.

## Sincronización automática con Google Calendar

Además del archivo `.ics`, el deportista puede conectar su cuenta de Google y elegir uno de sus calendarios propios desde **Mi entrenamiento → Calendario → Sincronización automática**. Las nuevas sesiones asignadas se ponen en una cola persistente y el proceso de la API las envía y reintenta cada 15 segundos. La app conserva el ID de Google: al editar una sesión pendiente actualiza ese evento y al cancelarla lo elimina. Solo se pueden cambiar sesiones sin entrenos registrados. **Es una sincronización de TeiTraining hacia Google; los cambios hechos solo en Google no se importan.**

Para activarla en local:

1. Crea un proyecto de Google Cloud, habilita Google Calendar API y configura una [pantalla de consentimiento OAuth](https://developers.google.com/workspace/calendar/api/auth). Si está en modo de pruebas, añade la cuenta Google que usarás como usuario de prueba.
2. Crea un cliente OAuth **Aplicación web** con la URI de redirección exacta `http://localhost:8000/api/v1/google-calendar/callback`.
3. Copia `.env.example` a `.env` y configura `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `GOOGLE_RETURN_URL` y una clave estable `GOOGLE_TOKEN_ENCRYPTION_KEY`. Genera la clave con `.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`. `.env` está excluido de Git.
4. En `.env`, usa la `DATABASE_URL` real de tu instalación (para SQLite local: `sqlite+pysqlite:///./dev.db`). Desde `apps/api`, carga el archivo y arranca la API:

   ```sh
   set -a
   source ../../.env
   set +a
   ../../.venv/bin/alembic upgrade head
   ../../.venv/bin/uvicorn app.main:app --reload
   ```

   Después entra como deportista, conecta Google y elige el calendario. `GOOGLE_CALENDAR_SYNC_POLL=1` activa el envío en segundo plano. No cambies la clave de cifrado sin migrar primero los tokens guardados.

La sincronización inicial enlaza los entrenos que ya proceden del calendario principal de la misma dirección de correo, utilizando su ID externo. En la base local de ejemplo se comprobó sobre una copia que enlaza 291 sesiones futuras y no crea duplicados. Si eliges otro calendario, se crearán copias allí. Desconectar detiene los envíos futuros y borra la credencial local; los eventos existentes permanecen en Google.

La integración necesita credenciales OAuth de **tu propio proyecto de Google Cloud**. La conexión de Google Calendar disponible para este asistente no configura automáticamente las credenciales de la aplicación web. El flujo externo real no se ha probado todavía porque el repositorio no contiene esas credenciales; las pruebas usan respuestas simuladas de Google. En producción usa HTTPS y revisa las condiciones de publicación/consentimiento de Google.


## Nuevos flujos y preparación del piloto

En **Organizar entreno**, usar la biblioteca y el editor de bloques; previsualizar antes de publicar. En la ficha del deportista, adaptar una pendiente futura con motivo. El deportista puede guardar un borrador, registrar medidas específicas y corregir desde el historial. **Seguimiento y rendimiento** separa carga, cumplimiento, series y tests. La administración invita por correo y muestra el estado de entrega; configurar las variables SMTP de `.env.example`.

Antes de arrancar con el nuevo esquema, aplicar `alembic upgrade head` desde `apps/api`, con la `DATABASE_URL` del entorno de prueba. No se ha aplicado la migración a la base local existente durante esta entrega. Las nuevas revisiones son `c621prescription` y `c622accounts`.

El despliegue, correo real, retención y condiciones de menores aún están pendientes. [OPERATIONS.md](OPERATIONS.md) describe copias/restauración, configuración y puertas que siguen bloqueando datos reales. El MVP no se declara terminado; consultar [IMPLEMENTATION.md](IMPLEMENTATION.md).
