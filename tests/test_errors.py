import pytest
from fastapi.testclient import TestClient


class TestNotFound:
    def test_nonexistent_page_returns_404(self, client):
        resp = client.get("/pagina-inexistente", follow_redirects=False)
        assert resp.status_code == 404

    def test_nonexistent_api_returns_404(self, client):
        resp = client.get("/api/nonexistent", follow_redirects=False)
        assert resp.status_code == 404

    def test_404_has_no_traceback(self, client):
        resp = client.get("/pagina-inexistente")
        assert "Traceback" not in resp.text

    def test_404_has_request_id_header(self, client):
        resp = client.get("/pagina-inexistente", follow_redirects=False)
        assert "X-Request-ID" in resp.headers


class TestUnauthorized:
    def test_protected_route_without_auth(self, client):
        resp = client.get("/timer/", follow_redirects=False)
        assert resp.status_code == 303

    def test_api_without_auth_returns_401(self, client):
        resp = client.get("/simulados/chart-data")
        assert resp.status_code == 401

    def test_flashcards_review_without_auth(self, client):
        resp = client.post("/flashcards/api/review", json={"card_id": 1, "quality": 4})
        assert resp.status_code == 401


class TestSecurityHeaders:
    def test_request_id_in_response(self, client):
        resp = client.get("/login")
        assert "X-Request-ID" in resp.headers
        assert len(resp.headers["X-Request-ID"]) == 32

    def test_response_time_header(self, client):
        resp = client.get("/login")
        assert "X-Response-Time" in resp.headers
        assert "ms" in resp.headers["X-Response-Time"]

    def test_x_content_type_options(self, client):
        resp = client.get("/login")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/login")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_no_x_xss_protection(self, client):
        resp = client.get("/login")
        assert resp.headers.get("X-XSS-Protection") is None

    def test_csp_header(self, client):
        resp = client.get("/login")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src" in csp
        assert "frame-ancestors" in csp

    def test_referrer_policy(self, client):
        resp = client.get("/login")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_cross_origin_opener_policy(self, client):
        resp = client.get("/login")
        assert resp.headers.get("Cross-Origin-Opener-Policy") == "same-origin"

    def test_cross_origin_resource_policy(self, client):
        resp = client.get("/login")
        assert resp.headers.get("Cross-Origin-Resource-Policy") == "same-origin"


class TestHealthCheck:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_json(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "database" in data
        assert data["db_connected"] is True

    def test_health_no_internal_details(self, client):
        resp = client.get("/health")
        text = resp.text
        assert "SECRET_KEY" not in text


class TestErrorResponses:
    def test_rate_limit_returns_json(self, rate_limit_client):
        for i in range(12):
            rate_limit_client.post("/login", data={"username": "user_a", "password": "wrong"}, follow_redirects=False)
        resp = rate_limit_client.post("/login", data={"username": "user_a", "password": "wrong"}, follow_redirects=False)
        assert resp.status_code == 429
        data = resp.json()
        assert "error" in data
        assert "Retry-After" in resp.headers

    def test_rate_limit_register_returns_json(self, rate_limit_client):
        for i in range(6):
            rate_limit_client.post("/register", data={
                "username": f"rate{i}",
                "email": f"rate{i}@test.com",
                "password": "pass123",
                "password_confirm": "pass123",
            }, follow_redirects=False)
        resp = rate_limit_client.post("/register", data={
            "username": "ratelast",
            "email": "last@test.com",
            "password": "pass123",
            "password_confirm": "pass123",
        }, follow_redirects=False)
        assert resp.status_code == 429
        data = resp.json()
        assert "error" in data

    def test_login_invalid_returns_200_with_error(self, client, user_a):
        resp = client.post("/login", data={"username": "user_a", "password": "wrong"})
        assert resp.status_code == 200
        assert "invalido" in resp.text.lower() or "invalidos" in resp.text.lower()

    def test_register_short_password_returns_200(self, client):
        resp = client.post("/register", data={
            "username": "validuser",
            "email": "valid@test.com",
            "password": "123",
            "password_confirm": "123",
        })
        assert resp.status_code == 200


class TestNoSensitiveDataInResponses:
    def test_no_traceback_in_response_body(self, client, user_a):
        resp = client.get("/timer/", follow_redirects=False)
        assert "Traceback" not in resp.text

    def test_no_file_paths_in_response(self, client, user_a):
        resp = client.get("/timer/", follow_redirects=False)
        assert "/home/" not in resp.text

    def test_404_no_traceback(self, client):
        resp = client.get("/definitely-not-a-real-page-xyz123")
        assert "Traceback" not in resp.text


class TestStatsEmptyData:
    def test_stats_with_no_data(self, auth_client_a):
        resp = auth_client_a.get("/stats/")
        assert resp.status_code == 200
        assert "Estat" in resp.text

    def test_stats_has_all_sections(self, auth_client_a):
        resp = auth_client_a.get("/stats/")
        assert resp.status_code == 200
        assert "Dias Estudados" in resp.text
        assert "Sequencia Atual" in resp.text or "Sequência Atual" in resp.text
        assert "Tempo Total" in resp.text

    def test_stats_no_traceback(self, auth_client_a):
        resp = auth_client_a.get("/stats/")
        assert "Traceback" not in resp.text


class TestStatsWithData:
    def test_stats_with_sessions(self, auth_client_a, db, user_a):
        from app.models.subject import Subject
        from app.models.study_session import StudySession
        from datetime import datetime

        subj = Subject(name="Matematica", user_id=user_a.id, study_mode="programacao")
        db.add(subj)
        db.commit()
        db.refresh(subj)

        session = StudySession(
            subject="Matematica",
            duration_minutes=60.0,
            user_id=user_a.id,
            study_mode="programacao",
            date=datetime.now(),
            session_type="estudo",
        )
        db.add(session)
        db.commit()

        resp = auth_client_a.get("/stats/")
        assert resp.status_code == 200
        assert "Matematica" in resp.text

    def test_stats_with_phases(self, auth_client_a, db, user_a):
        from app.models.phase import Phase
        from app.models.goal import Goal

        phase = Phase(name="Fase 1", user_id=user_a.id, study_mode="programacao", progress=50.0)
        db.add(phase)
        db.commit()
        db.refresh(phase)

        goal = Goal(title="Meta 1", phase_id=phase.id, completed=True)
        db.add(goal)
        db.commit()

        resp = auth_client_a.get("/stats/")
        assert resp.status_code == 200
