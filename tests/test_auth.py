from conftest import CSRF, PASSWORD, login, make_member, post, query

import tracking


def set_code(code="garnet-gold"):
    tracking.set_setting(tracking.SIGNUP_CODE_KEY, code)


def signup(client, email="new@example.com", code="garnet-gold", password="longenough", confirm=None):
    return post(
        client,
        "/signup",
        {
            "email": email,
            "code": code,
            "password": password,
            "confirm": password if confirm is None else confirm,
        },
    )


# --- access control -------------------------------------------------------


def test_logged_out_pages_redirect_to_login(client):
    for url in ["/", "/search", "/search?q=smith", "/admin"]:
        response = client.get(url)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


def test_post_without_csrf_token_is_rejected(client):
    make_member("a@example.com")
    response = client.post("/login", data={"email": "a@example.com", "password": PASSWORD})
    assert response.status_code == 400
    response = client.post(
        "/login", data={"email": "a@example.com", "password": PASSWORD, "csrf": "wrong"}
    )
    assert response.status_code == 400


# --- sign-up --------------------------------------------------------------


def test_signup_closed_when_no_code_set(client):
    make_member("new@example.com", password=None)
    response = signup(client)
    assert response.status_code == 400
    assert b"Sign-up is closed" in response.data


def test_signup_rejects_wrong_code(client):
    set_code()
    make_member("new@example.com", password=None)
    response = signup(client, code="nope")
    assert b"chapter code is wrong" in response.data
    assert query("SELECT password_hash FROM members")[0]["password_hash"] is None


def test_signup_rejects_unapproved_email(client):
    set_code()
    response = signup(client, email="stranger@example.com")
    assert b"approved list" in response.data


def test_signup_rejects_short_or_mismatched_password(client):
    set_code()
    make_member("new@example.com", password=None)
    assert b"at least 8" in signup(client, password="short").data
    assert b"don&#39;t match" in signup(client, confirm="different1").data


def test_signup_success_is_case_insensitive_and_activates(client):
    set_code("Garnet-Gold")
    make_member("new@example.com", password=None)
    response = signup(client, email="  NEW@Example.com ", code="garnet-gold ")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    row = query("SELECT password_hash, activated_at FROM members")[0]
    assert row["password_hash"] and row["activated_at"]
    assert login(client, "new@example.com", "longenough").status_code == 302


def test_signup_twice_points_to_login(client):
    set_code()
    make_member("new@example.com")
    response = signup(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


# --- login / logout -------------------------------------------------------


def test_login_wrong_password(client):
    make_member("a@example.com")
    response = login(client, "a@example.com", "wrong-password")
    assert response.status_code == 401
    assert b"Wrong email or password" in response.data


def test_invited_member_logging_in_is_sent_to_signup_with_email_filled(client):
    make_member("a@example.com", password=None)
    response = login(client, " A@Example.com", "anything")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/signup")
    page = client.get("/signup").data
    assert b"haven&#39;t created your account yet" in page
    assert b'value="a@example.com"' in page
    # The prefill is used once, not on every later visit.
    assert b'value="a@example.com"' not in client.get("/signup").data
    # And no session was started.
    assert client.get("/search").status_code == 302


def test_unknown_email_still_gets_generic_login_error(client):
    response = login(client, "stranger@example.com", "anything")
    assert response.status_code == 401
    assert b"Wrong email or password" in response.data


def test_successful_signup_prefills_login_email(client):
    set_code()
    make_member("new@example.com", password=None)
    signup(client)
    assert b'value="new@example.com"' in client.get("/login").data


def test_login_records_last_login_and_redirects(client):
    make_member("a@example.com")
    response = login(client, "A@example.com")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/search")
    assert query("SELECT last_login_at FROM members")[0]["last_login_at"] is not None


def test_login_follows_safe_next_only(client):
    make_member("a@example.com")
    response = post(
        client, "/login?next=/search?q=nash", {"email": "a@example.com", "password": PASSWORD}
    )
    assert response.headers["Location"] == "/search?q=nash"

    post(client, "/logout")
    response = post(
        client, "/login?next=//evil.example", {"email": "a@example.com", "password": PASSWORD}
    )
    assert response.headers["Location"] == "/search"


def test_logout_ends_session(client):
    make_member("a@example.com")
    login(client, "a@example.com")
    assert client.get("/search").status_code == 200
    post(client, "/logout")
    assert client.get("/search").status_code == 302


def test_removed_member_is_logged_out(client):
    member_id = make_member("a@example.com")
    login(client, "a@example.com")
    query("DELETE FROM members WHERE id = %s RETURNING id", (member_id,))
    assert client.get("/search").status_code == 302


def test_signup_error_keeps_email_and_code_but_not_passwords(client):
    set_code()
    make_member("new@example.com", password=None)
    page = signup(client, password="longenough", confirm="different1").data
    assert b'value="new@example.com"' in page
    assert b'value="garnet-gold"' in page
    assert b"longenough" not in page
