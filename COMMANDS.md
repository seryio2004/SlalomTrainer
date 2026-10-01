# Comandos para ejecutar TeiTraining en local

Estos comandos usan SQLite en `apps/api/dev.db`; no necesitas Docker. Ejecútalos desde la raíz del repositorio salvo donde se indique otro directorio.

## Primera preparación

```sh
python3 -m venv .venv
.venv/bin/pip install -e 'apps/api[test]'
cd apps/web
npm ci
cd ../..
cd apps/api
DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/alembic upgrade head
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/python -m app.bootstrap admin@example.org 'clave-inicial-larga' 'Mi club'
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/python -m app.demo_seed
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/python -m app.dev_passwords 12345678
```

`app.bootstrap` crea el administrador solo una vez y exige una clave inicial de al menos 12 caracteres. El último comando pone `12345678` en **todas las cuentas existentes de esta base de desarrollo**, incluida la cuenta personal importada si está presente. No cambia la contraseña de tu cuenta de Google. No ejecutes este reset en una base con datos reales.

Si la base y el administrador ya existen, desde `apps/api` basta con:

```sh
DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/alembic upgrade head
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/python -m app.demo_seed
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/python -m app.dev_passwords 12345678
```

## Iniciar la aplicación

Terminal 1, desde la raíz:

```sh
cd apps/api
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///./dev.db ../../.venv/bin/uvicorn app.main:app --reload
```

Terminal 2, desde la raíz:

```sh
cd apps/web
npm run dev
```

Abre <http://localhost:5173/>. La documentación de la API está en <http://localhost:8000/docs>. Deben estar abiertos ambos procesos; si solo arrancas Vite, el inicio de sesión fallará porque no encontrará la API.

## Cuentas locales

Todas las cuentas listadas usan la contraseña `12345678` después del reset anterior.

| Rol | Correo |
| --- | --- |
| Administrador y entrenador | `admin@example.org` |
| Deportista con vista de prueba | `demo.vista@example.org` |
| Deportista de demo | `demo.alba@example.org` |
| Deportista de demo | `demo.bruno@example.org` |
| Deportista de demo | `demo.clara@example.org` |
| Deportista de demo | `demo.diego@example.org` |
| Deportista de demo | `demo.elena@example.org` |

Si ya importaste tu calendario personal, también puedes entrar con el correo usado en esa importación y `12345678`. Esa cuenta solo existe en tu base local. La contraseña de ocho caracteres es para pruebas: el alta normal de usuarios sigue exigiendo un mínimo de doce.

## Comprobaciones opcionales

Desde la raíz:

```sh
.venv/bin/pytest -q apps/api/tests
npm --prefix apps/web run build
```

Para activar la conexión automática con Google Calendar, consulta el apartado correspondiente de [README.md](README.md); requiere credenciales OAuth de tu proyecto de Google Cloud.


## Invitaciones y recuperación

La administración web envía invitaciones en vez de establecer contraseñas de prueba. Configurar SMTP y `MAIL_TOKEN_ENCRYPTION_KEY` / `PUBLIC_WEB_URL` en `.env` como indica [OPERATIONS.md](OPERATIONS.md). Sin correo configurado, la invitación/recuperación devuelve un error explícito; el login existente sigue funcionando. La API procesa la cola en su ciclo de vida. No ejecutar envíos reales como validación: las pruebas simulan SMTP.

La copia/restauración SQLite desechable está en `apps/api/scripts/sqlite_backup.py`; los comandos y los límites de preparación del piloto están en `OPERATIONS.md`. No ejecutar demo ni reset de contraseñas sobre datos reales.
