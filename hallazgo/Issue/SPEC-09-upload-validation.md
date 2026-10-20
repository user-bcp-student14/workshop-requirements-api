# Validar nombre y tamaño de archivos cargados

## Fuente

Issue aprobado: [#9 — Validar nombre y tamaño de archivos cargados](https://github.com/user-bcp-student14/workshop-requirements-api/issues/9).

Evidencia: `app/main.py:107-112`; el handler forma el destino con `file.filename`, lee el contenido completo y lo escribe.

## Contexto actual

`POST /api/requirements` recibe un archivo multipart y guarda su contenido bajo el directorio de cargas usando el nombre proporcionado por el cliente.

## Problema confirmado

El handler no muestra validación del nombre/ruta ni un límite de tamaño antes de leer el archivo completo. No queda garantizado que el destino se mantenga en el directorio previsto ni que el consumo de memoria y almacenamiento tenga un límite acordado.

## Comportamiento a preservar

- La carga aceptada conserva `POST /api/requirements` y el código HTTP 201.
- La respuesta de una carga aceptada conserva los campos `owner`, `fileName`, `storedAt` y `size`, salvo cambio de contrato aprobado explícitamente.
- El archivo aceptado queda disponible en el directorio de cargas configurado.

## Alcance

Definir y aplicar una política verificable para nombres y tamaño de archivos aceptados por este endpoint.

## Fuera de alcance

Análisis antivirus, procesamiento semántico del documento, cambios de autenticación y cambios al modelo de tareas.

## Criterios de aceptación

- Los nombres aceptados no permiten que el archivo se escriba fuera del directorio de cargas configurado.
- El límite máximo de tamaño es explícito y los archivos que lo exceden se rechazan conforme a una respuesta acordada.
- El rechazo de un archivo demasiado grande no requiere acumular el archivo completo en memoria.
- Las cargas válidas mantienen el código y la forma de respuesta establecidos.
- Pruebas con directorios temporales verifican nombres válidos/no válidos, tamaño límite y ausencia de escrituras fuera del directorio.

## Contratos afectados/protegidos

Request multipart `file` y respuesta de `POST /api/requirements`.

## Riesgos, supuestos y preguntas abiertas

- Decisión aprobada: máximo inclusivo de 100 bytes y únicamente extensión `.md` (sin distinguir mayúsculas).
- Decisión aprobada: HTTP 400 por nombre/extensión no permitidos y HTTP 413 por superar el tamaño máximo.
- Las pruebas deben usar archivos y rutas temporales; no modificar archivos ajenos al directorio temporal.
