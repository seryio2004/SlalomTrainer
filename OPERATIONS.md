# Preparación operativa del piloto

Estado: **pendiente de decisiones del club y validación en el despliegue**. No usar datos reales todavía. El código nuevo no sustituye la aceptación E1–E7 / A01–A22.

## Acceso y correo

La administración invita mediante correo. Los enlaces caducan (48 horas para invitación, una hora para recuperación), se usan una vez y solo se conserva su hash. Mientras están en la cola SMTP se cifran con Fernet; tras enviarlos se elimina el texto cifrado. Reenviar invalida el enlace anterior. Recuperar contraseña revoca todas las sesiones de esa cuenta. El servidor verifica membresía/rol/ámbito en cada petición; la baja conserva histórico.

Configurar `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USER`, `SMTP_PASSWORD`, `PUBLIC_WEB_URL` y `MAIL_TOKEN_ENCRYPTION_KEY` fuera del repositorio. SMTP usa STARTTLS. Producción requiere `PUBLIC_WEB_URL` HTTPS. La clave de cifrado se genera con Fernet y debe conservarse mientras haya mensajes pendientes. La API procesa la cola cada 15 segundos, con reintentos; no devuelve enlaces ni credenciales al navegador. Hay que verificar entrega real, caducidad, activación y recuperación en el entorno elegido. Las pruebas usan SMTP simulado.

La cola ofrece entrega al menos una vez: una interrupción entre el envío SMTP y el commit puede repetir el correo con el mismo enlace, que sigue siendo de un solo uso. Un administrador puede reenviar una invitación desde la API `POST /clubs/{club_id}/invitations/{member_id}/resend`; una baja invalida invitaciones pendientes. El proxy debe limitar intentos de login, aceptación y recuperación por IP; recuperación limita además el envío a una vez por cuenta cada cinco minutos.

## Condiciones que debe cerrar el club

Acordar y documentar responsable, ubicación del despliegue, acceso a secretos/copias, retención de datos deportivos y copias, objetivos de recuperación, revisión de solicitudes de datos y condiciones para deportistas menores. Estos puntos están pendientes según la respuesta del club; no se ha inventado una política ni dado por obtenido un consentimiento.

## Despliegue y migración

Usar un origen HTTPS para web y `/api`, con cookies Secure, proxy y límites de acceso. Servir `apps/web/dist` generado por `npm --prefix apps/web run build`; `sw.js` guarda exclusivamente el shell y recursos estáticos. Las rutas `/api/` y peticiones de escritura quedan fuera de la caché persistente. Requiere conexión para datos deportivos.

Instalar dependencias como indica README. Ejecutar Alembic sobre una copia del despliegue antes de aplicar migraciones al destino autorizado. No arrancar con `create_all`. La revisión `c621prescription` conserva las prescripciones/resultados antiguos y deja desconocida la fecha real de ejecución. Su downgrade elimina las nuevas series, fechas y revisiones: no es reversible sin pérdida una vez utilizadas. Conservar copia previa. `c622accounts` añade enlaces y cola de acceso; su downgrade pierde los enlaces pendientes.

## Copias y ensayo de restauración

SQLite, desde la raíz y con destinos nuevos:

```sh
.venv/bin/python apps/api/scripts/sqlite_backup.py backup /ruta/base.db /ruta/copias/tei-fecha.db
.venv/bin/python apps/api/scripts/sqlite_backup.py restore /ruta/copias/tei-fecha.db /tmp/tei-restore-fecha.db
```

Usa la API de backup SQLite para una copia consistente, permisos 0600 y comprobaciones de integridad y claves foráneas. Rechaza sobrescribir cualquier destino. Imprime solo revisión de migración y recuentos, sin filas privadas. Programa el primer comando con el planificador del entorno y la retención acordada, con almacenamiento cifrado y supervisión de fallos; aún no está configurado en un despliegue.

PostgreSQL: usar `pg_dump --format=custom --file=<archivo>` con credenciales en un archivo `.pgpass` privado; restaurar con `pg_restore --exit-on-error --dbname=<base-desechable> <archivo>` sobre una base aislada vacía. No usar `--clean` sobre producción. Aplicar migraciones en esa copia y verificar claves, recuentos, login, publicación, adaptación, ejecución, corrección y aislamiento entre clubes. Este ensayo PostgreSQL queda pendiente de disponer del entorno.

Guardar fecha, revisión Alembic, recuentos, resultados del recorrido y tiempo de recuperación en un acta sin datos personales. Una prueba SQLite no acepta PostgreSQL. Antes de abrir una copia restaurada, revocar sesiones y credenciales OAuth restauradas y reaplicar todas las eliminaciones autorizadas posteriores a la fecha de copia; registrar y verificar el resultado.

## Solicitudes de datos

Existe una exportación deportiva propia JSON sin credenciales ni resultados de compañeros. La exportación/eliminación integral y el registro persistente de solicitudes todavía requieren implementación/verificación. No confundir baja con eliminación ni exportación deportiva `.ics` con exportación personal integral. Revisar también revisiones, snapshots, credenciales, integraciones y copias. Esta carencia sigue bloqueando datos reales; no ejecutar un borrado manual improvisado.

## Puertas pendientes

Antes del piloto: entrega SMTP real; HTTPS/proxy y límites; exportación/eliminación integral; pruebas PostgreSQL y restauración; automatización/supervisión de copias; condiciones y retención del club; E2E y revisión móvil/teclado/Safari/Chrome. La compilación y pruebas sintéticas disponibles no dan por satisfechas estas puertas.
