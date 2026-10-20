# Tratar los valores de entrada como datos SQL

## Fuente

Issue aprobado: [#11 — Parametrizar consultas SQL con valores de entrada](https://github.com/user-bcp-student14/workshop-requirements-api/issues/11).

Evidencia: `app/main.py:70-71` concatena `owner` en `GET /api/tasks`; `app/main.py:84-85` concatena campos de `POST /api/tasks`; `app/main.py:93` concatena `owner` en `GET /api/summary`.

## Contexto actual

Varias consultas SQLite se construyen concatenando valores recibidos en parámetros HTTP o en el cuerpo de creación de tareas.

## Problema confirmado

La concatenación puede hacer que entradas con caracteres especiales se interpreten como parte de la consulta en lugar de valores, y puede provocar resultados o errores no previstos.

## Comportamiento a preservar

- Se mantienen rutas, códigos de éxito, filtros y estructura de respuesta para entradas válidas.
- Los valores se persisten y consultan con los mismos significados funcionales acordados.
- El alcance de cada consulta permanece limitado al resultado esperado por la solicitud autorizada.

## Alcance

Eliminar la interpretación de valores de entrada como sintaxis SQL en consultas de tareas y resumen identificadas en la evidencia.

## Fuera de alcance

Cambios de esquema, motor de base de datos, autorización de usuarios, validación de archivos y cambios funcionales en los endpoints.

## Criterios de aceptación

- Los valores que provienen de owner y del cuerpo de creación se procesan como datos, no alteran la sintaxis de las consultas.
- Los endpoints `GET /api/tasks`, `POST /api/tasks` y `GET /api/summary` conservan los contratos para entradas válidas.
- Pruebas de integración con una base temporal cubren comillas y caracteres especiales y comprueban que los resultados se limitan a los datos esperados.
- Un fallo al procesar una entrada no produce modificaciones parciales no previstas en la base.

## Contratos afectados/protegidos

`GET /api/tasks`, `POST /api/tasks`, `GET /api/summary` y persistencia SQLite vigente.

## Riesgos, supuestos y preguntas abiertas

- No se requiere cambio de contrato HTTP según la evidencia disponible.
- Las pruebas deben usar datos sintéticos y una base temporal.
