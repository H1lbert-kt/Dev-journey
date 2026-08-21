import pytest
from fastapi.testclient import TestClient


class TestAuthentication:
    def test_login_page_renders(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "login" in resp.text.lower() or "Login" in resp.text

    def test_login_with_valid_credentials(self, client, user_a):
        resp = client.post("/login", data={"username": "user_a", "password": "pass_a123"}, follow_redirects=False)
        assert resp.status_code in (303, 200)
        if resp.status_code == 303:
            assert "session_token" in resp.headers.get("set-cookie", "")

    def test_login_with_invalid_password(self, client, user_a):
        resp = client.post("/login", data={"username": "user_a", "password": "wrong"}, follow_redirects=False)
        assert resp.status_code == 200
        assert "invalido" in resp.text.lower() or "invalidos" in resp.text.lower()

    def test_login_with_nonexistent_user(self, client):
        resp = client.post("/login", data={"username": "nonexistent", "password": "pass123"}, follow_redirects=False)
        assert resp.status_code == 200
        assert "invalido" in resp.text.lower() or "invalidos" in resp.text.lower()

    def test_login_does_not_reveal_user_existence(self, client, user_a):
        resp1 = client.post("/login", data={"username": "user_a", "password": "wrong"}, follow_redirects=False)
        resp2 = client.post("/login", data={"username": "nonexistent", "password": "wrong"}, follow_redirects=False)
        assert resp1.text == resp2.text

    def test_register_new_user(self, client):
        resp = client.post("/register", data={
            "username": "newuser",
            "email": "new@test.com",
            "password": "pass123",
            "password_confirm": "pass123",
            "study_mode": "programacao",
        }, follow_redirects=False)
        assert resp.status_code in (303, 200)

    def test_register_short_password(self, client):
        resp = client.post("/register", data={
            "username": "shortpw",
            "email": "short@test.com",
            "password": "123",
            "password_confirm": "123",
        }, follow_redirects=False)
        assert resp.status_code == 200
        assert "minimo" in resp.text.lower() or "6 caracteres" in resp.text

    def test_register_invalid_username(self, client):
        resp = client.post("/register", data={
            "username": "a",
            "email": "test@test.com",
            "password": "pass123",
            "password_confirm": "pass123",
        }, follow_redirects=False)
        assert resp.status_code == 200
        assert "invalido" in resp.text.lower()

    def test_register_invalid_email(self, client):
        resp = client.post("/register", data={
            "username": "validuser",
            "email": "notanemail",
            "password": "pass123",
            "password_confirm": "pass123",
        }, follow_redirects=False)
        assert resp.status_code == 200
        assert "invalido" in resp.text.lower()

    def test_register_password_mismatch(self, client):
        resp = client.post("/register", data={
            "username": "mismatch",
            "email": "m@test.com",
            "password": "pass123",
            "password_confirm": "pass456",
        }, follow_redirects=False)
        assert resp.status_code == 200

    def test_logout_invalidates_session(self, auth_client_a):
        resp = auth_client_a.post("/logout", follow_redirects=False)
        assert resp.status_code == 303
        resp2 = auth_client_a.get("/timer/", follow_redirects=False)
        assert resp2.status_code == 303

    def test_protected_route_redirects_without_auth(self, client):
        resp = client.get("/timer/", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]


class TestAuthorization:
    def test_user_a_cannot_delete_user_b_simulado(self, auth_client_a, auth_client_b, db, user_a, user_b):
        from app.models.simulado import Simulado
        s = Simulado(name="B's Sim", total_questions=10, correct_answers=7,
                      wrong_answers=2, null_answers=1, correction_method="normal",
                      final_score=7, time_minutes=60, score=70.0, display_order=0,
                      user_id=user_b.id)
        db.add(s)
        db.commit()
        db.refresh(s)
        resp = auth_client_a.post(f"/simulados/{s.id}/delete", follow_redirects=False)
        from app.models.simulado import Simulado as S2
        remaining = db.query(S2).filter(S2.id == s.id).first()
        assert remaining is not None

    def test_unauthenticated_cannot_access_chart_data(self, client):
        resp = client.get("/simulados/chart-data")
        assert resp.status_code == 401

    def test_unauthenticated_cannot_access_reorder(self, client):
        resp = client.post("/simulados/reorder", json={"order": []})
        assert resp.status_code == 401


class TestIDOR:
    def test_cannot_access_other_users_exam(self, auth_client_a, auth_client_b, db, user_a, user_b):
        from app.models.exam import Exam
        exam = Exam(name="User B Exam", status="planejando", user_id=user_b.id)
        db.add(exam)
        db.commit()
        db.refresh(exam)
        resp = auth_client_a.get(f"/exams/{exam.id}", follow_redirects=False)
        assert resp.status_code in (303, 404)

    def test_cannot_delete_other_users_exam(self, auth_client_a, auth_client_b, db, user_a, user_b):
        from app.models.exam import Exam
        exam = Exam(name="User B Exam Delete", status="planejando", user_id=user_b.id)
        db.add(exam)
        db.commit()
        db.refresh(exam)
        resp = auth_client_a.post(f"/exams/{exam.id}/delete", follow_redirects=False)
        from app.models.exam import Exam as E2
        remaining = db.query(E2).filter(E2.id == exam.id).first()
        assert remaining is not None

    def test_cannot_update_other_users_flashcard(self, auth_client_a, auth_client_b, db, user_a, user_b):
        from app.models.subject import Subject
        from app.models.flashcard import Flashcard
        subj = Subject(name="B's Subj", user_id=user_b.id)
        db.add(subj)
        db.commit()
        db.refresh(subj)
        card = Flashcard(front="Q", back="A", subject_id=subj.id, user_id=user_b.id)
        db.add(card)
        db.commit()
        db.refresh(card)
        resp = auth_client_a.post(f"/flashcards/{card.id}/delete", follow_redirects=False)
        from app.models.flashcard import Flashcard as F2
        remaining = db.query(F2).filter(F2.id == card.id).first()
        assert remaining is not None


class TestSQLInjection:
    def test_login_sql_injection_username(self, client):
        resp = client.post("/login", data={
            "username": "' OR '1'='1",
            "password": "anything",
        }, follow_redirects=False)
        assert resp.status_code == 200
        assert "invalido" in resp.text.lower() or "invalidos" in resp.text.lower()

    def test_login_sql_injection_password(self, client, user_a):
        resp = client.post("/login", data={
            "username": "user_a",
            "password": "' OR '1'='1",
        }, follow_redirects=False)
        assert resp.status_code == 200

    def test_search_sql_injection(self, auth_client_a):
        resp = auth_client_a.get("/history/?period=all&subject='; DROP TABLE users; --")
        assert resp.status_code == 200


class TestSecurityHeaders:
    def test_x_content_type_options(self, client):
        resp = client.get("/login")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/login")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_x_xss_protection_removed(self, client):
        resp = client.get("/login")
        assert resp.headers.get("X-XSS-Protection") is None

    def test_referrer_policy(self, client):
        resp = client.get("/login")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client):
        resp = client.get("/login")
        assert "camera=()" in resp.headers.get("Permissions-Policy", "")

    def test_csp_header(self, client):
        resp = client.get("/login")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src" in csp
        assert "frame-ancestors" in csp

    def test_cross_origin_opener_policy(self, client):
        resp = client.get("/login")
        assert resp.headers.get("Cross-Origin-Opener-Policy") == "same-origin"

    def test_cross_origin_resource_policy(self, client):
        resp = client.get("/login")
        assert resp.headers.get("Cross-Origin-Resource-Policy") == "same-origin"


class TestCookieSecurity:
    def test_session_cookie_httponly(self, client, user_a):
        resp = client.post("/login", data={"username": "user_a", "password": "pass_a123"}, follow_redirects=False)
        cookies = resp.headers.get_list("set-cookie")
        session_cookie = [c for c in cookies if "session_token" in c][0]
        assert "httponly" in session_cookie.lower()

    def test_session_cookie_samesite(self, client, user_a):
        resp = client.post("/login", data={"username": "user_a", "password": "pass_a123"}, follow_redirects=False)
        cookies = resp.headers.get_list("set-cookie")
        session_cookie = [c for c in cookies if "session_token" in c][0]
        assert "samesite" in session_cookie.lower()

    def test_session_cookie_has_expiry(self, client, user_a):
        resp = client.post("/login", data={"username": "user_a", "password": "pass_a123"}, follow_redirects=False)
        cookies = resp.headers.get_list("set-cookie")
        session_cookie = [c for c in cookies if "session_token" in c][0]
        assert "max-age" in session_cookie.lower()


def _reset_rate_limits():
    """Reset the rate limit state on all middleware instances."""
    from main import _rate_limit_instances
    for inst in _rate_limit_instances:
        inst._requests.clear()
        inst._login_attempts.clear()
        inst._register_attempts.clear()


class TestRateLimiting:
    def test_login_rate_limit(self, client):
        _reset_rate_limits()
        for i in range(12):
            client.post("/login", data={"username": "user_a", "password": "wrong"}, follow_redirects=False)
        resp = client.post("/login", data={"username": "user_a", "password": "wrong"}, follow_redirects=False)
        assert resp.status_code == 429

    def test_register_rate_limit(self, client):
        _reset_rate_limits()
        for i in range(6):
            client.post("/register", data={
                "username": f"rate{i}",
                "email": f"rate{i}@test.com",
                "password": "pass123",
                "password_confirm": "pass123",
            }, follow_redirects=False)
        resp = client.post("/register", data={
            "username": "ratelast",
            "email": "last@test.com",
            "password": "pass123",
            "password_confirm": "pass123",
        }, follow_redirects=False)
        assert resp.status_code == 429


class TestInputValidation:
    def test_simulado_reorder_invalid_json(self, auth_client_a):
        resp = auth_client_a.post("/simulados/reorder",
                                   content=b"not json",
                                   headers={"Content-Type": "application/json"})
        assert resp.status_code == 400

    def test_simulado_reorder_huge_list(self, auth_client_a):
        resp = auth_client_a.post("/simulados/reorder",
                                   json={"order": list(range(300))})
        assert resp.status_code == 400

    def test_simulado_reorder_non_integer_elements(self, auth_client_a):
        resp = auth_client_a.post("/simulados/reorder",
                                   json={"order": ["a", "b", "c"]})
        assert resp.status_code == 200

    def test_flashcard_upload_too_large(self, auth_client_a):
        from io import BytesIO
        large_content = b"x" * (2 * 1024 * 1024)
        resp = auth_client_a.post("/flashcards/import",
                                   files={"file": ("test.txt", BytesIO(large_content), "text/plain")},
                                   data={"subject_id": "1"},
                                   follow_redirects=False)
        assert resp.status_code in (303, 400, 413, 422)


class TestOpenRedirect:
    def test_switch_mode_blocks_external_referer(self, auth_client_a):
        resp = auth_client_a.post("/switch-mode",
                                   data={"mode": "programacao"},
                                   headers={"Referer": "https://evil.com/steal"},
                                   follow_redirects=False)
        if resp.status_code == 303:
            location = resp.headers.get("location", "")
            assert "evil.com" not in location

    def test_switch_mode_blocks_double_slash_referer(self, auth_client_a):
        resp = auth_client_a.post("/switch-mode",
                                   data={"mode": "programacao"},
                                   headers={"Referer": "//evil.com"},
                                   follow_redirects=False)
        if resp.status_code == 303:
            location = resp.headers.get("location", "")
            assert "evil.com" not in location


class TestHealthEndpoint:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "db_connected" in data


class TestLogout:
    def test_logout_clears_cookies(self, client, user_a):
        client.post("/login", data={"username": "user_a", "password": "pass_a123"}, follow_redirects=False)
        resp = client.post("/logout", follow_redirects=False)
        cookies = resp.headers.get_list("set-cookie")
        for c in cookies:
            if "session_token" in c:
                assert "max-age=0" in c.lower() or "expires=" in c.lower()


class TestPasswordSecurity:
    def test_password_hash_is_argon2(self, user_a):
        assert user_a.password_hash.startswith("$argon2")

    def test_password_not_stored_plaintext(self, user_a):
        assert user_a.password_hash != "pass_a123"
