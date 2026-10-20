# Restringir consultas por identidad autorizada

## Fuente

Issue aprobado: [#10 — Restringir consultas de tareas y resumen por identidad autorizada](https://github.com/user-bcp-student14/workshop-requirements-api/issues/10).

Evidencia: `app/main.py:68-71` permite que el parámetro `owner` determine el filtro de tareas; `app/main.py:91-93` usa el mismo patrón en el resumen.

## Contexto actual

Los endpoints `GET /api/tasks` y `GET /api/summary` admiten un parámetro `owner`. Cuando se proporciona, se usa para elegir el conjunto de datos consultado, independientemente de que corresponda al usuario autenticado.

## Problema confirmado

La lógica observada no demuestra que el usuario autenticado esté autorizado a consultar un owner distinto, por lo que puede haber acceso cruzado a tareas o resúmenes.

## Comportamiento a preservar

- Sin parámetro `owner`, se consultan los datos del usuario autenticado.
- Se conservan las rutas, filtros y formas de respuesta vigentes para solicitudes autorizadas.
- Los accesos entre owners solo se permiten si una política aprobada los autoriza.

## Alcance

Definir y aplicar una política de autorización coherente al parámetro `owner` en `GET /api/tasks` y `GET /api/summary`.

## Fuera de alcance

Cambios al formato de token, reglas de creación de tareas, validación de carga de archivos y estructura de la base de datos.

## Criterios de aceptación

- Un usuario no obtiene tareas ni resumen de otro owner sin permiso explícito conforme a la política acordada.
- Se conserva el comportamiento de consulta propia cuando `owner` se omite.
- Las respuestas para consultas autorizadas conservan su estructura actual.
- Pruebas de integración cubren consulta propia, consulta de owner ajeno y cada excepción de rol que se apruebe.

## Contratos afectados/protegidos

Parámetro opcional `owner` y respuestas de `GET /api/tasks` y `GET /api/summary`.

## Riesgos, supuestos y preguntas abiertas

- Decisión aprobada: toda identidad, incluido `TRAINER`, solo puede consultar su propio owner.
- `POST /api/tasks` conserva el comportamiento existente para un `owner` explícito; su autorización de escritura queda fuera de este issue y requiere revisión independiente.
