# Aceptar el token emitido por Quarkus

## Fuente

Issue aprobado: [#12 — Alinear validación de tokens con el JWT emitido por Quarkus](https://github.com/user-bcp-student14/workshop-requirements-api/issues/12).

Evidencia: `app/main.py:17-26` interpreta el header Bearer como Base64 con formato legado y secreto fijo. El backend emite JWT RS256 según `workshop-auth-backend/src/main/java/com/bcp/workshop/auth/TokenService.java:50-54`. El frontend reenvía el token en `workshop-login-frontend/src/app/dashboard/dashboard.component.ts:43-44`.

## Contexto actual

Los handlers protegidos de esta API dependen de `legacy_identity`. El flujo cliente obtiene el token de Quarkus y lo envía como Bearer, pero el formato que esta API espera no coincide con el token emitido.

## Problema confirmado

Una respuesta de login válida puede no autenticar las llamadas protegidas a esta API, impidiendo completar el flujo integrado.

## Comportamiento a preservar

- Los endpoints protegidos siguen requiriendo autenticación.
- Tokens inválidos o expirados no conceden acceso.
- Las rutas y formas de respuesta de los endpoints protegidos no cambian como efecto implícito de la alineación.
- No se conserva un fallback inseguro al formato legado.

## Alcance

Establecer que esta API valide el contrato del token emitido por Quarkus y que exista una prueba de integración del flujo de autenticación con un consumidor configurado.

## Fuera de alcance

Cambios al endpoint de login, política de autorización por owner/rol, persistencia de tareas y cambios visuales del frontend.

## Criterios de aceptación

- Un token vigente emitido por el backend configurado permite el acceso autenticado a endpoints protegidos de esta API.
- Tokens inválidos, expirados o con issuer/audience no aceptados son rechazados.
- Las pruebas verifican aceptación y rechazo sin claves privadas, credenciales reales ni secretos incorporados al repositorio.
- Se conserva el contrato de las respuestas de los endpoints protegidos para solicitudes autorizadas.

## Contratos afectados/protegidos

Header `Authorization: Bearer` para `GET /api/tasks`, `POST /api/tasks`, `GET /api/summary`, `POST /api/requirements` y `GET /api/backend-health`. Los endpoints y cuerpos existentes deben permanecer documentados.

## Riesgos, supuestos y preguntas abiertas

- Decisiones aprobadas: validación por JWKS, issuer `workshop-auth-backend` y audience `workshop-requirements-api`.
- URL local de JWKS: `http://127.0.0.1:8080/auth/.well-known/jwks.json`; en contenedores se configura la URL interna alcanzable.
- Confirmar si otros consumidores dependen del formato legado antes de retirarlo.
- Esta especificación debe permanecer alineada con las copias del issue #12 en backend y frontend.
