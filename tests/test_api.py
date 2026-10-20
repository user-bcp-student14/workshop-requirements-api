import base64
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.exceptions import PyJWKClientConnectionError

from app.main import create_app

ISSUER = "workshop-auth-backend"
AUDIENCE = "workshop-requirements-api"
KEY_ID = "test-rsa-key"
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class StubJwksClient:
    def __init__(self, public_key=PRIVATE_KEY.public_key(), connection_error=False):
        self.public_key = public_key
        self.connection_error = connection_error

    def get_signing_keys(self, refresh: bool = False) -> list[SimpleNamespace]:
        if self.connection_error:
            raise PyJWKClientConnectionError("test connection error")
        return [SimpleNamespace(key=self.public_key, key_id=KEY_ID)]


def token(
    username: str = "student",
    role: str = "STUDENT",
    *,
    signing_key=PRIVATE_KEY,
    key_id: str = KEY_ID,
    **overrides,
) -> str:
    now = int(time.time())
    claims = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + 3600,
        "iss": ISSUER,
        "aud": AUDIENCE,
    }
    claims.update(overrides)
    return jwt.encode(claims, signing_key, algorithm="RS256", headers={"kid": key_id})


def headers(username: str = "student", role: str = "STUDENT", **overrides) -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role, **overrides)}"}


def create_test_app(
    tmp_path: Path,
    *,
    jwks_client: StubJwksClient | None = None,
):
    return create_app(
        str(tmp_path / "workshop.db"),
        str(tmp_path / "uploads"),
        jwks_client=jwks_client or StubJwksClient(),
        token_issuer=ISSUER,
        token_audience=AUDIENCE,
    )


def test_lists_seeded_tasks(tmp_path: Path) -> None:
    app = create_test_app(tmp_path)
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_creates_task_with_quoted_values_and_summarizes(tmp_path: Path) -> None:
    app = create_test_app(tmp_path)
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={
                "title": "Planner's task",
                "description": "Preserve 'quoted' text",
                "status": "TODO",
                "priority": "HIGH",
                "owner": "planner's team",
            },
        )
        summary = client.get("/api/summary", headers=headers())
    assert created.status_code == 201
    assert created.json()["title"] == "Planner's task"
    assert created.json()["description"] == "Preserve 'quoted' text"
    assert created.json()["owner"] == "planner's team"
    assert summary.json()["total"] == 2


def test_owner_filters_are_bound_values(tmp_path: Path) -> None:
    crafted_username = "student' OR '1'='1"
    app = create_test_app(tmp_path)
    with TestClient(app) as client:
        tasks = client.get("/api/tasks", params={"owner": crafted_username}, headers=headers(crafted_username))
        summary = client.get("/api/summary", params={"owner": crafted_username}, headers=headers(crafted_username))
    assert tasks.status_code == 200
    assert tasks.json() == []
    assert summary.status_code == 200
    assert summary.json()["total"] == 0


@pytest.mark.parametrize("endpoint", ["/api/tasks", "/api/summary"])
@pytest.mark.parametrize(
    ("username", "role", "other_owner"),
    [("student", "STUDENT", "trainer"), ("trainer", "TRAINER", "student")],
)
def test_rejects_queries_for_another_owner(
    endpoint: str,
    username: str,
    role: str,
    other_owner: str,
    tmp_path: Path,
) -> None:
    app = create_test_app(tmp_path)
    with TestClient(app) as client:
        response = client.get(endpoint, params={"owner": other_owner}, headers=headers(username, role))
    assert response.status_code == 403


def test_uploads_markdown_file_at_the_maximum_size(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_test_app(tmp_path)
    content = b"a" * 100
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.md", content, "text/markdown")},
        )
    assert response.status_code == 201
    assert response.json()["size"] == 100
    assert (upload_dir / "requirements.md").read_bytes() == content


@pytest.mark.parametrize("filename", ["../outside.md", "..\\outside.md", "requirements.txt"])
def test_rejects_unsafe_names_and_non_markdown_files(filename: str, tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_test_app(tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": (filename, b"content", "text/markdown")},
        )
    assert response.status_code == 400
    assert list(upload_dir.iterdir()) == []
    assert not (tmp_path / "outside.md").exists()


def test_rejects_uploads_larger_than_one_hundred_bytes(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_test_app(tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.md", b"a" * 101, "text/markdown")},
        )
    assert response.status_code == 413
    assert response.json()["detail"] == "File exceeds the 100-byte limit"
    assert list(upload_dir.iterdir()) == []


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": int(time.time()) - 1},
        {"iss": "unexpected-issuer"},
        {"aud": "another-service"},
    ],
)
def test_rejects_expired_or_wrong_audience_tokens(claims: dict[str, object], tmp_path: Path) -> None:
    app = create_test_app(tmp_path)
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers(**claims))
    assert response.status_code == 401


def test_rejects_invalid_signature_and_legacy_tokens(tmp_path: Path) -> None:
    app = create_test_app(tmp_path)
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    invalid_signature = token(signing_key=other_key)
    unknown_key = token(key_id="unknown-key")
    legacy_value = base64.b64encode(
        f"student|STUDENT|{int(time.time()) + 3600}|WORKSHOP_SECRET_2026".encode()
    ).decode()
    with TestClient(app) as client:
        invalid = client.get("/api/tasks", headers={"Authorization": f"Bearer {invalid_signature}"})
        unknown = client.get("/api/tasks", headers={"Authorization": f"Bearer {unknown_key}"})
        legacy = client.get("/api/tasks", headers={"Authorization": f"Bearer {legacy_value}"})
    assert invalid.status_code == 401
    assert unknown.status_code == 401
    assert legacy.status_code == 401


def test_jwks_unavailable_returns_service_error(tmp_path: Path) -> None:
    app = create_test_app(tmp_path, jwks_client=StubJwksClient(connection_error=True))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 503
    assert response.json()["detail"] == "Token verification service unavailable"


def test_validates_a_token_using_the_configured_jwks_url(monkeypatch, tmp_path: Path) -> None:
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(PRIVATE_KEY.public_key(), as_dict=True)
    jwk.update({"kid": KEY_ID, "use": "sig", "alg": "RS256"})
    response_body = json.dumps({"keys": [jwk]}).encode()

    class JwksHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response_body)

        def log_message(self, format: str, *args) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), JwksHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("AUTH_JWKS_URL", f"http://127.0.0.1:{server.server_port}/jwks")
    try:
        app = create_app(
            str(tmp_path / "workshop.db"),
            str(tmp_path / "uploads"),
            token_issuer=ISSUER,
            token_audience=AUDIENCE,
        )
        with TestClient(app) as client:
            response = client.get("/api/tasks", headers=headers())
        assert response.status_code == 200
        assert len(response.json()) == 2
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_rejects_missing_bearer_header(tmp_path: Path) -> None:
    app = create_test_app(tmp_path)
    with TestClient(app) as client:
        response = client.get("/api/tasks")
    assert response.status_code == 401
