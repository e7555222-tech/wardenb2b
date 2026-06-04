"""Pytest yapılandırması.

Uygulama import edilmeden ÖNCE ortam değişkenlerini ayarlar (database.py ve auth.py
modül seviyesinde okuduğu için sıra önemlidir) ve izole bir SQLite test veritabanı
ile bir TestClient sağlar.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

# ── Uygulama importundan ÖNCE ortam değişkenleri ────────────────────────────────
_TMP_DB = Path(tempfile.gettempdir()) / "warden_test.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["ADMIN_EMAIL"] = "admin@warden.app"
os.environ["ADMIN_PASSWORD"] = "AdminPass123"
os.environ["ADMIN_NAME"] = "Test Admin"
os.environ["DEMO_SEED"] = "false"
os.environ["CORS_ORIGINS"] = "*"

# backend/ paketini import yoluna ekle (modüller düz import ediliyor: `from auth import ...`)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402

# Testlerde rate limiting'i kapat (aksi halde 5/dk register limiti testleri 429 ile düşürür)
main.limiter.enabled = False


@pytest.fixture(scope="session")
def client():
    # Context manager lifespan'i tetikler → init_db + admin seed çalışır
    with TestClient(main.app) as c:
        yield c


# ── Yardımcılar ─────────────────────────────────────────────────────────────────

def register(client, email, password="StrongPass123", name="Test User"):
    return client.post("/register", json={"email": email, "password": password, "name": name})


def auth_headers(client, email, password="StrongPass123"):
    register(client, email, password=password)
    token = client.post("/token", data={"username": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def admin_headers(client):
    token = client.post(
        "/token", data={"username": "admin@warden.app", "password": "AdminPass123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
