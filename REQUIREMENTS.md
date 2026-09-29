# Requerimientos

## 1. Alcance del producto final

La aplicación será una plataforma de planificación, ejecución, seguimiento y análisis del entrenamiento de piragüismo slalom para clubes.

La prioridad es el uso interno del club promotor, sin objetivo de monetizar ese uso. Deben primar la utilidad deportiva, la facilidad de mantenimiento y un coste de operación asumible.

Debe poder utilizarse inicialmente en un club y evolucionar posteriormente a una plataforma multi-club. La ampliación a otros clubes es una posibilidad a largo plazo; una eventual monetización para esos clubes es una decisión independiente, muy a futuro y sin compromiso de implementación. No se requieren pagos, suscripciones, facturación ni funcionalidades comerciales para el club promotor.

La aplicación debe cubrir:

- planificación deportiva;
- creación de entrenamientos;
- asignación por categorías y grupos;
- adaptación individual;
- ejecución y feedback del deportista;
- carga y recuperación;
- evolución del rendimiento;
- gestión de temporadas;
- estadísticas;
- integraciones externas.

---

# 2. Usuarios y roles

## 2.1 Deportista

Debe poder:

- disponer de una cuenta propia;
- consultar su calendario de entrenamientos;
- consultar el contenido de cada sesión;
- marcar una sesión como realizada;
- marcar una sesión como parcialmente realizada;
- marcar una sesión como no realizada;
- registrar resultados reales;
- registrar RPE;
- registrar molestias;
- registrar feedback;
- consultar su historial;
- consultar su evolución;
- consultar su carga;
- consultar sus métricas de recuperación.

## 2.2 Entrenador

Debe poder:

- disponer de una cuenta de entrenador;
- crear entrenamientos;
- modificar entrenamientos;
- crear plantillas;
- duplicar plantillas;
- organizar entrenamientos en bloques;
- crear planificaciones;
- asignar entrenamientos a categorías;
- asignar entrenamientos a grupos;
- asignar entrenamientos a deportistas concretos;
- crear adaptaciones individuales;
- consultar quién completó un entrenamiento;
- consultar quién lo realizó parcialmente;
- consultar quién no lo realizó;
- consultar feedback;
- consultar RPE;
- consultar molestias;
- consultar carga;
- consultar evolución individual;
- consultar evolución grupal;
- reorganizar calendarios;
- gestionar sesiones recurrentes;
- consultar alertas de seguimiento.

## 2.3 Administrador de club

Debe poder:

- crear y desactivar cuentas;
- gestionar deportistas;
- gestionar entrenadores;
- gestionar grupos;
- gestionar categorías;
- gestionar temporadas;
- configurar modalidades;
- configurar permisos;
- gestionar pertenencia a grupos;
- gestionar estado de usuarios;
- consultar auditoría administrativa.

## 2.4 Tutor

Rol futuro.

Debe poder añadirse sin rediseñar el dominio.

Posibles funciones futuras:

- consentimiento;
- consulta limitada;
- gestión de datos del menor;
- recepción de avisos;
- autorización de determinados tratamientos de datos.

---

# 3. Clubes

La plataforma final debe soportar múltiples clubes.

Cada club debe disponer de:

- usuarios;
- deportistas;
- entrenadores;
- grupos;
- categorías;
- temporadas;
- planificaciones;
- entrenamientos;
- estadísticas;
- configuración independiente.

Los datos de un club no deben ser visibles desde otro club sin autorización explícita.

---

# 4. Perfil deportivo

Cada deportista debe poder tener:

- nombre;
- fecha de nacimiento;
- categoría de edad;
- sexo competitivo;
- modalidad/es;
- grupo/s;
- estado deportivo;
- entrenador/es asociados;
- historial deportivo;
- observaciones autorizadas.

Modalidades iniciales:

- K1;
- C1.

Un deportista puede practicar más de una modalidad.

---

# 5. Categorías

Las planificaciones deben poder segmentarse por:

- edad/categoría;
- sexo;
- modalidad;
- grupo;
- deportistas concretos.

Las categorías de edad deben poder configurarse por temporada.

No deben depender de nombres fijos definidos en código.

Debe ser posible combinar criterios.

Ejemplos:

- Cadete masculino K1;
- Cadete femenino K1;
- Junior C1;
- Infantil completo;
- Grupo tecnificación;
- deportistas concretos de diferentes categorías.

---

# 6. Grupos

Debe ser posible crear grupos manuales.

Ejemplos:

- iniciación;
- competición;
- tecnificación;
- grupo tardes;
- grupo de agua;
- grupo de gimnasio.

Un deportista puede pertenecer a varios grupos.

Un entrenador puede estar autorizado únicamente para grupos concretos.

---

# 7. Temporadas

Debe poder crearse una temporada deportiva.

Una temporada debe contener:

- fecha de inicio;
- fecha de fin;
- fases;
- planificaciones;
- objetivos;
- competiciones futuras;
- estado.

---

# 8. Fases de entrenamiento

Debe soportar fases configurables.

Fases iniciales:

- adaptación;
- fuerza general;
- hipertrofia;
- fuerza máxima;
- potencia/explosividad;
- puesta a punto;
- competición.

Debe poder analizarse el rendimiento por fase.

---

# 9. Planificación

Debe soportar:

```text
Temporada
    ↓
Fase
    ↓
Plan
    ↓
Semana / microciclo
    ↓
Día
    ↓
Sesión
```

Debe poder mantenerse más de una planificación simultánea para distintas categorías o grupos.

Debe poder reutilizarse una planificación como base para otra.

Debe poder existir:

- plan general;
- plan por categoría;
- plan por modalidad;
- plan por sexo;
- plan por grupo;
- override individual.

---

# 10. Tipos de entrenamiento

Debe soportar como mínimo:

- agua/slalom;
- gimnasio;
- carrera/trail;
- ergómetro;
- core;
- movilidad/estiramientos;
- test;
- recuperación;
- descanso;
- otro configurable.

---

# 11. Plantillas

Los entrenadores deben poder crear plantillas reutilizables.

Una plantilla puede contener:

- título;
- objetivo;
- tipo;
- bloques;
- ejercicios;
- volumen;
- intensidad;
- descansos;
- notas.

Modificar una plantilla no debe modificar sesiones históricas ya realizadas.

Debe existir versionado lógico o snapshots.

---

# 12. Sesiones

Cada sesión debe incluir:

- fecha;
- hora;
- duración prevista;
- tipo;
- objetivo;
- instrucciones;
- entrenador;
- destinatarios;
- bloques;
- contenido específico.

Estados:

- planificada;
- realizada;
- parcial;
- omitida;
- cancelada;
- sustituida.

---

# 13. Asignación

Una sesión creada para un grupo debe generar seguimiento independiente por deportista.

Cada deportista debe poder tener:

- estado propio;
- feedback propio;
- resultados propios;
- override propio.

La sesión común no debe duplicarse innecesariamente.

---

# 14. Overrides individuales

Un entrenador debe poder cambiar para un deportista:

- ejercicio;
- series;
- repeticiones;
- carga;
- distancia;
- duración;
- intensidad;
- bloque completo.

La aplicación debe conservar:

- prescripción original;
- modificación;
- ejecución real.

---

# 15. Gimnasio

Debe permitir registrar:

- ejercicio;
- orden;
- series;
- repeticiones;
- carga;
- RIR;
- RPE cuando corresponda;
- descanso;
- tiempo;
- distancia;
- lado;
- observaciones.

Debe soportar:

- ejercicios bilaterales;
- ejercicios unilaterales;
- isométricos;
- ejercicios por tiempo;
- ejercicios por distancia.

---

# 16. Historial de fuerza

Debe mostrar evolución por ejercicio de:

- peso;
- repeticiones;
- RIR;
- volumen;
- mejores marcas;
- tendencia.

Debe permitir definir ejercicios de referencia.

---

# 17. Agua / slalom

Debe poder registrar:

- duración;
- objetivo;
- calentamiento;
- bloques;
- mangas;
- puertas;
- tiempos;
- dificultad;
- RPE;
- errores técnicos;
- observaciones;
- contenido técnico.

Debe diferenciar sesiones como:

- técnica;
- base;
- intensidad;
- simulación de competición;
- trabajo específico.

---

# 18. Carrera / trail

Debe poder registrar:

- distancia;
- tiempo;
- ritmo;
- desnivel positivo;
- parciales;
- RPE global;
- RPE por segmentos;
- observaciones;
- respuesta posterior.

---

# 19. Ergómetro

Debe poder registrar:

- modelo;
- drag/resistencia;
- distancia;
- tiempo;
- ritmo;
- potencia;
- cadencia;
- RPE;
- intervalos;
- observaciones.

---

# 20. Tests

Debe permitir crear tests configurables.

Inicialmente:

- 200 m;
- 500 m;
- 1000 m.

Cada resultado debe poder asociarse a:

- deportista;
- fecha;
- máquina;
- resistencia;
- protocolo;
- tiempo;
- potencia;
- cadencia;
- RPE;
- observaciones.

Debe permitir comparación histórica válida.

---

# 21. Core

Debe soportar:

- repeticiones;
- tiempo;
- lado;
- series;
- margen temporal;
- RIR cuando aplique;
- observaciones.

---

# 22. Movilidad

Debe poder registrar:

- duración;
- zonas;
- lado;
- rigidez;
- asimetrías;
- molestias;
- sensación de movilidad.

Zonas relevantes:

- isquios;
- cadera;
- lumbar/lumbopélvica;
- torácica;
- dorsal;
- pectoral;
- flexores de cadera;
- gemelo;
- sóleo;
- aductores;
- glúteos.

---

# 23. Feedback

Después de una sesión, el deportista debe poder registrar rápidamente:

- completada / parcial / no realizada;
- RPE;
- sensación general;
- calidad técnica;
- fatiga muscular;
- dolor/molestias;
- zona de molestia;
- comentario.

Para usuarios infantiles debe existir una interfaz simplificada.

---

# 24. Readiness y recuperación

Debe permitir un registro diario opcional de:

- sueño;
- fatiga;
- agujetas;
- motivación;
- energía;
- dolor;
- zona;
- comentarios.

Debe mostrar evolución temporal.

---

# 25. Carga

Debe calcular al menos:

```text
sRPE = minutos × RPE
```

Debe poder obtener carga por:

- sesión;
- día;
- semana;
- deportista;
- grupo;
- disciplina;
- tipo de sesión;
- fase.

Debe mostrar tendencias y comparación con semanas previas.

No debe presentar una cifra de carga como diagnóstico médico.

---

# 26. Fatiga

La aplicación no debe reducir la fatiga a una única métrica obligatoria.

Debe presentar por separado:

- carga;
- recuperación;
- rendimiento;
- molestias.

Debe poder detectar patrones como:

- caída de rendimiento;
- aumento de RPE;
- aumento de fatiga;
- mala recuperación;
- molestias repetidas;
- carga elevada mantenida.

---

# 27. Recomendaciones

La aplicación puede generar recomendaciones como:

- mantener;
- reducir volumen;
- reducir intensidad;
- modificar sesión;
- descansar;
- realizar descarga;
- progresar carga;
- mantener carga.

Las recomendaciones nunca deben modificar automáticamente la planificación sin confirmación de un entrenador autorizado.

---

# 28. Progresión

Para ejercicios de fuerza debe poder proponerse progresión en función de:

- carga;
- reps;
- RIR;
- técnica;
- cumplimiento;
- historial.

El entrenador puede:

- aceptar;
- modificar;
- rechazar.

---

# 29. Dashboard del deportista

Debe mostrar:

- entrenamiento de hoy;
- próximos entrenamientos;
- estado de realización;
- feedback pendiente;
- carga semanal;
- recuperación;
- historial;
- evolución.

---

# 30. Dashboard del entrenador

Debe mostrar por grupo y sesión:

- número de deportistas;
- completados;
- parciales;
- no realizados;
- sin feedback;
- RPE medio;
- molestias reportadas;
- carga;
- deportistas que requieren atención.

Debe permitir entrar al detalle de cada deportista.

---

# 31. Dashboard individual del entrenador

Debe mostrar:

- calendario;
- historial;
- carga;
- recuperación;
- evolución de fuerza;
- agua;
- carrera;
- ergómetro;
- tests;
- molestias;
- feedback.

---

# 32. Estadísticas

Debe permitir filtrar por:

- deportista;
- grupo;
- categoría;
- sexo;
- modalidad;
- semana;
- mes;
- temporada;
- fase;
- tipo de entrenamiento;
- ejercicio.

---

# 33. Calendario

La aplicación debe disponer de calendario propio.

Debe soportar:

- día;
- semana;
- cambios de horario;
- arrastrar o mover sesiones;
- recurrencias;
- cancelaciones;
- sesiones por grupo;
- sesiones individuales.

---

# 34. Google Calendar

Integración futura/avanzada por usuario.

Debe permitir:

- exportar/sincronizar sesiones;
- actualizar cambios relevantes;
- evitar duplicados;
- mantener IDs externos.

Google Calendar no será la fuente de verdad del producto.

---

# 35. PWA y móvil

La aplicación debe ser:

- responsive;
- mobile-first;
- instalable como PWA;
- usable desde Safari/Chrome;
- convertible a Android mediante Capacitor;
- convertible a iOS mediante Capacitor.

La aplicación móvil no debe requerir reescribir el frontend.

---

# 36. Notificaciones

Debe poder añadirse posteriormente:

- aviso de nuevo entrenamiento;
- cambio de horario;
- feedback pendiente;
- sesión próxima;
- alerta de entrenador;
- recuperación pendiente.

---

# 37. Health y sensores

Arquitectura preparada para integrar posteriormente:

- Apple Health;
- HealthKit;
- Apple Watch;
- frecuencia cardiaca;
- sueño;
- GPS;
- sensores deportivos;
- potencia/cadencia.

No forman parte obligatoria del primer MVP.

---

# 38. Privacidad

Por trabajar con menores:

- los perfiles no serán públicos por defecto;
- no existirán rankings públicos por defecto;
- cada entrenador solo verá deportistas autorizados;
- se minimizarán datos personales;
- se registrarán operaciones sensibles;
- se podrá eliminar/exportar información;
- se podrá incorporar consentimiento de tutor;
- se podrá incorporar rol de tutor.

---

# 39. Auditoría

Debe registrarse en acciones relevantes:

- usuario;
- acción;
- recurso;
- fecha/hora.

Especialmente:

- cambios de planificación;
- cambios de permisos;
- modificación de deportistas;
- modificaciones administrativas.

---

# 40. Multi-club

La versión final debe poder soportar:

```text
Club A
├── deportistas
├── entrenadores
├── grupos
└── planes

Club B
├── deportistas
├── entrenadores
├── grupos
└── planes
```

Debe existir aislamiento de datos entre clubes.

El desarrollo inicial no necesita ofrecer todavía alta pública de nuevos clubes.
