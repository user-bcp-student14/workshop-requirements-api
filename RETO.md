# Reto — API FastAPI

Los contratos vigentes que hay que preservar están en `docs/ENDPOINTS.md`. Este
archivo conserva la lista historica de temas del laboratorio.

## Hallazgos sembrados

| Área | Caso | Objetivo |
|---|---|---|
| SCA | `urllib3 2.5.0` y `python-multipart 0.0.21` | Analizar CVEs y aplicar versiones corregidas. |
| Auth | Token Base64 con secreto embebido | Abordado: validar JWT RS256, issuer, audience, expiración y firma mediante JWKS. |
| Autorización | El cliente puede consultar otro `owner` | Abordado: consultas propias solamente. |
| SQL | Filtros e inserts concatenados | Abordado: consultas parametrizadas. |
| Files | Se conserva directamente `upload.filename` | Abordado: solo `.md`, nombre directo y máximo 100 bytes. |
| Arquitectura | Rutas, DB, reglas y serialización en un archivo | Separar capas. |
| Calidad | `dict`, excepciones amplias, condicionales y duplicación | Aplicar Pydantic, tipos y funciones pequeñas. |

No se incluyen payloads de explotación.
