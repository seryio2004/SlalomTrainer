# TeiTraining

Base ejecutable para la aplicación de entrenamiento del club. Las reglas objetivo están en [REQUIREMENTS.md](REQUIREMENTS.md), [ARCHITECTURE.md](ARCHITECTURE.md) y [MVP.md](MVP.md).

## Estado actual

Esta primera entrega permite iniciar sesión, crear cuentas de prueba, crear grupos manuales, autorizar a un entrenador sobre grupos o deportistas, publicar una sesión común con asignaciones individuales, registrar estado/duración/RPE y consultar recuentos y carga conocida. La API comprueba club y rol, mantiene una copia de la prescripción en cada asignación y usa una migración inicial explícita. La web separa un menú de entrenador (calendario, organización y deportistas) de la vista del deportista (calendario, siguiente entreno, historial y señal visual de fatiga). Admite sesiones en casa con pasos detallados y sesiones en el club; al completar una sesión de agua pide sensaciones, trabajo realizado, lo mejor y lo peor.

**Es un primer recorrido de desarrollo, todavía no el MVP ni una versión apta para datos reales de menores.** Faltan invitaciones y recuperación de contraseña, auditoría, desactivación desde la interfaz, jerarquía temporada→fase→plan→microciclo→día, gestión completa de grupos y categorías, plantillas, adaptaciones, revisiones de prescripción, resultados detallados por disciplina, recuperación diaria, estadísticas completas, exportación/eliminación y operación de producción. La PWA tiene manifest e icono; aún no tiene service worker para caché estática. La creación directa de cuentas con contraseña está bloqueada fuera de `APP_ENV=development`.

El siguiente tramo debe implementar primero la jerarquía de planes, los destinatarios por categorías/grupos y las revisiones de prescripción, seguido de adaptaciones y resultados por tipo. La referencia para dar por terminado el producto inicial son E1–E7 y A01–A22 de `MVP.md`.

## Arranque local

Para probar las vistas sin Docker puedes usar SQLite. Desde la raíz, instala dependencias y prepara una base local:

```sh
python3 -m venv .venv
.venv/bin/pip install -e 'apps/api[test]'
cd apps/api
DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/alembic upgrade head
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/python -m app.bootstrap admin@example.org 'cambia-esta-clave-larga' 'Mi club'
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/python -m app.demo_seed
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/uvicorn app.main:app --reload
```

Si la cuenta de administrador ya existe, omite `app.bootstrap`. `app.demo_seed` se puede repetir: conserva el grupo y las sesiones que ya creó. La base `apps/api/dev.db` se ignora en Git. En este espacio de trabajo ya está preparada con el grupo de prueba.

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

Abre `http://localhost:5173`. La API está en `http://localhost:8000/api/v1` y su contrato interactivo en `http://localhost:8000/docs`. El ID del club se muestra al crear el administrador; la interfaz lo obtiene automáticamente de su membresía. Para probar el flujo: entra como `admin@example.org` / `cambia-esta-clave-larga`; la cuenta también tiene rol de entrenador. Verás **Grupo Demo · Cadete K1** con seis deportistas y seis sesiones, incluida una rutina de estiramientos en casa. Usa **Calendario** para revisar las sesiones y **Organizar entreno** para publicar una nueva. En **Deportistas y grupos** puedes abrir la vista de cualquier deportista autorizado en modo consulta. Para registrar un entreno y responder al feedback, entra como `demo.vista@example.org` / `DemoVista2026!`. Los datos de la demo son ficticios.

`APP_ENV=development` es obligatorio para el alta directa de cuentas y permite la cookie de sesión sin HTTPS en localhost. No uses estas credenciales de ejemplo fuera de un entorno local. En un despliegue real hay que implementar primero la invitación segura, HTTPS y las condiciones de privacidad descritas en `MVP.md`.

## Código del front

El punto de entrada es `apps/web/src/main.tsx`; `App.tsx` coordina autenticación y navegación. Las vistas están en `apps/web/src/components/`, las llamadas HTTP en `api.ts`, los tipos en `types.ts` y los estilos en `style.css`. Edita estos archivos fuente. `apps/web/dist/` se genera con `npm run build` y Vite compacta sus archivos para distribución, por eso los recursos de `dist/assets` pueden verse en una sola línea.

## Comprobaciones

```sh
.venv/bin/pytest -q apps/api/tests
cd apps/web && npm run build
```

La prueba API usa SQLite en memoria para verificar el flujo, los permisos, las indicaciones en casa, el feedback de agua y la señal de fatiga. La migración se ha comprobado con SQLite; falta probarla sobre PostgreSQL en un entorno con el servidor disponible. El despliegue de producción y la restauración de copias todavía no se han probado.
