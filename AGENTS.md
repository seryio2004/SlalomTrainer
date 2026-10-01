# AGENTS.md — TeiTraining

Instrucciones para agentes que trabajen en este repositorio. Se aplican a todo el
proyecto; un `AGENTS.md` en un subdirectorio puede añadir reglas específicas.

## Objetivo y referencias

TeiTraining es una aplicación de entrenamiento para un club, con administración,
planificación, prescripción individual, registro y seguimiento de deportistas.
El MVP sigue en desarrollo: no supongas que una función descrita está implementada.

Antes de modificar un área, consulta las referencias pertinentes:

- `REQUIREMENTS.md`: reglas de producto.
- `MVP.md`: alcance y criterios de aceptación E1–E7 y A01–A22.
- `ARCHITECTURE.md`: diseño objetivo y decisiones de arquitectura.
- `IMPLEMENTATION.md`: estado implementado y carencias conocidas.
- `README.md` y `COMMANDS.md`: funcionamiento y ejecución local.

Contrasta los documentos con el código. Si hay una discrepancia que afecta a la
tarea, explícitala; no reduzcas los requisitos para declarar terminado el MVP.

## Mapa del repositorio

- `apps/api/app/`: FastAPI, SQLAlchemy 2 y Pydantic 2, con Python >= 3.11.
- `apps/api/app/deps.py` y `security.py`: acceso, autenticación y CSRF.
- `apps/api/app/models.py` y `schemas.py`: persistencia y contratos de entrada/salida.
- `apps/api/alembic/versions/`: migraciones de base de datos.
- `apps/api/tests/`: pruebas pytest e integración HTTP.
- `apps/web/src/`: React 19, TypeScript y Vite.
- `apps/web/src/api.ts` y `types.ts`: cliente HTTP y tipos compartidos del front.
- `apps/web/src/components/`: vistas y componentes; `src/training/`: cálculos de entrenamiento.
- `compose.yaml`: PostgreSQL local. SQLite se usa en desarrollo y pruebas.

## Forma de trabajar

1. Revisa el estado de Git y el flujo afectado antes de editar. Conserva los cambios
   existentes del usuario; no los reviertas ni los incluyas en cambios ajenos.
2. Implementa el cambio mínimo que resuelva el problema completo. Sigue los patrones
   existentes y evita refactorizaciones, dependencias o abstracciones sin necesidad.
3. Si cambia un contrato, actualiza API, tipos y consumidores en la misma entrega.
4. Valida el comportamiento afectado y documenta los límites de la comprobación.
5. Actualiza los documentos correspondientes si cambia el uso, el contrato o el
   estado de implementación. No marques como probado lo que solo has inspeccionado.

Resuelve decisiones rutinarias de implementación sin pedir confirmación. Solicita
aclaración cuando falte una decisión de producto que cambie el resultado. No
despliegues ni modifiques servicios externos fuera del alcance autorizado.

## Reglas de dominio que debes conservar

- El aislamiento por club y los permisos se verifican en el servidor en cada
  operación. Un ID recibido del cliente no demuestra pertenencia ni autorización.
- El rol administrativo por sí solo no da acceso a datos privados de recuperación.
  Reutiliza las comprobaciones de acceso existentes.
- La baja de una membresía bloquea acceso y conserva el histórico. La retirada de
  un grupo cierra su período; no elimina asignaciones previas.
- Los períodos de grupo usan intervalos `[entrada, salida)` en la fecha local del
  club. Distingue fechas locales de instantes UTC; evita fechas y horas ambiguas.
- Los planes pertenecen a su entrenador. El cierre de temporada bloquea nuevas
  publicaciones vinculadas; respeta las sesiones independientes existentes.
- Previsualización y publicación deben resolver los mismos destinatarios, sin
  duplicados. Si cambia el conjunto revisado, conserva el conflicto y exige revisarlo.
- Conserva las copias individuales de prescripción y la trazabilidad de correcciones.
  No reescribas el histórico desde una plantilla o un grupo actualizado.
- Los campos opcionales sin respuesta permanecen nulos; no los conviertas en cero.
- Los cálculos de carga deben distinguir datos ausentes de valores válidos y
  mantener las unidades y fórmulas documentadas.

## Seguridad, datos e integraciones

- Conserva la autenticación con cookies y la protección CSRF de las operaciones
  que modifican datos. No relajes permisos para solucionar un fallo de interfaz.
- No incluyas secretos, tokens OAuth, contraseñas o datos personales reales en
  código, pruebas, logs o documentación. Usa `.env.example` para nombres de variables.
- Las herramientas de bootstrap, demo y reset de contraseñas son de desarrollo.
  No las ejecutes sobre una base con datos reales ni como paso de validación habitual.
- La auditoría debe conservar autor, acción y contexto necesarios sin exponer
  valoraciones privadas o credenciales.
- Google Calendar sincroniza de TeiTraining hacia Google. Conserva los IDs externos,
  la cola persistente y los reintentos sin duplicar eventos. No añadas importación
  bidireccional de forma implícita.
- Prueba integraciones externas con respuestas simuladas. Una prueba con mocks
  no demuestra que OAuth o el servicio externo funcionen en un despliegue real.

## Persistencia y migraciones

- Todo cambio de esquema persistente necesita una migración Alembic. No sustituyas
  migraciones por `create_all` en el arranque de la aplicación.
- No reescribas migraciones ya aplicadas; añade una nueva revisión.
- Mantén la compatibilidad prevista con SQLite y PostgreSQL. Una prueba en SQLite
  no demuestra compatibilidad con PostgreSQL.
- Para cambios de esquema, verifica la actualización sobre una base desechable y
  la conservación de datos relevantes. Evalúa la reversión en una copia si procede;
  indica explícitamente las transformaciones que no puedan revertirse sin pérdida.
- Nunca borres bases, reinicies volúmenes ni ejecutes migraciones destructivas sobre
  datos reales sin autorización específica.

## Frontend

- Edita fuentes en `apps/web/src/`; no edites `dist/`, `node_modules/` ni el lockfile
  manualmente. Conserva `package-lock.json` cuando cambien dependencias.
- Mantén TypeScript tipado; evita `any` y supresiones de errores sin justificación.
- Contempla carga, vacío, error y éxito en los flujos que modifiques. Evita envíos
  duplicados y muestra errores que permitan al usuario actuar.
- Usa controles semánticos, etiquetas accesibles, foco visible y navegación por
  teclado. Comprueba las vistas afectadas en móvil y escritorio cuando sea posible.
- Mantén el idioma español y la terminología del club en los textos de interfaz.

## Validación

Comandos desde la raíz, con dependencias instaladas:

```sh
.venv/bin/pytest -q apps/api/tests
npm --prefix apps/web run build
npm --prefix apps/web run test:load
```

Ejecuta las comprobaciones pertinentes: pytest para backend, build para frontend
y `test:load` para cambios en cálculos de carga. No hay un comando de lint ni una
suite general de tests del front definidos en `package.json`; no inventes su resultado.

Añade pruebas de regresión para errores de lógica, permisos, contratos, persistencia
o cálculos. En cambios de acceso cubre al menos un caso permitido y uno denegado,
incluyendo otro club cuando corresponda. Reutiliza fixtures y evita servicios reales.
Para cambios solo de documentación, comprueba rutas, comandos y coherencia; no es
necesario ejecutar toda la suite.

Si una comprobación falla, determina si lo causa tu cambio o un problema previo.
No ocultes el fallo ni amplíes el alcance sin motivo. Si faltan dependencias o un
servicio, informa de qué validación queda pendiente.

## Entrega

Resume qué cambió, por qué y qué comprobaciones ejecutaste con su resultado.
Indica cualquier limitación o trabajo pendiente que afecte al uso. No hagas commits,
push ni publicaciones salvo que la tarea los autorice.
