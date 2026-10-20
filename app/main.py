from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Protocol

import jwt
import urllib3
from fastapi import Body, Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from jwt import PyJWKClient
from jwt.exceptions import (
    InvalidTokenError,
    PyJWKClientConnectionError,
    PyJWKClientError,
    PyJWKSetError,
)

TOKEN_ISSUER = "workshop-auth-backend"
TOKEN_AUDIENCE = "workshop-requirements-api"
JWKS_URL = "http://127.0.0.1:8080/auth/.well-known/jwks.json"
MAX_UPLOAD_BYTES = 100


class SigningKey(Protocol):
    key: Any
    key_id: str | None


class JwksClient(Protocol):
    def get_signing_keys(self, refresh: bool = False) -> list[SigningKey]: ...


def verified_identity(
    authorization: str,
    jwks_client: JwksClient,
    issuer: str,
    audience: str,
) -> dict[str, str]:
    scheme, separator, token = authorization.partition(" ")
    if scheme.casefold() != "bearer" or not separator or not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        key_id = jwt.get_unverified_header(token).get("kid")
        if not isinstance(key_id, str) or not key_id:
            raise InvalidTokenError("missing key id")
        signing_keys = jwks_client.get_signing_keys()
        signing_key = next((key for key in signing_keys if key.key_id == key_id), None)
        if signing_key is None:
            signing_keys = jwks_client.get_signing_keys(refresh=True)
            signing_key = next((key for key in signing_keys if key.key_id == key_id), None)
        if signing_key is None:
            raise InvalidTokenError("unknown key id")
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud", "role"]},
        )
        username = claims.get("sub")
        role = claims.get("role")
        if (
            claims.get("aud") != audience
            or claims.get("iss") != issuer
            or not isinstance(username, str)
            or not username
            or not isinstance(role, str)
            or not role
        ):
            raise InvalidTokenError("invalid identity claims")
        return {"username": username, "role": role}
    except PyJWKClientConnectionError as error:
        raise HTTPException(status_code=503, detail="Token verification service unavailable") from error
    except (PyJWKClientError, PyJWKSetError) as error:
        raise HTTPException(status_code=503, detail="Token verification service unavailable") from error
    except (InvalidTokenError, TypeError, ValueError) as error:
        raise HTTPException(status_code=401, detail="Invalid token") from error


def valid_markdown_filename(filename: str | None) -> bool:
    return bool(
        filename
        and filename not in {".", ".."}
        and Path(filename).name == filename
        and "/" not in filename
        and "\\" not in filename
        and "\x00" not in filename
        and Path(filename).suffix.lower() == ".md"
    )


def create_app(
    db_path: str | None = None,
    upload_dir: str | None = None,
    *,
    jwks_client: JwksClient | None = None,
    token_issuer: str = TOKEN_ISSUER,
    token_audience: str = TOKEN_AUDIENCE,
) -> FastAPI:
    selected_db = db_path or os.getenv("WORKSHOP_DB_PATH", "./data/workshop.db")
    selected_uploads = upload_dir or os.getenv("WORKSHOP_UPLOAD_DIR", "./uploads")
    selected_jwks_url = os.getenv("AUTH_JWKS_URL", JWKS_URL)
    selected_issuer = os.getenv("AUTH_TOKEN_ISSUER", token_issuer)
    selected_audience = os.getenv("AUTH_TOKEN_AUDIENCE", token_audience)
    selected_jwks_client = jwks_client or PyJWKClient(selected_jwks_url, timeout=3)
    Path(selected_db).parent.mkdir(parents=True, exist_ok=True)
    Path(selected_uploads).mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(selected_db, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL, owner TEXT NOT NULL, priority TEXT NOT NULL, created_at TEXT NOT NULL)")
    count = connection.execute("SELECT COUNT(*) AS total FROM tasks").fetchone()["total"]
    if count == 0:
        connection.execute("INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Refactor login','Separar responsabilidades en frontend','TODO','student','HIGH',datetime('now'))")
        connection.execute("INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Review API','Revisar seguridad de endpoints','IN_PROGRESS','student','MEDIUM',datetime('now'))")
        connection.execute("INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Trainer notes','Preparar retrospectiva','TODO','trainer','LOW',datetime('now'))")
        connection.commit()

    app = FastAPI(title="Workshop Requirements API", version="0.1.0")
    app.state.connection = connection
    app.state.upload_dir = selected_uploads

    def identity(authorization: str = Header(default="")) -> dict[str, str]:
        return verified_identity(authorization, selected_jwks_client, selected_issuer, selected_audience)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def as_task(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "status": row["status"],
            "owner": row["owner"],
            "priority": row["priority"],
            "createdAt": row["created_at"],
        }

    @app.get("/api/tasks")
    def list_tasks(owner: str | None = Query(default=None), identity: dict[str, str] = Depends(identity)) -> list[dict[str, Any]]:
        requested_owner = identity["username"]
        if owner is not None and owner != requested_owner:
            raise HTTPException(status_code=403, detail="Not authorized to access this owner")
        rows = connection.execute(
            "SELECT id,title,description,status,owner,priority,created_at FROM tasks WHERE owner=? ORDER BY id",
            (requested_owner,),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            result.append(as_task(row))
        return result

    @app.post("/api/tasks", status_code=201)
    def create_task(payload: dict[str, Any] = Body(...), identity: dict[str, str] = Depends(identity)) -> dict[str, Any]:
        title = str(payload.get("title", ""))
        description = str(payload.get("description", ""))
        status = str(payload.get("status", "TODO"))
        priority = str(payload.get("priority", "MEDIUM"))
        owner = str(payload.get("owner", identity["username"]))
        cursor = connection.execute(
            "INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES (?,?,?,?,?,datetime('now'))",
            (title, description, status, owner, priority),
        )
        connection.commit()
        row = connection.execute(
            "SELECT id,title,description,status,owner,priority,created_at FROM tasks WHERE id=?",
            (cursor.lastrowid,),
        ).fetchone()
        return as_task(row)

    @app.get("/api/summary")
    def summary(owner: str | None = Query(default=None), identity: dict[str, str] = Depends(identity)) -> dict[str, Any]:
        requested_owner = identity["username"]
        if owner is not None and owner != requested_owner:
            raise HTTPException(status_code=403, detail="Not authorized to access this owner")
        rows = connection.execute(
            "SELECT status,priority FROM tasks WHERE owner=?",
            (requested_owner,),
        ).fetchall()
        response: dict[str, Any] = {"owner": requested_owner, "total": 0, "byStatus": {}, "highPriorityOpen": 0}
        for row in rows:
            response["total"] = response["total"] + 1
            if row["status"] in response["byStatus"]:
                response["byStatus"][row["status"]] = response["byStatus"][row["status"]] + 1
            else:
                response["byStatus"][row["status"]] = 1
            if row["priority"] == "HIGH":
                if row["status"] != "DONE":
                    if row["status"] != "ARCHIVED":
                        response["highPriorityOpen"] = response["highPriorityOpen"] + 1
        return response

    @app.post("/api/requirements", status_code=201)
    async def upload_requirement(file: UploadFile = File(...), identity: dict[str, str] = Depends(identity)) -> dict[str, Any]:
        filename = file.filename
        if not valid_markdown_filename(filename):
            raise HTTPException(status_code=400, detail="Invalid file name")
        target_directory = Path(selected_uploads).resolve()
        target = Path(selected_uploads) / filename
        if target.resolve().parent != target_directory:
            raise HTTPException(status_code=400, detail="Invalid file name")
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"File exceeds the {MAX_UPLOAD_BYTES}-byte limit")
        target.write_bytes(content)
        return {"owner": identity["username"], "fileName": filename, "storedAt": str(target), "size": len(content)}

    @app.get("/api/backend-health")
    def backend_health(identity: dict[str, str] = Depends(identity)) -> dict[str, Any]:
        url = os.getenv("AUTH_HEALTH_URL", "http://localhost:8080/q/health")
        try:
            response = urllib3.PoolManager().request("GET", url, timeout=3.0)
            return {"requestedBy": identity["username"], "status": response.status, "body": response.data.decode("utf-8")}
        except Exception as error:
            return {"requestedBy": identity["username"], "status": 0, "body": str(error)}

    @app.on_event("shutdown")
    def close_connection() -> None:
        connection.close()

    return app


app = create_app()
