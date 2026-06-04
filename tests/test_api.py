"""Warden B2B API entegrasyon testleri."""
from conftest import admin_headers, auth_headers, register


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Kayıt & parola politikası ───────────────────────────────────────────────────

def test_register_rejects_short_password(client):
    r = register(client, "short@warden.app", password="ab1")
    assert r.status_code == 400


def test_register_rejects_password_without_digit(client):
    r = register(client, "nodigit@warden.app", password="onlyletters")
    assert r.status_code == 400


def test_register_accepts_strong_password(client):
    r = register(client, "strong@warden.app", password="StrongPass123")
    assert r.status_code == 200
    assert r.json()["email"] == "strong@warden.app"


def test_register_duplicate_rejected(client):
    register(client, "dup@warden.app")
    r = register(client, "dup@warden.app")
    assert r.status_code == 400


# ── Giriş ────────────────────────────────────────────────────────────────────────

def test_login_wrong_password(client):
    register(client, "login@warden.app")
    r = client.post("/token", data={"username": "login@warden.app", "password": "WrongPass123"})
    assert r.status_code == 401


def test_login_success(client):
    register(client, "login2@warden.app")
    r = client.post("/token", data={"username": "login2@warden.app", "password": "StrongPass123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


# ── Yetkilendirme & lead izolasyonu ──────────────────────────────────────────────

def test_lead_creation_requires_auth(client):
    r = client.post("/leads", json={"name": "x", "email": "x@warden.app", "budget": 1000})
    assert r.status_code == 401


def test_leads_are_isolated_between_users(client):
    ha = auth_headers(client, "iso_a@warden.app")
    hb = auth_headers(client, "iso_b@warden.app")

    lead = client.post(
        "/leads", json={"name": "Lead A", "email": "la@warden.app", "budget": 20000}, headers=ha
    ).json()

    # B kullanıcısı A'nın lead'ini göremez
    assert client.get(f"/leads/{lead['id']}", headers=hb).status_code == 404
    # A kendi lead'ini görür
    assert any(x["id"] == lead["id"] for x in client.get("/leads", headers=ha).json())


# ── Tier limiti ──────────────────────────────────────────────────────────────────

def test_free_tier_lead_limit_enforced(client):
    h = auth_headers(client, "limit@warden.app")
    for i in range(10):  # Free tier limiti = 10
        r = client.post(
            "/leads", json={"name": f"L{i}", "email": f"l{i}@warden.app", "budget": 1000}, headers=h
        )
        assert r.status_code == 200, f"{i}. lead başarısız oldu"
    over = client.post(
        "/leads", json={"name": "L11", "email": "l11@warden.app", "budget": 1000}, headers=h
    )
    assert over.status_code == 403


# ── Parola sıfırlama: token sızdırmamalı ─────────────────────────────────────────

def test_password_reset_does_not_leak_token(client):
    register(client, "reset@warden.app")
    r = client.post("/password-reset/request", json={"email": "reset@warden.app"})
    assert r.status_code == 200
    assert "reset_token" not in r.json()


def test_password_reset_is_generic_for_unknown_email(client):
    known = client.post("/password-reset/request", json={"email": "reset@warden.app"}).json()
    unknown = client.post("/password-reset/request", json={"email": "ghost@warden.app"}).json()
    # Hesap numaralandırması engellenir: yanıt aynı olmalı
    assert known == unknown


# ── Webhook secret doğrulaması ───────────────────────────────────────────────────

def test_webhook_rejects_wrong_secret(client):
    h = auth_headers(client, "wh@warden.app")
    lead = client.post(
        "/leads", json={"name": "W", "email": "w@warden.app", "budget": 20000}, headers=h
    ).json()
    payload = {"lead_id": lead["id"], "score": 80, "sentiment": "Yüksek", "action": "Ara"}

    bad = client.post("/webhook/lead-score", json=payload, headers={"X-Webhook-Secret": "wrong"})
    assert bad.status_code == 401

    ok = client.post(
        "/webhook/lead-score", json=payload, headers={"X-Webhook-Secret": "test-webhook-secret"}
    )
    assert ok.status_code == 200


# ── Simülasyon ───────────────────────────────────────────────────────────────────

def test_simulate_score_assigns_values(client):
    h = auth_headers(client, "sim@warden.app")
    lead = client.post(
        "/leads", json={"name": "S", "email": "s@warden.app", "budget": 40000}, headers=h
    ).json()
    r = client.post(f"/leads/{lead['id']}/simulate-score", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["score"] is not None
    assert body["sentiment"] in ("Yüksek", "Orta", "Düşük")
    assert body["action"]


# ── Admin yetkisi ────────────────────────────────────────────────────────────────

def test_admin_endpoints_forbidden_for_normal_user(client):
    h = auth_headers(client, "normal@warden.app")
    assert client.get("/admin/users", headers=h).status_code == 403


def test_admin_can_list_users(client):
    h = admin_headers(client)
    r = client.get("/admin/users", headers=h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_admin_cannot_delete_self(client):
    h = admin_headers(client)
    me = client.get("/users/me", headers=h).json()
    r = client.delete(f"/admin/users/{me['id']}", headers=h)
    assert r.status_code == 400


def test_admin_delete_user_cascades(client):
    # Silinecek kullanıcı + lead'i oluştur
    victim = auth_headers(client, "victim@warden.app")
    client.post("/leads", json={"name": "V", "email": "v@warden.app", "budget": 5000}, headers=victim)
    victim_id = client.get("/users/me", headers=victim).json()["id"]

    h = admin_headers(client)
    r = client.delete(f"/admin/users/{victim_id}", headers=h)
    assert r.status_code == 200  # cascade sayesinde FK hatası olmadan silinir
