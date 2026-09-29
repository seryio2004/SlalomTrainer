# Arquitectura de TeiTraining

## 1. Propósito y uso de este documento

Esta es la guía técnica para implementar la plataforma de planificación, ejecución y seguimiento del entrenamiento de piragüismo slalom. Define el dominio, los límites entre módulos, las reglas de integridad y los contratos que deben respetar las pantallas y servicios.

| Documento | Responsabilidad |
| --- | --- |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Capacidades del producto final; referencia funcional. |
| [MVP.md](MVP.md) | Alcance inicial, orden de entrega y criterios de aceptación. |
| `ARCHITECTURE.md` | Decisiones técnicas para construir esas capacidades y permitir su evolución. |

Una capacidad futura descrita aquí no implica implementarla en el MVP. Ante una contradicción, resolverla contra el requisito funcional y actualizar ambos documentos de implementación. Estas decisiones son la base propuesta del proyecto, no una descripción de código ya existente.

### 1.1 Decisiones fundamentales

1. Web autenticada, responsive y mobile-first, instalable como PWA.
2. Un club operativo en el MVP; aislamiento por club en el modelo y en cada operación desde el inicio.
3. Monolito modular con una API y una base de datos. Los módulos comparten transacciones, pero no duplican reglas de negocio.
4. Separación entre plantilla, prescripción común, adaptación individual y ejecución real.
5. Revisiones inmutables de prescripción y correcciones auditadas de resultados.
6. Calendario y base de datos propios como fuente de verdad.
7. Permisos comprobados en backend, también en búsquedas, estadísticas y exportaciones.
8. Carga, recuperación, rendimiento y molestias se muestran por separado. Ninguna recomendación cambia un plan sin intervención de un entrenador autorizado.

### 1.2 Prioridad del club y sostenibilidad

La aplicación se construye para el uso interno del club promotor, sin objetivo de monetizar ese uso. Las decisiones se valoran por su utilidad para entrenadores y deportistas, facilidad de mantenimiento y coste de operación asumible por el club.

Una posible monetización para otros clubes es una opción muy a futuro, sin compromiso ni calendario. No justifica añadir ahora facturación, suscripciones, planes comerciales, límites por tarifa, licencias de pago ni infraestructura comercial. Tampoco se reservan tablas, servicios o abstracciones para esas funciones.

Se mantienen `club_id`, membresías y aislamiento de datos porque permiten ampliar el uso a otros clubes sin mezclar información. Esta preparación técnica no obliga a ofrecer un servicio comercial ni a desplegar administración multi-club en el MVP. La infraestructura se dimensiona para el uso real del club; se amplía cuando exista una necesidad comprobada.

## 2. Plataforma y organización técnica

### 2.1 Stack de referencia

Se conserva el stack definido inicialmente y se concretan sus responsabilidades:

| Capa | Decisión | Responsabilidad |
| --- | --- | --- |
| Web | React, TypeScript y Vite | Interfaz y navegación mobile-first. |
| Navegación | React Router | Rutas autenticadas y espacios por rol. |
| Datos remotos | TanStack Query | Consultas, caché en memoria e invalidación tras cambios. |
| Formularios | React Hook Form y Zod | Ayuda de validación en cliente; el backend vuelve a validar. |
| API | Python, FastAPI y Pydantic | Contratos REST, autenticación y casos de uso. |
| Persistencia | PostgreSQL, SQLAlchemy 2 y Alembic | Integridad relacional, transacciones y migraciones. |
| Contrato | OpenAPI generado por la API | Generación del cliente y tipos TypeScript. |
| Despliegue | Contenedores y proxy con HTTPS | Web y API bajo un mismo origen en el MVP. |
| Móvil futuro | Capacitor | Reutilización del frontend con adaptadores de plataforma. |

Las versiones se fijarán en los manifiestos y archivos de bloqueo al iniciar la implementación. La lógica deportiva vive en el backend; los tipos generados no sustituyen las validaciones ni los permisos. Los contratos Python y TypeScript se conectan mediante OpenAPI, sin asumir que comparten código de validación.

### 2.2 Módulos y límites

| Módulo | Responsabilidades |
| --- | --- |
| Identidad y acceso | Usuarios, credenciales, sesiones, membresías, roles y permisos. |
| Club y estructura deportiva | Perfiles, modalidades, grupos, categorías y autorizaciones de entrenadores. |
| Planificación | Temporadas, fases, planes, microciclos, días y selección de destinatarios. |
| Prescripción | Ejercicios, plantillas, revisiones, sesiones y adaptaciones individuales. |
| Seguimiento | Asignaciones, ejecución, resultados, feedback y recuperación diaria. |
| Análisis | Carga, cumplimiento, históricos, comparativas y señales de seguimiento. |
| Administración | Configuración, auditoría, exportación y eliminación de información. |
| Integraciones futuras | Calendarios externos, notificaciones, salud y sensores. |

Cada módulo separa rutas HTTP, esquemas de entrada/salida, casos de uso, reglas de dominio y persistencia. Las rutas delegan en servicios; no contienen reglas deportivas ni consultas sin autorización. Análisis consume seguimiento y no modifica prescripciones.

### 2.3 Estructura inicial del repositorio

```text
/
├── ARCHITECTURE.md
├── REQUIREMENTS.md
├── MVP.md
├── apps/
│   ├── web/src/
│   │   ├── app/                 # Rutas, proveedores y sesión
│   │   ├── features/            # Funcionalidades por módulo
│   │   ├── components/          # Componentes accesibles compartidos
│   │   └── platform/            # Adaptadores web y, después, nativos
│   └── api/
│       ├── app/core/            # Configuración, autenticación, contexto de club
│       ├── app/modules/         # Módulos de dominio
│       ├── migrations/
│       └── tests/
├── packages/api-client/         # Cliente generado desde OpenAPI
├── tests/e2e/
├── infra/                       # Contenedores, despliegue y restauración
└── docs/decisions/              # Decisiones que cambien esta base
```

No se necesitan microservicios, un bus de eventos externo ni un almacén analítico para el MVP. Las tareas duraderas de exportación o eliminación usan una tabla de trabajos y un proceso ejecutor del mismo backend. Las integraciones futuras podrán reutilizar ese mecanismo.

## 3. Identidad, clubes y autorización

### 3.1 Modelo de identidad

| Entidad | Campos y relaciones esenciales |
| --- | --- |
| `User` | Identidad global: ID, email normalizado único, hash de contraseña, nombre visible y estado. |
| `AuthSession` | Usuario, hash del token, vencimiento, revocación y metadatos mínimos de seguridad. |
| `Club` | Nombre, identificador estable, zona horaria IANA y estado. |
| `ClubMembership` | `club_id`, `user_id`, estado; combinación única por club y usuario. |
| `MembershipRole` | Roles de una membresía: `club_admin`, `coach`, `athlete`; pueden coexistir. |
| `AthleteProfile` | Membresía, nombre deportivo, nacimiento, sexo competitivo, estado deportivo y observaciones restringidas. |
| `CoachProfile` | Membresía y estado del entrenador. |
| `CoachGroupGrant` | Entrenador, grupo, permisos concretos y vigencia. |
| `CoachAthleteGrant` | Autorización directa sobre un deportista, permisos y vigencia. |

La cuenta no equivale al perfil deportivo. Un usuario puede pertenecer a distintos clubes sin compartir automáticamente sus perfiles o datos. Desactivar una membresía retira acceso a ese club; desactivar la cuenta global revoca todas sus sesiones. El administrador de club solo gestiona membresías de su club.

El rol de tutor se incorporará mediante una relación explícita tutor–deportista y permisos propios. No se asumirá parentesco a partir del email ni se reutilizará el acceso del deportista.

### 3.2 Aislamiento obligatorio

Las entidades usan IDs UUID independientes del nombre, timestamps de creación/modificación y versión en recursos editables. Los catálogos se archivan; sus referencias históricas no se eliminan en cascada. Las pertenencias y autorizaciones usan intervalos de vigencia sin solapamientos duplicados para la misma relación.

- Toda tabla con datos de un club incluye `club_id`, incluidas tablas hijas, asignaciones, resultados y auditoría. Las identidades y sesiones globales son excepciones explícitas.
- Las referencias entre entidades del club usan claves foráneas compuestas `(club_id, id)` o restricciones equivalentes que impidan relaciones entre clubes.
- Cada caso de uso recibe un contexto autenticado de usuario, club activo y permisos. El `club_id` enviado por el cliente nunca constituye autorización.
- Consultas, agregaciones, trabajos y exportaciones aplican ese contexto. Un UUID difícil de adivinar no constituye autorización.
- Las claves de caché del cliente incluyen club, usuario y filtros; se vacía la caché al cerrar sesión o cambiar de club.
- Aunque el MVP configure un club real, las pruebas de integración crean dos clubes y demuestran el aislamiento.

### 3.3 Matriz de acceso

| Acción | Deportista | Entrenador | Administrador de club |
| --- | --- | --- | --- |
| Consultar calendario y resultados deportivos | Propios | Deportistas autorizados | Requiere permiso deportivo adicional. |
| Registrar ejecución, feedback y recuperación | Propios | Corrección justificada si dispone del permiso | Requiere permiso deportivo adicional. |
| Crear planes, plantillas y sesiones | No | Dentro de su ámbito | Requiere rol/permiso de entrenador. |
| Adaptar una asignación | No | Deportista autorizado | Requiere permiso deportivo adicional. |
| Gestionar cuentas, grupos, categorías y permisos | No | No | Sí, en su club. |
| Consultar auditoría administrativa | No | No | Sí, con datos sensibles minimizados. |
| Solicitar exportación/eliminación | Propia | Propia | Gestiona solicitudes autorizadas del club. |

Ser administrador no concede por sí solo acceso a molestias o recuperación. Los permisos deportivos se obtienen por grupo o asignación directa y se comprueban en cada petición. Al terminar una autorización, cesa el acceso, también al histórico. Un permiso vigente de consulta individual permite ver el histórico deportivo del deportista dentro del club.

Editar el contenido común, horario o destinatarios de una sesión requiere autorización de planificación sobre todos los afectados. Si el entrenador solo tiene permiso sobre algunos destinatarios, puede adaptar sus asignaciones, pero no modificar la sesión común. Los agregados solo incluyen destinatarios visibles y se identifican como parciales si procede, sin revelar nombres ni cantidades de personas no autorizadas. Las plantillas pertenecen al club: los entrenadores pueden reutilizar las compartidas; su edición requiere autoría o permiso explícito de gestión de biblioteca.

### 3.4 Autenticación del MVP

Alta por administrador mediante invitación de un solo uso y con caducidad; sin registro público. El usuario establece su contraseña. Se incluyen inicio/cierre de sesión, recuperación de contraseña y revocación de sesiones. Las respuestas de recuperación no revelan si existe un email.

La web utiliza token opaco en cookie `HttpOnly`, `Secure` y `SameSite`, con expiración y validación del estado del usuario en servidor. Las mutaciones requieren protección CSRF y validación de origen. Las contraseñas se almacenan con hash adaptativo mediante una biblioteca mantenida; los tokens de invitación, recuperación y sesión se guardan hasheados. No se guardan credenciales en `localStorage`.

Aplicar límites de intentos a autenticación y recuperación. Desactivar membresías o revocar permisos no espera a que expire una caché. Invitaciones y recuperación usan un adaptador de correo transaccional configurable por entorno. El futuro cliente nativo tendrá un adaptador de sesión y almacenamiento seguro, sin trasladar credenciales a componentes de UI.

## 4. Estructura deportiva y planificación

### 4.1 Perfiles, categorías y grupos

| Entidad | Datos y regla principal |
| --- | --- |
| `Discipline` | Catálogo del club con K1 y C1 iniciales; ampliable y archivable. |
| `AthleteDiscipline` | Deportista, modalidad, vigencia y principal opcional; admite varias modalidades. |
| `AgeCategory` | Temporada, nombre y edad mínima/máxima; usa la fecha de referencia de la temporada. |
| `AthleteSeasonCategory` | Categoría asignada en una temporada, criterio usado y motivo de corrección manual. |
| `TrainingGroup` | Nombre, descripción y estado. |
| `TrainingGroupMembership` | Deportista, grupo, inicio y fin de pertenencia. |

La edad se calcula respecto a la fecha configurada para la temporada, no respecto al día de consulta. No se codifican nombres ni reglas federativas. Se validan límites de edad y asignaciones ambiguas; una corrección manual queda auditada. Cambiar temporada o categoría actual no reescribe la clasificación histórica.

Modalidad deportiva (`K1`, `C1`) y tipo de entrenamiento (`water`, `gym`, etc.) son dimensiones distintas. Una sesión indica modalidad concreta o trabajo general; practicar K1 y C1 no duplica una sesión general ni su carga.

### 4.2 Jerarquía completa

```text
Temporada → Fase → Plan → Microciclo/semana → Día → Sesión
```

| Entidad | Contenido mínimo |
| --- | --- |
| `Season` | Nombre, inicio, fin, objetivos, fecha de referencia de edad y estado `draft/active/closed`. |
| `TrainingPhase` | Temporada, nombre configurable, fechas, objetivos y orden. |
| `TrainingPlan` | Fase, nombre, objetivos, estado `draft/active/archived`, entrenador responsable y segmentación. |
| `Microcycle` | Plan, nombre/orden, inicio, fin y objetivos. |
| `PlanDay` | Microciclo y fecha local; único por microciclo y fecha. |
| `WorkoutSession` | Día, horario, responsable, metadatos de calendario y revisión publicada. |

Un plan pertenece a una fase. Para continuar una planificación a través de fases se crean planes enlazados mediante `source_plan_id` al reutilizarlos; no se asigna una sesión a varias fases. Las fases pueden solaparse para grupos distintos. Las fechas de cada hijo deben estar dentro del período de su padre. Un microciclo puede durar más o menos de siete días; las estadísticas semanales usan semanas de calendario.

El MVP permite una temporada activa por club y conserva las cerradas para consulta. Cerrar una temporada bloquea nuevas publicaciones y cambios de planificación; permite completar registros pendientes y corregir resultados de forma auditada. Archivar un plan lo retira de edición sin borrar sus sesiones. Pueden coexistir planes generales, por categoría, sexo, modalidad, grupo o deportista. Una sesión individual sigue perteneciendo a un día de un plan; su formulario puede crear ese contexto mínimo explícitamente.

Duplicar un plan copia estructura y prescripciones a nuevas fechas validadas. No copia ejecuciones, feedback ni asignaciones publicadas. Conserva referencia al origen. Las competiciones futuras se modelarán como eventos de temporada independientes de las sesiones.

### 4.3 Selección de destinatarios

`TargetRule` almacena filtros estructurados, no SQL ni nombres concatenados. Una regla combina categoría, sexo competitivo, modalidad y grupo. Dentro de una dimensión se aplica OR; entre dimensiones, AND. Varias reglas se unen con OR. Se pueden añadir deportistas explícitos y excluir otros; las exclusiones prevalecen.

Ejemplo: `(Cadete AND masculino AND K1) OR (grupo Tecnificación)`, más deportistas explícitos, menos exclusiones. Una dimensión vacía no restringe; asignar a todo el club requiere elección explícita.

El entrenador previsualiza destinatarios antes de publicar. El servidor resuelve la selección para la fecha local de cada sesión con pertenencias y categorías vigentes, comprueba permisos y genera una sola asignación por deportista. Si incluye personas no autorizadas se rechaza la publicación; no se publica parcialmente sin avisar.

La sesión hereda la selección del plan o declara una propia que reemplaza la heredada. Los planes concurrentes no tienen precedencia automática: dos sesiones distintas se mantienen distintas y se advierte de solapamientos.

Los destinatarios se congelan al publicar. Entrar o salir de un grupo no altera asignaciones existentes. Una actualización explícita muestra altas y bajas y conserva asignaciones con ejecución; las retiradas sin ejecución se cancelan con motivo. Se conserva un snapshot de categoría, sexo competitivo, grupos y modalidad de contexto para estadísticas históricas.

## 5. Prescripción, revisiones y asignaciones

### 5.1 Cadena de datos

```text
WorkoutTemplate → TemplateRevision
                         ↓ copia al crear sesión
WorkoutSession → SessionRevision → SessionAssignment
                                       ↓
                             AssignmentPrescriptionRevision
                              (base + adaptación efectiva)
                                       ↓
                              WorkoutExecution → Resultados
                                       └──────→ SessionFeedback
```

| Entidad | Responsabilidad |
| --- | --- |
| `WorkoutTemplate` | Identidad reutilizable, autor y estado archivado/activo. |
| `TemplateRevision` | Versión inmutable de título, tipo, objetivo, bloques y contenido. |
| `WorkoutSession` | Identidad común, día, horario, duración prevista, entrenador responsable y estado de planificación. |
| `SessionRevision` | Prescripción común inmutable; referencia opcional a revisión de plantilla de origen. |
| `SessionBlock` | Revisión, identificador estable de bloque, título, orden e instrucciones. |
| `ExercisePrescription` | Bloque, identificador estable de elemento, ejercicio, orden y objetivos de series/reps/carga/tiempo/distancia/intensidad/descanso/lado. |
| `SessionAssignment` | Sesión, deportista, estado individual, fecha de asignación y contexto histórico. Única por `(club_id, session_id, athlete_id)`. |
| `AssignmentPrescriptionRevision` | Base común utilizada, adaptación estructurada opcional, autor, motivo y fecha. |

La sesión común se almacena una vez por revisión. Una asignación sin adaptación referencia esa base; no duplica todo el entrenamiento. Una adaptación conserva operaciones sobre identificadores estables y contenido efectivo resuelto e inmutable. No se parchean arrays por su posición.

Los snapshots incluyen nombres, unidades y parámetros necesarios para mostrar contenido aunque se archive un ejercicio o cambie un catálogo. Las revisiones tienen `schema_version`; los lectores mantienen compatibilidad o una migración explícita para versiones anteriores.

### 5.2 Edición e histórico

- Editar una plantilla crea una revisión. Ninguna sesión existente se actualiza por ese cambio.
- Publicar una sesión guarda prescripción y destinatarios en una transacción.
- Editar contenido publicado crea una nueva `SessionRevision`. La asignación conserva su base anterior hasta una actualización explícita.
- La actualización masiva solo afecta a asignaciones futuras sin ejecución iniciada. La interfaz muestra afectados, bloqueados y adaptaciones pendientes de revisión.
- Una adaptación existente no se aplica automáticamente a otra base. El entrenador conserva su versión o la revisa y publica contra la nueva base.
- El primer guardado de ejecución, incluso borrador, comprueba la versión de asignación y fija `assignment_prescription_revision_id` y el horario/contexto de referencia en la misma transacción; una actualización concurrente obliga a recargar antes de registrar. Ediciones posteriores del calendario no cambian esa evidencia.
- No se mueve, cancela o sustituye de forma masiva una sesión con ejecuciones iniciadas. Se pueden cancelar o sustituir explícitamente las asignaciones pendientes manteniendo el resto. Para cambiarles el horario se crea una sesión de sustitución; no se altera el horario común de quienes ya iniciaron ejecución.
- Corregir resultados requiere autor, fecha y motivo, conserva la revisión previa e invalida los agregados afectados. El histórico puede corregirse de forma trazable; nunca se sobrescribe silenciosamente.

### 5.3 Adaptación individual

Permite sustituir, añadir o retirar ejercicios; cambiar series, repeticiones, carga, distancia, duración, intensidad, descanso e instrucciones; y sustituir bloques completos. Se aplica solo a la asignación seleccionada y requiere permiso sobre ese deportista.

El detalle distingue prescripción común original, adaptación efectiva y resultados reales. Si se realiza un ejercicio no prescrito, el resultado incluye su identidad/snapshot y origen añadido o sustituido; no obliga a modificar retrospectivamente la prescripción.

## 6. Estados y transiciones

### 6.1 Planificación y cumplimiento

`WorkoutSession.status` expresa el estado común: `draft`, `planned`, `cancelled`, `replaced`. El borrador no aparece al deportista. Una sesión de grupo no pasa a «realizada» cuando responde la primera persona.

`SessionAssignment.status` expresa lo que corresponde a cada deportista:

| Estado | Significado | Efecto analítico |
| --- | --- | --- |
| `planned` | Asignada, sin cierre individual. | Si venció, «sin registrar», no omitida. |
| `completed` | Deportista declara realizada. | Cuenta como completada. |
| `partial` | Realización parcial. | Cuenta por separado, no como completada. |
| `skipped` | Deportista declara no realizada. | Cuenta como omitida. |
| `cancelled` | Entrenador cancela una asignación pendiente. | Excluida del denominador de cumplimiento. |
| `replaced` | Sustituida por otra asignación identificada. | Original excluida; reemplazo con seguimiento propio. |

`planned → completed/partial/skipped` corresponde al registro individual. `planned → cancelled/replaced` exige permiso de planificación y ausencia de ejecución iniciada. Los estados finales no vuelven a `planned` mediante edición genérica; una corrección usa un comando auditado. `replaced_by_assignment_id` identifica el reemplazo, sin ciclos ni enlaces a otro deportista o club.

La cancelación o sustitución común solo pasa la sesión a `cancelled/replaced` si afecta a todos sus destinatarios sin ejecución iniciada; una operación sobre un subconjunto cambia únicamente sus asignaciones y mantiene la sesión común.

Una ejecución tiene estado de guardado `draft/submitted`, separado del cumplimiento. Un borrador no declara una sesión completada. «Sin feedback» se deriva de la ausencia de feedback enviado y puede coexistir con ejecución enviada. El vencimiento usa la hora final prevista y la zona del club; una sesión futura no genera un pendiente atrasado.

### 6.2 Reglas de cierre

- Una asignación tiene como máximo una ejecución lógica y un feedback lógico; las correcciones generan revisiones.
- El deportista puede guardar ejecución y feedback conjuntamente o completar feedback después.
- `completed/partial` permiten datos incompletos: la UI señala qué falta sin inventar valores. Duración real y RPE válidos son necesarios para calcular carga, no para conservar la declaración de realización.
- `skipped` no exige duración ni RPE y no admite resultados deportivos. Si existen resultados, declarar `partial/completed` o descartarlos explícitamente mediante corrección auditada.
- Descanso es un tipo propio: no exige resultados, duración activa ni RPE. Su cumplimiento puede confirmarse, pero no entra en métricas de cumplimiento de entrenamientos activos.

## 7. Contenido deportivo y ejecución real

### 7.1 Modelo común y unidades

`WorkoutExecution` contiene asignación, revisión efectiva utilizada, fecha local de realización, inicio/fin opcionales, duración activa real en segundos, notas y estado de guardado. `SessionFeedback` es la única fuente del RPE global real. RPE objetivo y RPE por serie/segmento son campos distintos.

Persistir segundos, metros y kilogramos; convertir a minutos, kilómetros y ritmos para visualización/cálculo. Identificar unidades de potencia y cadencia explícitamente. Cero y ausencia son distintos. RPE global entre 1 y 10; RIR no negativo; no se admiten tiempos, distancias, cargas o repeticiones negativos. La duración activa no se deduce del tiempo que permaneció abierta la pantalla.

`TrainingType` es un catálogo del club con códigos base estables: `water`, `gym`, `running`, `ergometer`, `core`, `mobility`, `test`, `recovery`, `rest`, `other`. Los tipos personalizados usan un esquema genérico validado y nombre configurable. Archivar un tipo o ejercicio no borra históricos.

Estructura común, relaciones y resultados consultables se guardan en tablas relacionales. JSONB se reserva para snapshots inmutables y extensiones tipadas con versión; no sustituye todas las métricas por texto libre.

### 7.2 Esquemas específicos del producto final

La tabla describe el producto final; `MVP.md` delimita qué campos y flujos se implementan inicialmente.

| Tipo / entidad | Prescripción y resultados estructurados |
| --- | --- |
| Gimnasio / `ActualSet` | Ejercicio, orden, serie, reps, carga, RIR, RPE de serie opcional, descanso, tiempo, distancia, lado y notas. Bilateral, unilateral, isométrico, tiempo y distancia. |
| Agua / `WaterRunResult` | Subtipo técnica/base/intensidad/simulación/específico, objetivo, calentamiento, bloques, mangas, puertas, duración, tiempos por manga, dificultad, errores y contenido técnico. |
| Carrera / `RunningResult`, `RunningSplit` | Distancia, duración, desnivel positivo, parciales, RPE por segmento, observaciones y respuesta posterior. Ritmo derivado de distancia/tiempo válidos. |
| Ergómetro / `ErgometerResult`, `ErgometerInterval` | Modelo, resistencia/drag con unidad/escala, distancia, tiempo, ritmo, potencia, cadencia, intervalos y observaciones. |
| Test / `TestDefinition`, `TestProtocolRevision`, `TestResult` | Nombre, distancia, protocolo versionado, máquina/modelo, resistencia, fecha, tiempo, potencia, cadencia, observaciones y referencia a ejecución. Iniciales: 200, 500 y 1000 m. |
| Core / resultados por serie | Reps, tiempo, lado, series, margen temporal, RIR cuando aplique y observaciones. |
| Movilidad / `MobilityResult` | Duración, zonas, lado, rigidez, asimetrías, molestias y sensación de movilidad. |
| Recuperación | Duración, objetivo, instrucciones, actividad realizada y sensaciones. |
| Descanso | Indicación de descanso y confirmación opcional, sin simular una actividad con RPE. |
| Otro configurable | Bloques, instrucciones, duración y métricas genéricas con nombre y unidad. |

Las zonas corporales incluyen inicialmente isquios, cadera, lumbar/lumbopélvica, torácica, dorsal, pectoral, flexores de cadera, gemelo, sóleo, aductores y glúteos. Se admite registrar varias zonas; el texto libre complementa el catálogo.

### 7.3 Comparabilidad e historial de rendimiento

`Exercise` incluye tipo de medición y marca de ejercicio de referencia. El historial de fuerza muestra carga, reps, RIR, volumen, mejores marcas y tendencia por ejercicio y variante comparables. Volumen externo = suma de `kg × reps` de series válidas; no equivale a sRPE ni permite mezclar isométricos o distancias. La convención de carga por lado/material se guarda y muestra para evitar sumas ambiguas.

Los tests solo se agrupan como comparables si coinciden distancia, versión de protocolo, modelo de máquina y resistencia/escala. Un dato ausente deja el resultado como «comparabilidad no verificada». Los demás resultados permanecen en el histórico con contexto; no se presenta una mejora entre protocolos distintos como marca equivalente. La definición del test indica la métrica principal y si mejora al aumentar o disminuir; en fuerza, las mejores cargas se comparan para el mismo ejercicio, variante, reps y convención de carga. No se estima 1RM en el MVP.

## 8. Feedback, recuperación, carga y señales

### 8.1 Feedback y recuperación

`SessionFeedback` contiene RPE global opcional, sensación general, calidad técnica, fatiga muscular, presencia/intensidad de molestias, zonas, comentario y fecha de envío. No duplica el estado de realización. Escalas iniciales: sensación, calidad técnica, sueño, motivación y energía de 1 (muy baja/mala) a 5 (muy alta/buena); fatiga y agujetas de 1 (ninguna) a 5 (muy altas); intensidad de dolor opcional de 0 (ninguno) a 10 (máximo percibido). La ausencia es `null`, no el extremo inferior. Se valida coherencia entre molestias sí/no y su intensidad. Las etiquetas se adaptan al concepto y se conserva la versión de escala si cambia.

El modo infantil simplifica preguntas y controles manteniendo el contrato de datos. Es una preferencia de presentación, sin fijar umbrales de edad en código. Los detalles por serie permanecen disponibles sin bloquear el envío rápido.

`RecoveryLog` es único por `(club_id, athlete_id, local_date)`. Admite sueño, fatiga, agujetas, motivación, energía, dolor, zonas y comentario. El registro es opcional para el deportista. Ausencia de registro no significa mala recuperación. Se muestran series temporales independientes.

### 8.2 Cálculo de carga

```text
sRPE = (actual_duration_seconds / 60) × SessionFeedback.rpe
```

- Solo se calcula para ejecuciones enviadas `completed/partial` con duración y RPE presentes. Nunca se usa duración prevista como sustituto silencioso.
- Si falta un dato, carga `null`: «sin datos suficientes». RPE ausente no es cero.
- Una omitida tiene cero actividad registrada, pero no una medición de sRPE. Canceladas, sustituidas y descansos quedan fuera de los agregados de carga de entrenamiento.
- Mostrar suma de cargas conocidas, número con carga calculable y número sin datos. Redondear solo en presentación.
- Fecha de carga: realización local. Semana: lunes a domingo en zona del club. Planificación/cumplimiento usan fecha prevista y lo indican.
- Filtrar por sesión, día, semana, mes, deportista, grupo, categoría, sexo, modalidad, temporada, fase y tipo. El filtro por ejercicio se aplica al rendimiento, no a un reparto ficticio del RPE global.
- Pertenencia histórica a grupos/categorías: contexto congelado de asignación. Varios grupos seleccionados deduplican asignaciones. Una persona puede aparecer en dos vistas de grupo; no se suman esas vistas para obtener el total del club.
- RPE medio usa solo respuestas válidas y muestra tamaño de muestra. La carga media de grupo es la suma conocida dividida por el número de deportistas con al menos una carga calculable en el período; muestra ese denominador frente al total autorizado del grupo y las sesiones incompletas. No asume cero para quien no respondió.
- Comparar semanas con cobertura visible. Si la semana anterior carece de datos o tiene carga cero, no calcular un porcentaje de cambio engañoso.

Inicialmente se usan consultas SQL con índices adecuados. Las futuras proyecciones o cachés serán reconstruibles y se actualizarán tras una corrección; nunca serán la única fuente de datos.

### 8.3 Cumplimiento y seguimiento

Mostrar completadas, parciales, omitidas, sin registrar, canceladas y sustituidas. Porcentaje de cumplimiento completo: `completed / asignaciones de entrenamiento vencidas elegibles`, contando en ambos términos solo ese conjunto temporal; excluir canceladas, sustituidas, descanso y futuras. Las parciales tienen su porcentaje. El detalle permite inspeccionar los registros de cada agregado.

En el MVP las señales son hechos observables: molestias declaradas y registros/feedback pendientes. La detección de caída de rendimiento, RPE elevado, mala recuperación o carga sostenida llegará después con reglas versionadas, período, evidencia y umbrales explícitos. Las cifras de carga no se presentan como diagnóstico médico.

`Recommendation` futura guardará evidencia, propuesta, versión de regla, estado y decisión (`accepted/modified/rejected`). Aceptar crea una revisión mediante el caso de uso autorizado; no modifica histórico ni ejecuta cambios automáticamente. La progresión de fuerza considerará carga, reps, RIR, técnica, cumplimiento e historial.

## 9. Calendario y recurrencias

El calendario ofrece día y semana, sesiones grupales e individuales, cambios de horario, movimiento, cancelación y sustitución. Mover tendrá alternativa por formulario accesible aunque exista arrastre.

Guardar instantes de calendario con zona en PostgreSQL y transmitirlos en ISO 8601; conservar zona IANA del club y fechas civiles para días de plan, nacimiento y recuperación. Una fecha civil no se convierte en medianoche UTC. La edición resuelve explícitamente horas inexistentes o ambiguas por cambio horario.

`RecurrenceSeries` guarda frecuencia, días, hora local, zona y fecha límite. El MVP materializa una serie semanal finita dentro del plan, sin tarea periódica: cada ocurrencia genera sesión y asignaciones independientes. La clave `(series_id, occurrence_key)` evita duplicados.

La UI distingue «solo esta sesión» y «esta y las futuras pendientes». Las excepciones se guardan y no reaparecen al regenerar. Las realizadas, los borradores de ejecución y las adaptaciones no se alteran por edición de serie. Mover valida día, microciclo y fase de destino; cruzar de plan requiere destino autorizado. Se advierte de solapamientos sin fusionar sesiones automáticamente.

## 10. Contratos de API y consistencia

Prefijo `/api/v1`. Recursos de club bajo `/clubs/{club_id}/...`; el servidor valida membresía y ámbito. Estas son familias iniciales; el contrato OpenAPI se concretará al implementar.

| Familia | Operaciones principales |
| --- | --- |
| `/auth/*`, `/me` | Sesión, recuperación, invitaciones e identidad actual. |
| `/memberships`, `/athletes`, `/coaches`, `/groups` | Administración y estructura deportiva. |
| `/seasons`, `/phases`, `/plans`, `/microcycles`, `/plan-days` | Jerarquía y copia de planes. |
| `/plans/{id}/targets/preview` | Resolución y validación de destinatarios. |
| `/templates`, `/exercises`, `/training-types`, `/disciplines` | Catálogos y versiones. |
| `/sessions`, `/sessions/{id}/publish`, `/sessions/{id}/reschedule` | Crear, publicar y cambiar horario. |
| `/sessions/{id}/cancel`, `/sessions/{id}/replace`, `/recurrence-series` | Comandos de calendario y recurrencia. |
| `/assignments/{id}/prescription-revisions` | Adaptación o adopción de nueva base. |
| `/assignments/{id}/execution`, `/assignments/{id}/feedback` | Lectura, guardado y envío de seguimiento propio. |
| `/assignments/{id}/corrections` | Correcciones trazables de registros enviados. |
| `/athletes/{id}/recovery`, `/athletes/{id}/history` | Recuperación e historial autorizado. |
| `/dashboards/athlete`, `/dashboards/coach`, `/analytics/*` | Agregados con permisos. |
| `/audit`, `/data-requests` | Auditoría y exportación/eliminación. |

Salvo `/auth/*` y `/me`, los sufijos están bajo el prefijo de club. Ninguna pantalla se conecta directamente a PostgreSQL.

Reglas del contrato:

- Paginación y límites; rangos temporales obligatorios en calendarios y consultas extensas.
- Validación semántica de fechas, unidades, rangos, relaciones y permisos en backend.
- Errores con `code`, mensaje, errores de campo y `request_id`, sin datos internos. `401` sesión inválida, `403` acción prohibida, `404` recurso fuera del ámbito visible, `409` conflicto y `422` datos inválidos.
- Concurrencia mediante `version` esperada. Una versión antigua produce conflicto; no prevalece silenciosamente la última escritura.
- Publicación, duplicación de planes/series y envío de ejecución admiten clave de idempotencia por actor, club y operación. Misma clave/cuerpo devuelve resultado previo; cuerpo distinto produce conflicto.
- Unicidad de asignación, ejecución, feedback y recuperación impide duplicados aunque falle el cliente.
- Publicación y asignaciones; adaptación y revisión; envío y estado individual; corrección y auditoría se guardan en transacciones atómicas.
- Ningún endpoint genérico permite cambiar `club_id`, autor, permiso o estado saltándose comandos de dominio.

## 11. Web, navegación y PWA

| Área | Pantallas principales |
| --- | --- |
| Acceso | Invitación, login, recuperación y selección de rol si procede. |
| Deportista | Hoy, agenda, detalle, registro rápido, recuperación, historial y evolución. |
| Entrenador | Resumen, calendario, planes, editor, plantillas, seguimiento grupal y ficha individual. |
| Administración | Usuarios/permisos, grupos, categorías, modalidades, temporadas, configuración y auditoría. |

El menú de entrenador contiene calendario, organización de entrenos y acceso a deportistas/grupos. Solo los roles autorizados lo ven. El menú del deportista empieza con el calendario, sigue con el próximo entreno y su registro con feedback, y muestra después historial y una barra de fatiga cualitativa sin valores numéricos. La vista de un deportista abierta desde el menú del entrenador reutiliza la misma presentación en modo consulta y mantiene los permisos de la API. Las sesiones distinguen casa y club; las de casa llevan pasos detallados. En agua, el registro completado o parcial requiere sensaciones, trabajo realizado, lo mejor y lo peor. La barra de fatiga combina carga y sensaciones recientes como orientación visual, sin sustituir las medidas independientes ni ofrecer una interpretación médica.

Cada pantalla contempla carga, vacío, error, falta de permiso y conflicto. Ocultar controles por rol mejora la UI, pero no sustituye autorización. Formularios con etiquetas, teclado, foco visible, errores asociados y estados que no dependan solo del color.

PWA inicial: manifest, iconos, instalación y caché de archivos estáticos. Las peticiones autenticadas y datos de menores no se guardan en la caché del service worker. El MVP requiere conexión para leer/guardar datos deportivos: muestra desconexión y no anuncia un guardado antes de confirmación del servidor. La sincronización offline queda aplazada.

El feedback rápido usa pocas preguntas y campos opcionales progresivos. Objetivo de usabilidad: enviarlo en aproximadamente un minuto, comprobado en el piloto. Validar UI desde 360 px, con teclado en escritorio, en Safari y Chrome. Encapsular dependencias de plataforma para reutilizar el frontend mediante Capacitor.

## 12. Privacidad, auditoría y ciclo de vida de datos

Perfiles y estadísticas privados; sin rankings públicos. Nacimiento y observaciones personales no se incluyen en respuestas que no los necesitan. Recuperación y molestias requieren permisos deportivos; los logs operativos no copian comentarios ni cuerpos sensibles.

`AuditLog` registra club, actor, acción, recurso, fecha, motivo cuando corresponda, petición y referencias a revisiones. Incluye planificación, adaptaciones, correcciones, permisos, perfiles, altas/bajas, exportaciones y eliminaciones. Se escribe en la misma transacción que la operación; no almacena contraseñas, tokens ni copias indiscriminadas de datos sensibles.

Desactivar o archivar mantiene histórico y retira acceso; no equivale a eliminar. `DataRequest` implementa solicitudes de exportación/eliminación con verificación de identidad/ámbito, estado, responsable y resultado. Exportar datos propios excluye datos de compañeros. Los archivos tienen acceso temporal autenticado y caducidad configurada.

La eliminación ejecuta una política documentada de borrado o anonimización sobre perfiles, resultados, snapshots, trabajos, exportaciones y referencias de auditoría, sin romper datos de terceros. Las copias tienen retención limitada y procedimiento para reaplicar eliminaciones si se restaura una copia anterior. Los plazos, responsables y condiciones de consentimiento se definirán con el club antes de incorporar datos reales; este documento no establece una conclusión legal.

Tutor y consentimiento estructurado serán extensiones mediante `GuardianAthleteLink` y `ConsentRecord` versionados por finalidad y vigencia. No se presupone que el futuro rol de tutor resuelva las condiciones de uso de menores durante el piloto.

## 13. Extensiones del producto final

| Capacidad | Punto de extensión y regla |
| --- | --- |
| Varios clubes operativos | Extensión a largo plazo, cuando exista una necesidad real; alta y selección sobre membresías y aislamiento existentes. Independiente de cualquier monetización. |
| Google Calendar | Conexión por usuario, credenciales protegidas y `ExternalCalendarEvent` con asignación, proveedor, calendario, ID externo, revisión sincronizada y estado. Unicidad del enlace, reintentos y cancelaciones; la app sigue siendo fuente de verdad. |
| Notificaciones | Preferencias por usuario, eventos de nuevo entrenamiento/cambio/pendiente/alerta y registro de entregas para deduplicar. |
| Salud y sensores | Adaptadores para HealthKit, Apple Health/Watch, GPS, pulso, sueño, potencia y cadencia; origen, unidad, timestamp y autorización de importación explícitos. |
| Recomendaciones y progresión | Reglas versionadas y decisiones del entrenador; aceptación mediante comandos existentes. |
| Adjuntos y vídeo | Almacenamiento de objetos privado y URLs temporales; metadatos/permisos en la API. |
| Competiciones | Eventos de temporada, objetivos y planificación, separados de entrenamientos. |

Las escrituras que originen efectos externos persistirán un evento en una tabla outbox dentro de la transacción. El ejecutor procesará eventos con reintentos, deduplicación y estado de error. No se realizarán llamadas externas dentro de una transacción deportiva. Tablas e integraciones futuras se crean cuando corresponda su entrega, no para simular funcionalidades en el MVP.

## 14. Operación y validación

### 14.1 Entornos y despliegue

Entornos local, pruebas y producción con configuración/secretos separados. Desarrollo reproducible con web, API, PostgreSQL y correo de pruebas. Datos de ejemplo sintéticos. Migraciones versionadas, índices por club/fechas/deportista y revisión de consultas de calendario/dashboards.

Producción incluye HTTPS, migraciones controladas, comprobaciones de disponibilidad, logs con `request_id`, seguimiento de errores sin datos deportivos sensibles, copias automáticas y ensayo de restauración. Las tareas duraderas sobreviven al reinicio. Los objetivos de recuperación y la retención se acuerdan antes del piloto.

### 14.2 Verificación exigida

| Nivel | Comprobaciones |
| --- | --- |
| Dominio | Segmentación, reglas de edad, estados, revisiones, adaptación, comparabilidad, carga y datos ausentes. |
| Integración PostgreSQL | Claves de club, unicidades, permisos, transacciones, idempotencia, correcciones y concurrencia. |
| Contrato | OpenAPI/cliente consistentes, errores y compatibilidad de snapshots. |
| E2E | Administración → planificación → asignación → adaptación → ejecución → feedback → revisión e histórico. |
| Interfaz | Móvil/escritorio, modo infantil, teclado, errores, conflicto y desconexión. |
| Operación | Despliegue desde cero, migración, revocación, exportación, eliminación y restauración. |

Condiciones de aceptación: editar plantilla no cambia sesiones existentes; editar sesión no altera prescripción ya ejecutada; ninguna consulta revela datos de otro club/deportista; reenvíos no duplican datos; corregir duración o RPE recalcula carga; el cambio horario no desplaza recurrencias a otra hora local sin advertencia.

La trazabilidad de los 40 apartados de requisitos, entregas y escenarios está en [MVP.md](MVP.md). Cada funcionalidad debe referenciar su requisito y respetar estas reglas antes de darse por terminada.
