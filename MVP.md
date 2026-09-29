# MVP de TeiTraining

## 1. Objetivo y contrato de entrega

Entregar una web que un club de piragüismo slalom pueda utilizar durante varias semanas para planificar entrenamientos, asignarlos, adaptarlos a cada deportista, registrar ejecución y revisar cumplimiento, carga, recuperación y evolución básica.

La prioridad es resolver el trabajo diario del club promotor, sin objetivo de monetizar su uso. El éxito se mide por utilidad deportiva, adopción y mantenimiento asumible, sin objetivos de ingresos o captación comercial. Una posible monetización para otros clubes queda como decisión muy a futuro y no condiciona esta entrega.

El flujo de aceptación principal es:

```text
Administrador configura el club y sus permisos
    → Entrenador planifica y publica sesiones
    → Cada deportista consulta su prescripción efectiva
    → Registra ejecución y feedback
    → Entrenador revisa resultados y adapta sesiones futuras
    → El histórico conserva lo prescrito y lo realizado
```

[REQUIREMENTS.md](REQUIREMENTS.md) define el producto final. [ARCHITECTURE.md](ARCHITECTURE.md) define entidades, reglas, permisos y contratos de implementación. Este documento fija el alcance inicial y las pruebas funcionales para aceptarlo; no implica que la aplicación esté implementada.

### 1.1 Criterio de alcance

- **Obligatorio:** debe funcionar antes de declarar terminado el MVP.
- **Básico:** capacidad incluida con el límite explícito descrito aquí.
- **Posterior:** se conserva en arquitectura y trazabilidad, pero no bloquea el primer lanzamiento.

Un campo opcional debe poder registrarse; opcional significa que el usuario puede dejarlo vacío. El registro diario de recuperación es opcional para el deportista, pero su funcionalidad y consulta forman parte del MVP.

Esta reformulación incorpora al alcance obligatorio el descanso como tipo propio, la jerarquía completa de planificación, la asignación individual explícita, las recurrencias semanales limitadas, la recuperación básica y el histórico sencillo de fuerza/tests. Acercan el primer producto a los requisitos sin introducir integraciones ni análisis predictivo.

## 2. Usuarios, organización y plataforma

Un club operativo, varios entrenadores y deportistas, varios grupos y categorías, K1 y C1 configurables y varios planes simultáneos. Un deportista puede practicar ambas modalidades y pertenecer a varios grupos. El esquema y las pruebas incluyen aislamiento entre clubes, aunque no exista alta pública ni selector multi-club en el MVP.

La plataforma inicial es una web mobile-first, responsive e instalable como PWA, validada en Safari y Chrome. Requiere conexión para consultar y guardar datos deportivos. Publicación en tiendas, empaquetado nativo y sincronización offline son posteriores.

| Rol | Funciones incluidas |
| --- | --- |
| Administrador | Invitar y desactivar miembros; gestionar perfiles, grupos, pertenencias, entrenadores autorizados, categorías, modalidades, temporada, permisos y auditoría; tramitar exportación/eliminación autorizadas. |
| Entrenador | Crear/duplicar planes y plantillas; publicar, mover, cancelar y sustituir sesiones; asignar por filtros o deportistas; adaptar prescripciones; consultar seguimiento y evolución en su ámbito. |
| Deportista | Consultar sesiones propias, registrar realización y resultados, enviar feedback, registrar recuperación y consultar historial/evolución propios. |

Una cuenta puede combinar roles. Administrar el club no concede automáticamente acceso a datos deportivos sensibles; se otorga además el permiso deportivo correspondiente. No hay registro público, perfiles públicos ni rankings públicos.

## 3. Recorridos y pantallas obligatorias

### 3.1 Puesta en marcha del club

El administrador configura zona horaria, temporada y categorías de edad con fecha de referencia; crea grupos y modalidades; invita usuarios y asigna permisos. Puede autorizar a un entrenador por grupo o directamente sobre un deportista.

Perfil mínimo: nombre, nacimiento, sexo competitivo, categoría por temporada, modalidades, grupos, estado deportivo y entrenadores autorizados. Las observaciones tienen acceso restringido. Las categorías son configurables; no se crean identificadores rígidos como `cadete_masculino_k1`.

Pantallas: acceso, invitación, recuperación de contraseña, usuarios/permisos, grupos, categorías/modalidades, temporadas y auditoría. Una baja revoca acceso y conserva histórico; eliminar información sigue un procedimiento distinto.

### 3.2 Planificación del entrenador

Crear temporada → fase → plan → microciclo → día → sesión. Una temporada activa por club; las anteriores permanecen consultables. Fases con nombre, fechas y objetivos configurables. Valores iniciales: adaptación, fuerza general, hipertrofia, fuerza máxima, potencia/explosividad, puesta a punto y competición.

El entrenador mantiene planes paralelos, duplica uno como base para otro y selecciona destinatarios combinando categoría, sexo, modalidad, grupo y deportistas concretos. Previsualiza la selección y publica. Coincidir con varios filtros genera una sola asignación de la misma sesión.

La navegación del entrenador se organiza por menús visibles solo con ese rol: calendario, organización de entrenos, deportistas/grupos y seguimiento. Desde la ficha de un deportista autorizado se abre su misma vista de calendario e historial en modo consulta; el entrenador no registra el feedback en su nombre.

Pantallas: resumen del entrenador, planes, detalle de plan/microciclo, calendario diario/semanal, editor de sesión, biblioteca de plantillas y catálogo de ejercicios.

### 3.3 Consulta y registro del deportista

La vista principal del deportista presenta primero el calendario y justo debajo la previsualización del siguiente entreno, con hora, contenido y acción para marcarlo completado. Esa acción abre el formulario de feedback antes del envío. Después aparecen una señal visual de fatiga actual y el historial propio. «Hoy» muestra sesiones del día, próximas y feedback pendiente. El detalle presenta objetivo, horario, duración prevista, bloques, ejercicios y adaptación personal. La vista rápida permite declarar realizada, parcial o no realizada, registrar duración real, RPE, sensaciones y molestias. Los resultados específicos dependen del tipo.

Hay modo simplificado con preguntas cortas y controles etiquetados para usuarios infantiles. Guardar borradores y reintentar un envío no duplica registros. Los mensajes distinguen guardado confirmado, error y falta de conexión.

Pantallas: hoy, agenda, detalle de sesión, registro, recuperación diaria, historial y evolución básica.

### 3.4 Revisión del entrenador

El seguimiento por grupo/sesión muestra asignados, completados, parciales, omitidos, sin registrar, sin feedback, RPE medio con tamaño de muestra, molestias y carga conocida con cobertura. Canceladas y sustituidas aparecen identificadas, sin penalizar cumplimiento.

La ficha individual incluye calendario, historial, feedback, molestias, carga semanal, recuperación, series de fuerza y tests, además de resultados básicos de agua/carrera/ergómetro. Permite adaptar una sesión futura y comparar prescripción original, adaptación y ejecución.

Las señales iniciales son pendientes y molestias declaradas. No se generan diagnósticos, predicciones ni cambios automáticos de entrenamiento.

## 4. Planificación, calendario y prescripción

| Capacidad | Alcance obligatorio |
| --- | --- |
| Temporadas y fases | Fechas, objetivos, estado y consulta de temporadas cerradas; categorías por temporada. |
| Planes | Varios simultáneos; nombre/objetivos, fase, destinatarios y duplicación a nuevas fechas sin resultados previos. |
| Microciclos y días | Entidades explícitas; límites de fechas validados; varias sesiones por día. |
| Destinatarios | AND entre dimensiones, OR dentro de dimensión o entre reglas; inclusiones/exclusiones individuales; previsualización y permisos. |
| Sesiones | Fecha/hora, duración prevista, tipo, modalidad o general, objetivo, instrucciones, entrenador responsable, bloques y destinatarios. |
| Calendario | Día/semana, detalle, crear, editar, mover por formulario, cancelar y sustituir con enlace al reemplazo. Arrastrar es posterior. |
| Recurrencias | Repetición semanal por días hasta fecha dentro del plan; editar una o futuras pendientes; sin duplicar ni reabrir excepciones. |
| Plantillas | Crear, editar mediante revisión, duplicar, reutilizar y guardar sesión como plantilla. |
| Bloques y ejercicios | Orden, título, instrucciones y contenido estructurado; catálogo archivable con ejercicios de referencia. |
| Adaptaciones | Sustituir/añadir/retirar ejercicio, cambiar series/reps/carga/distancia/duración/intensidad/descanso/instrucciones y sustituir bloque completo. |

Publicar congela destinatarios y prescripción. Cambiar pertenencias no reescribe asignaciones. Actualizar destinatarios o aplicar una revisión requiere operación explícita con previsualización. Las asignaciones con ejecución iniciada quedan protegidas; las adaptaciones existentes deben revisarse antes de cambiar su base.

Cada sesión indica si se realiza en casa o en el club. Las sesiones en casa deben incluir indicaciones detalladas por pasos, especialmente las rutinas de estiramientos y movilidad. Una sesión de grupo tiene prescripción común y seguimiento por persona. Los estados de realización pertenecen a cada asignación, no a la sesión común. Una sesión vencida sin respuesta se muestra «sin registrar»; nunca se convierte automáticamente en «no realizada».

## 5. Tipos de entrenamiento y resultados

Todos los tipos incluyen objetivo, instrucciones, bloques, duración prevista cuando corresponda y notas. Estado individual y feedback global comparten flujo; no se crean formularios incompatibles por disciplina.

| Tipo | Prescripción y registro incluidos | Posterior |
| --- | --- | --- |
| Gimnasio | Ejercicio/orden, series, reps, carga, RIR, RPE opcional por serie, descanso, tiempo, distancia, lado y notas. Resultados por serie; bilateral, unilateral e isométricos. | Propuestas automáticas de progresión. |
| Agua/slalom | Subtipo técnica/base/intensidad/simulación/específico, objetivo, calentamiento/bloques, duración, mangas previstas, RPE objetivo, instrucciones y notas; ejecución con duración, RPE y comentario. Al completarla o registrarla parcialmente se piden sensaciones, trabajo realizado, lo mejor y lo peor del entreno. | Puertas, tiempos por manga, dificultad y errores técnicos estructurados. |
| Carrera/trail | Distancia, duración, ritmo derivado, RPE, desnivel opcional y comentario. | Parciales, RPE por segmento, respuesta posterior estructurada e importación GPS. |
| Ergómetro | Modelo, resistencia/drag identificado, distancia, tiempo, ritmo, RPE y comentario; potencia y cadencia opcionales. | Intervalos e importación de máquinas. |
| Tests | Definición configurable y protocolo versionado; iniciales 200/500/1000 m; registro manual de fecha, distancia, tiempo, modelo, resistencia, RPE y notas; potencia/cadencia opcionales. | Protocolos compuestos y captura automática. |
| Core | Series, reps, segundos, lado, margen temporal, RIR opcional y comentario. | Análisis específico avanzado. |
| Movilidad | Duración/segundos, series cuando proceda, zonas, lado, molestias y comentario. | Rigidez, asimetrías y sensación de movilidad como series estructuradas. |
| Recuperación | Objetivo, duración, instrucciones, realización y sensaciones. | Protocolos avanzados. |
| Descanso | Tipo independiente, instrucciones y confirmación opcional; sin exigir RPE o duración activa. | Sin ampliación necesaria para el flujo básico. |
| Otro configurable | Nombre, bloques, instrucciones, duración y medidas genéricas con unidad. | Constructor avanzado de esquemas. |

Un ejercicio añadido durante ejecución se registra como tal; no cambia retrospectivamente lo prescrito. Los datos ausentes se muestran como ausentes. Los tests sin protocolo o condiciones verificables se conservan, pero no se presentan como comparables.

## 6. Feedback, recuperación y métricas

### 6.1 Feedback y resultados

Campos disponibles: estado de realización, duración real, RPE global 1–10, sensación general, calidad técnica, fatiga muscular, molestias sí/no, intensidad y zonas opcionales, comentario. Los detalles técnicos son opcionales y no bloquean el flujo rápido, salvo los cuatro campos de reflexión de las sesiones de agua completadas o parciales.

El estado reside en la asignación y el RPE global real en feedback. RPE objetivo y RPE de serie son distintos. La UI puede enviar ejecución y feedback juntos atómicamente o permitir completar feedback después. Los registros enviados admiten corrección con autor, fecha, motivo y revisión anterior conservada.

Una omitida no exige RPE ni duración. Una realizada/parcial con datos insuficientes conserva la declaración y señala que no puede calcularse carga. El modo infantil utiliza los mismos datos con presentación simplificada.

### 6.2 Recuperación diaria

Un registro opcional por persona y fecha local: sueño, fatiga, agujetas, motivación, energía, dolor, zonas y comentario. Edición trazable. Deportista y entrenadores autorizados consultan evolución temporal. La vista puede mostrar una barra orientativa de verde a rojo, sin cifras ni porcentajes, derivada de entrenos realizados y sensaciones recientes; se muestra «sin datos» cuando falta información. No sustituye las series de carga y recuperación ni se interpreta como diagnóstico. No se interpreta ausencia de registro como mala recuperación.

### 6.3 Carga y cumplimiento

```text
sRPE = duración real en minutos × RPE global real
```

Mostrar carga conocida por sesión, día y semana; comparación con semana anterior; total y media de grupo con denominador visible. Los cálculos usan ejecución enviada y datos válidos. Ausencia de duración o RPE produce «sin datos», no cero. Canceladas, sustituidas y descansos no cuentan como entrenamientos con carga.

Los totales no duplican a deportistas presentes en varios grupos. Semanas de lunes a domingo en zona del club; carga por fecha real de ejecución. Cumplimiento por fecha prevista, separando completadas, parciales, omitidas y sin registrar. Excluir del denominador futuras, canceladas, sustituidas y descansos.

### 6.4 Historial, evolución y filtros

- Historial de sesiones con estado, prescripción efectiva, resultados, RPE, molestias y comentarios.
- Fuerza por ejercicio: carga, reps, RIR, volumen, mejores marcas comparables y tendencia sencilla; ejercicios de referencia.
- Tests: tabla y gráfica temporal filtradas por distancia, protocolo, modelo y resistencia comparables.
- Agua/carrera/ergómetro: histórico de métricas básicas disponibles, sin rellenar datos no recogidos.
- Carga, recuperación, rendimiento y molestias en vistas separadas.
- Filtros por deportista, grupo, categoría, sexo, modalidad, semana/mes, temporada, fase y tipo. Filtro por ejercicio en fuerza; no se atribuye RPE global a cada ejercicio.

Las estadísticas históricas usan contexto de asignación conservado. Porcentajes y medias muestran cobertura y número de observaciones; una comparación sin base suficiente se identifica como tal.

## 7. Privacidad y operación necesarias para el piloto

Obligatorio antes de usar datos reales:

1. Invitación, login, recuperación, cierre de sesión y sesiones revocables; correo transaccional configurado.
2. Autorización en servidor por club, rol y ámbito, incluidas estadísticas y exportaciones.
3. Revocación efectiva al desactivar membresía o retirar permisos.
4. Auditoría de planificación, adaptaciones, correcciones, permisos, perfiles y administración.
5. Exportación propia y procedimiento operativo de eliminación/anonimización autorizado, incluidos snapshots y copias restauradas.
6. HTTPS, secretos fuera del repositorio, migraciones, copias automáticas y prueba documentada de restauración.
7. Política de retención y condiciones de tratamiento de datos de menores acordadas con el club. El portal completo de tutores no forma parte de esta entrega.
8. PWA con caché de recursos estáticos; datos autenticados fuera de la caché persistente del service worker.

La entrega administrativa puede ser sencilla, pero debe poder ejecutarse: no basta con indicar que exportación, borrado o restauración se resolverán en el futuro.

## 8. Trazabilidad con los requisitos del producto final

`Rxx` corresponde al apartado numerado de `REQUIREMENTS.md`. «Básico» indica capacidad utilizable con los límites anteriores, no una pantalla vacía ni un modelo sin interfaz.

| Requisito | Entrega MVP | Ampliación posterior |
| --- | --- | --- |
| R01 Alcance | Ciclo completo de planificación, ejecución, seguimiento y análisis básico. | Profundización analítica e integraciones. |
| R02 Roles | Administrador, entrenador y deportista; varios roles por cuenta. | Tutor y consentimientos estructurados. |
| R03 Clubes | Un club operativo y aislamiento probado. | Alta/gestión de otros clubes cuando exista necesidad real, a largo plazo. |
| R04 Perfil deportivo | Datos, modalidades, grupos, categoría de temporada, estado e historial. | Ampliaciones según uso. |
| R05 Categorías | Configurables por temporada y combinables con otras dimensiones. | Sin ampliación necesaria para lo requerido. |
| R06 Grupos | Pertenencia múltiple y permisos por grupo. | Sin ampliación necesaria para lo requerido. |
| R07 Temporadas | Fechas, estado, objetivos, fases y planes; histórico cerrado. | Competiciones. |
| R08 Fases | Configurables, objetivos y filtro de análisis por fase. | Sin ampliación necesaria para lo requerido. |
| R09 Planificación | Jerarquía completa, planes simultáneos, copia y adaptación individual. | Edición masiva avanzada. |
| R10 Tipos | Todos los base, incluido descanso y otro configurable. | Mayor especialización. |
| R11 Plantillas | Crear, editar, duplicar y reutilizar con revisiones. | Biblioteca avanzada. |
| R12 Sesiones | Metadatos completos y estados separados por sesión/asignación. | Sin ampliación necesaria para el flujo básico. |
| R13 Asignación | Seguimiento individual sobre sesión común. | Sin ampliación necesaria para lo requerido. |
| R14 Overrides | Ejercicio, parámetros, intensidad y bloques; original preservado. | Herramientas masivas. |
| R15 Gimnasio | Prescripción y resultados por serie. | Captura automática. |
| R16 Fuerza | Histórico/evolución básica y ejercicios de referencia. | Análisis avanzado. |
| R17 Agua/slalom | Objetivos, subtipos, bloques, mangas previstas y feedback. | Puertas, tiempos, dificultad y errores estructurados. |
| R18 Carrera/trail | Distancia, tiempo, ritmo, desnivel y RPE. | Parciales, segmentos y respuesta posterior estructurada. |
| R19 Ergómetro | Modelo, resistencia, distancia, tiempo, ritmo y RPE; potencia/cadencia opcionales. | Intervalos e importación. |
| R20 Tests | Definición/protocolo, captura manual y comparación contextual. | Protocolos compuestos e importación. |
| R21 Core | Series, reps, tiempo, lado, margen temporal y RIR opcional. | Análisis avanzado. |
| R22 Movilidad | Duración, zonas, lado y molestias. | Rigidez, asimetrías y sensación estructuradas. |
| R23 Feedback | Campos comunes completos con modo simplificado. | Ajustes según piloto. |
| R24 Recuperación | Registro diario opcional y evolución temporal. | Captura externa. |
| R25 Carga | sRPE, agregados, filtros y comparación semanal con cobertura. | Modelos adicionales. |
| R26 Fatiga | Indicadores separados; molestias y pendientes visibles. | Patrones y alertas configurables. |
| R27 Recomendaciones | Decisión manual del entrenador. | Propuestas con evidencia y aceptación explícita. |
| R28 Progresión | Historial para decidir y editar manualmente. | Propuestas de carga y aceptación/modificación/rechazo. |
| R29 Dashboard deportista | Hoy, próximas, estados, pendientes, carga, recuperación e historial/evolución. | Mayor profundidad analítica. |
| R30 Dashboard entrenador | Seguimiento grupal, carga, RPE, molestias y pendientes. | Alertas de patrones. |
| R31 Ficha individual | Calendario, historial y métricas básicas por tipo. | Análisis avanzado. |
| R32 Estadísticas | Filtros requeridos en las vistas donde aplican. | Informes personalizados. |
| R33 Calendario | Día/semana, mover por formulario, recurrencia semanal, cancelación y sustitución. | Arrastre y recurrencias avanzadas. |
| R34 Google Calendar | Posterior. | Sincronización opcional por usuario con deduplicación. |
| R35 PWA/móvil | Responsive, instalable, Safari/Chrome, adaptadores de plataforma. | Capacitor y publicación en tiendas. |
| R36 Notificaciones | Pendientes visibles dentro de la aplicación. | Push, email de actividad y preferencias. |
| R37 Salud/sensores | Posterior; puntos de integración definidos. | HealthKit, Watch, GPS, pulso, sueño y sensores. |
| R38 Privacidad | Perfiles privados, ámbito autorizado, minimización, exportación y eliminación. | Portal de tutor y consentimiento estructurado. |
| R39 Auditoría | Acciones deportivas y administrativas relevantes. | Revisión avanzada. |
| R40 Multi-club | Modelo, claves y consultas aisladas con pruebas de dos clubes. | Operación multi-club a largo plazo, independiente de la monetización. |

También quedan fuera chat, vídeo-análisis, rankings públicos, importaciones de Strava/Garmin y modelos predictivos complejos. Aplazar una funcionalidad deportiva no autoriza un atajo que impida implementarla después.

Pagos, suscripciones, facturación, tarifas y captación comercial no forman parte del alcance previsto para el club ni constituyen una siguiente fase comprometida. No se implementa preparación comercial en el MVP. Solo se reconsiderarán si en un futuro lejano se decide ofrecer la aplicación comercialmente a otros clubes.

## 9. Orden de implementación y puertas de salida

Cada entrega añade un recorrido verificable a la anterior. No basta con disponer de pantallas o tablas.

| Entrega | Trabajo | Condición para continuar |
| --- | --- | --- |
| E1 Base y acceso | Repositorio, entornos, migraciones, API/cliente, cuentas, club, roles, permisos y auditoría base. | Login, revocación y pruebas de aislamiento por club/rol. |
| E2 Estructura y planificación | Perfiles, grupos, categorías, temporada/fase/plan/microciclo/día, filtros y calendario inicial. | Previsualizar destinatarios autorizados y mantener planes simultáneos. |
| E3 Prescripción y publicación | Catálogos, tipos, bloques, plantillas versionadas, sesiones y asignaciones. | Publicar sesión grupal y verla desde dos cuentas con asignación independiente. |
| E4 Adaptación y calendario | Overrides, copia de planes, movimientos, cancelación, sustitución y recurrencias. | Modificar un destinatario sin afectar a otros ni perder la base. |
| E5 Ejecución y feedback | Resultados de tipos incluidos, borradores, envío, correcciones y modo infantil. | Completar recorrido móvil sin duplicar registros al reintentar. |
| E6 Seguimiento y evolución | Carga, recuperación, dashboards, historial, fuerza/tests y filtros. | Verificar métricas, ausencias, comparabilidad y recálculo tras correcciones. |
| E7 Preparación del piloto | PWA, accesibilidad, exportación/eliminación, copias/restauración, despliegue y E2E. | Cumplir escenarios y condiciones operativas. |

Las pruebas de dominio y permisos se incorporan con cada entrega. E7 integra y verifica; no pospone seguridad hasta el final.

## 10. Escenarios de aceptación verificables

Datos sintéticos: administrador, dos entrenadores con ámbitos distintos, al menos tres deportistas, dos grupos con un deportista compartido, K1/C1, dos planes y segundo club de prueba.

| ID | Escenario | Resultado exigido |
| --- | --- | --- |
| A01 | Invitar, activar, recuperar contraseña y desactivar membresía. | Acceso correcto, retirada inmediata de permisos e histórico conservado. |
| A02 | Deportista lee otra asignación; entrenador consulta grupo ajeno; usuario cambia club o ID en la petición. | Backend impide acceso, también en búsquedas, agregados y exportación. |
| A03 | Configurar categoría por temporada y combinar categoría + sexo + modalidad con grupo y personas explícitas. | Previsualización reproducible, permisos validados y cero duplicados. |
| A04 | Crear dos planes, microciclos/días y publicar sesión grupal. | Jerarquía/fechas válidas; cada deportista ve su asignación. |
| A05 | Duplicar plantilla y plan, cambiar plantilla original. | Nuevas identidades/prescripciones; sesiones existentes no cambian y no se copian resultados. |
| A06 | Cambiar ejercicio, carga y bloque para una persona. | Solo cambia su prescripción; se conservan original, adaptación y autor. |
| A07 | Registrar completada, parcial, omitida y dejar otra sin respuesta. | Estados/recuentos separados; sin respuesta no equivale a omisión. |
| A08 | Dos deportistas registran la misma sesión. | Ejecuciones/feedback independientes; uno no cierra la sesión del otro. |
| A09 | Enviar dos veces ejecución y editar desde dos pestañas con versiones distintas. | Un único registro lógico y conflicto explícito ante versión antigua. |
| A10 | Registrar 60 minutos con RPE 7; corregir a 45 minutos. | Carga pasa de 420 a 315, conserva corrección y actualiza agregados. |
| A11 | Parcial con duración sin RPE; descanso y otra sesión cancelada. | Carga parcial «sin datos»; descanso/cancelación excluidos de carga y denominador. |
| A12 | Editar sesión iniciada, cambiar grupos o categoría de temporada. | No cambia prescripción ejecutada, destinatarios ni contexto histórico. |
| A13 | Recurrencia semanal, cancelar una ocurrencia y editar futuras. | Sin duplicados ni reaparición de canceladas; ejecuciones/adaptaciones protegidas. |
| A14 | Mover sesión y sustituir asignación pendiente. | Fecha/jerarquía consistentes; reemplazo enlazado y original excluido de cumplimiento. |
| A15 | Registrar fuerza unilateral/isométrica, carrera, ergómetro, core, movilidad y agua. | Medidas/unidades propias, sin campos obligatorios incompatibles. |
| A16 | Comparar tests con distinto protocolo/resistencia y series incompatibles. | Histórico conservado, condiciones separadas y sin afirmar mejora equivalente. |
| A17 | Registrar/editar recuperación y no registrar al día siguiente. | Un registro por fecha, evolución correcta y ausencia sin imputar valores. |
| A18 | Filtrar dos grupos que comparten deportista. | No duplica asignaciones; medias, denominadores y cobertura visibles. |
| A19 | Móvil de 360 px, modo infantil, teclado y desconexión al enviar. | Flujo accesible, sin pérdida silenciosa ni confirmación falsa de guardado. |
| A20 | Semana con cambio horario y sesión realizada otro día. | Recurrencia conserva hora local; carga por realización y cumplimiento por fecha prevista. |
| A21 | Exportar/eliminar datos de usuario autorizado. | Datos propios sin compañeros; eliminación/anonimización coherente, trazable y sin romper otros historiales. |
| A22 | Desplegar desde cero, migrar y restaurar copia en entorno aislado. | Servicio operativo, datos consistentes y procedimiento documentado. |

## 11. Definición de MVP terminado

El MVP está terminado cuando E1–E7 están entregadas, A01–A22 verificadas y el club completa el flujo principal sin hojas de cálculo ni calendarios externos para sostenerlo. Deben existir datos persistentes, permisos y gestión de errores; las vistas simuladas no satisfacen la aceptación.

La entrega incluye instrucciones de instalación/despliegue, configuración de correo/secretos, migraciones, datos sintéticos, pruebas del flujo principal y procedimientos de copia/restauración y solicitudes de datos.

El piloto evaluará durante varias semanas si el entrenador planifica, adapta y revisa sin intervención técnica habitual, y si el deportista registra feedback desde móvil con rapidez. Las observaciones orientarán las ampliaciones sin alterar silenciosamente reglas de histórico, privacidad o cálculo.
