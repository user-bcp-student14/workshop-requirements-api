# Workshop Requirements API — Python FastAPI

> **Laboratorio intencionalmente vulnerable.** Ejecutar únicamente en local, repositorios privados y ambientes aislados. No publicar en Internet ni desplegar en CERT/PROD.

API FastAPI que administra tareas del workshop y recibe archivos de requerimientos. Usa SQLite y consume el token emitido por el backend Quarkus.

## Ejecución

Requisitos: Python 3.13.

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Swagger: `http://localhost:8000/docs`

## Endpoints

- `GET /api/tasks`
- `POST /api/tasks`
- `GET /api/summary`
- `POST /api/requirements`
- `GET /api/backend-health`

La API valida JWT RS256 mediante el JWKS del backend Quarkus. Para integracion
local, issuer y audience esperados son `workshop-auth-backend` y
`workshop-requirements-api`. Se pueden configurar mediante
`AUTH_TOKEN_ISSUER`, `AUTH_TOKEN_AUDIENCE` y `AUTH_JWKS_URL`; esta ultima usa
por defecto `http://127.0.0.1:8080/auth/.well-known/jwks.json`. En contenedores,
`AUTH_JWKS_URL` debe apuntar a la URL interna alcanzable del servicio auth.
Un JWKS inaccesible produce HTTP 503; tokens invalidos o vencidos producen
HTTP 401. No se acepta el formato Base64 legado.

`GET /api/tasks` y `GET /api/summary` solo permiten consultar el owner de la
identidad autenticada; indicar otro owner produce HTTP 403. Las consultas SQL
usan valores de entrada como parametros.

`POST /api/requirements` acepta nombres directos con extension `.md` (sin
distinguir mayusculas) y hasta 100 bytes inclusive. Nombre no permitido
produce HTTP 400; superar el limite produce HTTP 413. Los contratos estan en
[docs/ENDPOINTS.md](docs/ENDPOINTS.md).
