# Contratos actuales de la API

La API escucha localmente en `http://127.0.0.1:8000`. Todos los endpoints
`/api/*` requieren `Authorization: Bearer <JWT>`.

## Autenticación

Los JWT se validan con RS256 y las claves publicadas por el JWKS de Quarkus.
Los valores esperados por defecto son:

| Configuración | Valor |
|---|---|
| `AUTH_JWKS_URL` | `http://127.0.0.1:8080/auth/.well-known/jwks.json` |
| `AUTH_TOKEN_ISSUER` | `workshop-auth-backend` |
| `AUTH_TOKEN_AUDIENCE` | `workshop-requirements-api` |

En contenedores, configurar `AUTH_JWKS_URL` con una URL interna alcanzable.
Un token ausente, mal formado, inválido, vencido, con issuer/audience
incorrectos o firmado con un algoritmo distinto de RS256 produce HTTP 401
con `{"detail":"Invalid token"}`. Si no se puede contactar el JWKS, la API
responde HTTP 503 con `{"detail":"Token verification service unavailable"}`.
No se acepta el token Base64 legado.

## GET /api/tasks

Devuelve las tareas de la identidad del token, ordenadas por id.

`owner` es opcional; si se proporciona debe coincidir exactamente con el
username del token. Un valor distinto produce HTTP 403.

Respuesta HTTP 200: lista de objetos con `id`, `title`, `description`,
`status`, `owner`, `priority` y `createdAt`.

## POST /api/tasks

Crea una tarea y responde HTTP 201 con el objeto creado. El cuerpo usa los
campos `title`, `description`, `status`, `priority` y, opcionalmente, `owner`.
Los valores por defecto son `TODO`, `MEDIUM` y el username autenticado,
respectivamente. Si `owner` se proporciona, se persiste ese valor tal como
llega; la restriccion de owner de issue #10 aplica a las consultas GET. La
respuesta tiene el mismo formato de objeto que
`GET /api/tasks`.

## GET /api/summary

Devuelve el resumen del username autenticado. `owner` es opcional y, si se
proporciona, debe coincidir exactamente con el username del token; un valor
distinto produce HTTP 403.

Respuesta HTTP 200: `owner`, `total`, `byStatus` y `highPriorityOpen`.

## POST /api/requirements

Recibe un archivo multipart en el campo `file`. Solo acepta un nombre directo
con extension `.md` (sin distinguir mayusculas) y contenido de hasta 100 bytes
inclusive. Los archivos aceptados producen HTTP 201 y una respuesta con
`owner`, `fileName`, `storedAt` y `size`.

- Nombre/ruta no permitido o extension distinta: HTTP 400,
  `{"detail":"Invalid file name"}`.
- Contenido mayor a 100 bytes: HTTP 413,
  `{"detail":"File exceeds the 100-byte limit"}`.

## GET /api/backend-health

Consulta el endpoint de salud Quarkus configurado mediante `AUTH_HEALTH_URL`
(por defecto `http://localhost:8080/q/health`). Responde HTTP 200 con
`requestedBy`, `status` y `body`; un fallo de conexion se informa dentro de
la respuesta como `status: 0`.
