# Estado de implementación del MVP

Este documento describe el código disponible. No reduce el alcance de [MVP.md](MVP.md) ni sustituye sus criterios de aceptación. La aplicación se orienta al uso del club: no se ha añadido facturación ni monetización.

## Entrega actual

| Área | Disponible | Pendiente para completar el MVP |
| --- | --- | --- |
| E1 · Base y acceso | Sesión con cookies, CSRF, aislamiento por club y rol; alta de desarrollo; desactivación/reactivación de membresías; permisos directos y por grupo; auditoría de las nuevas operaciones. | Correo SMTP real y límites del proxy pendientes; auditoría del resto de operaciones sensibles. Invitación/activación, recuperación, revocación tras reset y cambio de roles están implementados en esta actualización. |
| E2 · Planificación | Crear temporada, fase, plan, microciclo y día; planes simultáneos; validación de fechas; cierre de temporada; archivo de plan; gestión de grupos con períodos; previsualización grupo/personas. | Perfiles completos, categorías de temporada, modalidades y filtros combinados; edición de períodos existentes y configuración del club. |
| E3 · Prescripción | Publicación con destinatarios sin duplicados, copia individual de prescripción; indicaciones detalladas en casa; vinculación opcional a un día de plan. | Catálogo de ejercicios, bloques/objetivos/medidas y plantillas propias versionadas están implementados; falta validar el recorrido visual completo. |
| E4 · Adaptaciones | Asignaciones individuales independientes, que no desaparecen al cambiar de grupo. | Adaptaciones versionadas con original conservado están implementadas. Siguen pendientes duplicación de planes, sustituciones y recurrencias; mover entre días de plan. |
| E5 · Registro | Estado, duración, RPE, sensación y molestias; reflexión de agua; reintento idéntico del envío existente. | Series y medidas específicas, borradores, correcciones versionadas y presentación con preguntas cortas están implementados. Falta validar el modo infantil con usuarios y las pantallas en móvil. |
| E6 · Seguimiento | Recuentos y carga conocida por sesión, historial, indicador orientativo de fatiga; recuperación diaria opcional con versiones, consulta temporal y acceso autorizado. | Carga por fecha real, agregados diarios/semanales, comparación con cobertura, filtros básicos e históricos separados de fuerza/tests están implementados. Faltan filtros de categoría/sexo/modalidad/temporada/fase, catálogo de protocolos de test independiente y gráficas de evolución de rendimiento. |
| E7 · Piloto | Manifest e icono; exportación `.ics` y sincronización OAuth unidireccional con cola y reintentos; compilación del front y pruebas API; migraciones SQLite verificadas. | Caché estática PWA, exportación deportiva propia JSON y copia/restauración SQLite están implementadas. Faltan E2E/navegador, accesibilidad, exportación/eliminación integral, PostgreSQL, despliegue y restauración operativa con copias automatizadas. |

## Cómo comprobar lo nuevo

1. Entrar como `admin@example.org` y abrir **Planes y temporadas**. La demo muestra temporada, fase, plan, microciclos y días. Crear un segundo plan no modifica el primero.
2. Abrir **Programar entreno** desde un día. Elegir grupo y deportistas adicionales, previsualizar y confirmar. Una persona seleccionada por ambas vías recibe una sola asignación.
3. En **Administración**, crear/editar/archivar grupos, incorporar/retirar deportistas y gestionar permisos. La retirada cierra un período; una reincorporación abre otro. Las asignaciones previas permanecen.
4. Entrar como `demo.vista@example.org` / `12345678` y abrir **Mi entrenamiento**. Debajo del siguiente entreno, desplegar los pendientes; consultar recuperación, evolución y fatiga; al final, desplegar todos los entrenamientos. Elegir un día de recuperación, guardar valoraciones opcionales y corregir indicando motivo.
5. Desde la cuenta del entrenador autorizado, abrir la vista de ese deportista y consultar recuperación en modo lectura. El rol administrativo por sí solo no concede acceso a estos registros privados.

## Reglas y límites actuales

- La pertenencia a un grupo usa intervalos `[entrada, salida)`, con fechas locales del club. La salida retira inmediatamente el permiso derivado del grupo. Un permiso directo o un segundo grupo autorizado puede mantener acceso.
- Solo puede existir una temporada activa por club. Se puede preparar planificación en borrador. Una temporada cerrada queda para consulta; no se puede reabrir desde esta entrega.
- Los planes pertenecen al entrenador que los crea. No hay todavía planes compartidos ni transferencia de autoría.
- Se mantienen sesiones independientes, sin `plan_day_id`, para conservar el flujo existente. Cerrar una temporada bloquea publicaciones vinculadas a ella; no afecta a sesiones sin vínculo.
- La hora de publicación se introduce en la zona del navegador, indicada en el formulario. El backend comprueba la fecha del día de plan en la zona del club. Aún no hay edición de la zona horaria ni recurrencias.
- La previsualización valida destinatarios con la misma resolución que la publicación. El front envía los IDs revisados; si el conjunto ha cambiado, la API responde con conflicto antes de crear asignaciones.
- Recuperación admite sueño, fatiga, agujetas, motivación y energía de 1 a 5, dolor de 0 a 10, zona y comentario. Los campos no contestados se conservan nulos. Cada consulta admite hasta 366 días; por defecto muestra los últimos 90 días.
- Corregir recuperación requiere la versión vigente y un motivo. Conserva valores anteriores, autor y fecha. La auditoría administrativa solo expone metadatos, no las valoraciones privadas.
- La barra de fatiga conserva su cálculo anterior a partir de entrenos y feedback; los registros diarios se consultan por separado.
- La baja de membresía bloquea acceso al club en cada petición y conserva los datos. La creación directa de cuentas con contraseña sigue limitada a desarrollo; la administración web usa invitaciones.

## Validación realizada

- `pytest -q apps/api/tests`: 5 pruebas de integración aprobadas; incluyen aislamiento entre clubes, roles, fechas, planes simultáneos, cierre, versiones de recuperación, revocación y reincorporación, conservación de asignaciones y conflictos de destinatarios.
- `npm --prefix apps/web run build`: comprobación TypeScript y compilación Vite aprobadas.
- Migraciones hasta `8d9c211a40b2`: subida, bajada hasta la revisión previa y nueva subida sobre copia de SQLite; `alembic check` sin diferencias.
- Demo ejecutada dos veces sobre copia de desarrollo; acceso a planificación y recuperación comprobado mediante API con las dos cuentas locales.
- Las migraciones y datos ficticios están aplicados en `apps/api/dev.db`. Copia previa de esta actualización: `/tmp/tei-before-planning.db` (temporal, no sustituye una copia permanente).
- No se ha verificado visualmente con navegador ni ejecutado PostgreSQL. Las pruebas de integración no equivalen a aceptar todos los escenarios A01–A22.

La reversión de la migración de períodos se bloquea si ya existen reincorporaciones: la estructura anterior no puede conservar varios períodos. En ese caso se debe restaurar una copia previa, nunca borrar historial para forzar la bajada.

## Importación puntual de calendario personal

`app.calendar_import` acepta un manifiesto JSON revisado con `events` (`id`, `title`, `start`, `end`, `description`). Solo funciona con `APP_ENV=development`: crea o reutiliza una cuenta deportista, un grupo personal, un plan por año, días y asignaciones. La clave de cada sesión se deriva del grupo, título y hora, de forma que repetir el mismo manifiesto no duplica entrenamientos. Las sesiones en casa toman las indicaciones detalladas de la descripción.

El manifiesto local se guarda en `apps/api/private/`, excluido de Git. Es una **importación puntual**; cambios futuros en Google Calendar requieren obtener y revisar un nuevo manifiesto. No hay sincronización automática ni modificación del calendario de Google.

## Exportación a Google Calendar

En **Mi entrenamiento → Calendario → Exportar a Google Calendar**, el deportista descarga sus asignaciones pendientes como `.ics`. El período por defecto va desde la fecha local del club hasta 365 días después; se puede escoger otro de hasta 366 días. El archivo incluye su prescripción individual, fecha, duración y lugar. La API solo permite exportar las asignaciones propias, usa caché desactivada y registra el acto sin copiar instrucciones en la auditoría.

Las sesiones cuyo origen es Google Calendar se excluyen por defecto, para evitar volver a importar el mismo contenido. Una casilla permite incluirlas cuando el destino sea otro calendario. Esta descarga es puntual y requiere importar el archivo en Google Calendar: no crea una conexión OAuth ni sincroniza cambios posteriores.

## Google Calendar automático

La conexión es individual por deportista y requiere OAuth de un proyecto Google Cloud configurado en el servidor. El token de actualización se cifra con Fernet; el cliente no recibe tokens. El usuario elige entre calendarios propios, puede pedir una reconciliación y desconectar. La publicación de sesión y la cola de envío se guardan en la misma transacción. El proceso de la API revisa la cola cada 15 segundos, usa ID de evento estable y guarda correspondencia asignación ↔ evento de Google. La reconciliación de origen Google enlaza los eventos del calendario principal cuando su ID coincide con el correo del deportista.

El alcance actual es **TeiTraining → Google Calendar**. No hay lectura de cambios desde Google. El entrenador puede editar o cancelar sesiones cuyos deportistas aún no hayan registrado el entreno; la edición actualiza el evento vinculado y la cancelación lo retira de Google mediante la misma cola persistente. Los destinatarios de una sesión publicada permanecen fijos. La importación puntual `.ics` sigue disponible. La integración real requiere credenciales OAuth externas y no se ha probado con la API real; la batería automatizada usa simulación y verifica reintento, idempotencia, permisos y enlace de eventos previos.

## Interfaz de entrenamiento y gráficos de carga

La vista del deportista conserva el calendario y el siguiente entrenamiento arriba, los pendientes en un desplegable y el historial completo al final. Las sesiones usan filas compactas que despliegan instrucciones y feedback. Recuperación muestra un resumen diario y un formulario desplegable; la consulta del entrenador sigue siendo de solo lectura.

El seguimiento incluye gráficos SVG adaptables de carga y duración para 7, 28 y 84 días (este último agrupa por semanas), con separación entre casa y club y distribución por modalidad. Utiliza solo sesiones completadas o parciales, excluye descansos y fechas futuras, y diferencia valores ausentes de ceros registrados. La carga procede del valor de la API: minutos realizados × RPE. Los registros se agrupan por fecha programada en la zona del navegador, ya que no existe una fecha independiente de realización. No se añaden estimaciones de riesgo ni datos ficticios.

Las barras permiten consultar detalles con ratón, teclado o pulsación; los mismos datos están disponibles en una tabla desplegable. La barra de fatiga mantiene su representación cualitativa sin números. La presentación mantiene azules, esquinas redondeadas y controles adaptados a pantallas estrechas.

Validación de esta actualización: `npm --prefix apps/web run test:load` (5 pruebas de agregación, datos ausentes, cambio horario y límites de fechas) y `npm --prefix apps/web run build` aprobados. La comprobación visual en Chrome queda pendiente porque no hay un navegador de pruebas disponible en esta sesión.

## Realizar entreno

La cuenta de deportista dispone de **Realizar entreno** en el menú y de un botón en cada sesión pendiente. La vista muestra la prescripción y permite cambiar entre sesiones. Al pulsar **Empezar entreno** se abre la pantalla de ejecución y se inicia el primer ejercicio cronometrado. En sesiones fuera del agua, la guía lee tanto los pasos individuales como las instrucciones generales. El formato recomendado es `Ejercicio | series x repeticiones o segundos | descanso`; por ejemplo, `Sentadilla | 3x12 reps | descanso 60s` o `Plancha | 3x30s | descanso 20s`. También separa ejercicios escritos como `Sentadilla 3x8, remo 3x10; descanso 90s`. Cronometra cada serie temporal y activa los descansos prescritos entre series; en series por repeticiones, el deportista confirma cuándo termina cada serie y la guía inicia el descanso. Si el paso no indica series, tiempo o descanso, no inventa esos valores y permite avanzar manualmente. En sesiones de agua muestra los pasos para avanzar manualmente.

El cronómetro calcula el tiempo restante con el reloj del navegador y continúa aunque la pestaña quede en segundo plano. El modo muestra el feedback existente al acabar; recorrer los pasos no marca automáticamente la sesión como completada. Los contadores se reinician al cambiar de sesión o salir de esta vista y el progreso no se guarda en el servidor.


## Prescripción → adaptación → ejecución → seguimiento (actualización)

- **Prescripción:** editor de bloques y ejercicios con orden/IDs estables, objetivo y campos opcionales de series, repeticiones, kg, segundos, metros, descanso, RIR, RPE objetivo, lado, intensidad, zonas y convención de carga. Objetivos específicos de agua, carrera, ergómetro y test. Catálogo del club archivable; plantillas del entrenador con revisiones, duplicación, reutilización y guardado desde el formulario de sesión. Se conservan las sesiones de texto anteriores.
- **Adaptación:** desde la ficha de un deportista, el entrenador responsable autorizado modifica bloques/ejercicios o medidas de su sesión futura con motivo y versión. Conserva original y revisiones; las otras asignaciones permanecen intactas. Un borrador o envío bloquea cambios de prescripción. Revisar la base común exige resolver adaptaciones; cancelar una pendiente conserva las adaptaciones.
- **Registro:** guardar borrador en servidor, continuar, enviar y corregir con motivo. `version` es obligatoria en los contratos de ejecución; clientes antiguos deben recargar y enviar la versión de asignación. Reintentar un envío idéntico no duplica; versiones antiguas dan conflicto. Cada corrección guarda autor, fecha y estado anterior en la transacción auditada. Las series añadidas se etiquetan, sin cambiar lo prescrito. Descanso y omisión no llevan duración activa ni RPE.
- **Medidas:** series con reps/kg/segundos/metros/lado/RIR/RPE/comentario; carrera con distancia/tiempo/desnivel; ergómetro/tests con modelo/resistencia/potencia/cadencia/protocolo/versiones; medidas genéricas con unidad. El protocolo de test es un snapshot configurable de texto y versión, no todavía un catálogo independiente de definiciones/protocolos. Los campos sin respuesta son nulos.
- **Seguimiento:** carga por fecha local real declarada, días y semanas lunes–domingo, cobertura, RPE con muestra, molestias y cumplimiento por fecha prevista. El filtro de varios grupos usa contexto congelado y no duplica asignaciones. La media de carga es por deportista con carga conocida y muestra su denominador. Una semana con cobertura incompleta no presenta diferencia de carga como comparación suficiente. Los registros antiguos sin fecha real se conservan y se identifican fuera de estos agregados; nunca se les atribuye la fecha prevista como realización. Fatiga usa también fechas reales. Fuerza separa ejercicio, reps, lado, medición y convención de carga; volumen externo solo con kg/reps comparables. Tests separan distancia/protocolo/versión/modelo/resistencia y muestran condiciones incompletas como no comparables.
- **Acceso:** invitaciones, aceptación de enlace de un solo uso, recuperación, revocación de sesiones tras recuperación y edición de roles con protección del último administrador. Cola SMTP cifrada con reintentos y estado de invitaciones en administración; no se devuelve el token en API. Se añade exportación JSON de perfil/membresía, asignaciones/resultados/revisiones y recuperación propios, además de plantillas propias del entrenador. Excluye credenciales y resultados de compañeros; aún no equivale a resolver todo el procedimiento integral de privacidad.
- **Operación:** caché PWA exclusivamente estática y herramienta de backup/restore SQLite que rechaza cualquier destino existente, comprueba integridad/claves y solo imprime recuentos. Ver [OPERATIONS.md](OPERATIONS.md). Despliegue, correo real, retención, copias y condiciones de menores están pendientes por decisión del club. **No usar datos reales todavía.**

Migraciones nuevas: `c621prescription` y `c622accounts`. Aplicarlas al entorno de prueba con Alembic; esta entrega no ha migrado ni reiniciado `apps/api/dev.db`. La bajada de `c621prescription` elimina resultados estructurados, fechas y revisiones añadidos; una reversión después de utilizarlos pierde datos y exige copia previa.

Comprobaciones de la actualización: suite API sobre SQLite, build TypeScript/Vite, pruebas de carga, migración desde la revisión previa conservando un registro sintético con campos nulos, `alembic check`, backup/restore y bajada/subida únicamente sobre copia sintética. La conexión del navegador no pudo inicializarse en esta sesión; no se declara revisión visual, Safari/Chrome ni E2E. SMTP y Google se comprueban con simulación. PostgreSQL y la operación del entorno real siguen sin verificar. E1–E7 y A01–A22 no están aceptadas en conjunto.
