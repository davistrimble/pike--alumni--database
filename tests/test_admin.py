from conftest import login, make_member, post, query

import tracking


def as_admin(client):
    admin_id = make_member("admin@example.com", is_admin=True)
    login(client, "admin@example.com")
    return admin_id


def member(email):
    rows = query("SELECT * FROM members WHERE email = %s", (email,))
    return rows[0] if rows else None


def test_non_admin_gets_403(client):
    make_member("a@example.com")
    login(client, "a@example.com")
    assert client.get("/admin").status_code == 403
    assert post(client, "/admin/code", {"code": "hijack"}).status_code == 403
    assert tracking.get_setting(tracking.SIGNUP_CODE_KEY) is None


def test_admin_page_shows_stats(client):
    as_admin(client)
    other = make_member("b@example.com")
    query("INSERT INTO search_events (member_id) VALUES (%s), (%s) RETURNING id", (other, other))
    query(
        "INSERT INTO contact_events (member_id, alumni_id, channel, action) "
        "VALUES (%s, 1, 'email', 'copy') RETURNING id",
        (other,),
    )
    stats = {row["email"]: row for row in tracking.member_stats()}
    assert stats["b@example.com"]["searches"] == 2
    assert stats["b@example.com"]["email_copies"] == 1
    assert stats["admin@example.com"]["searches"] == 0
    page = client.get("/admin")
    assert page.status_code == 200
    assert b"b@example.com" in page.data


def test_bulk_approve_emails(client):
    as_admin(client)
    make_member("old@example.com", password=None)
    response = post(
        client,
        "/admin/members",
        {"emails": "One@Example.com, two@example.com\nnot-an-email\nold@example.com"},
        follow_redirects=True,
    )
    assert b"Approved 2 email(s)" in response.data
    assert b"not-an-email, old@example.com" in response.data
    assert member("one@example.com") and member("two@example.com")
    assert member("not-an-email") is None


def test_toggle_admin(client):
    as_admin(client)
    other = make_member("b@example.com")
    post(client, f"/admin/members/{other}/admin")
    assert member("b@example.com")["is_admin"] is True
    post(client, f"/admin/members/{other}/admin")
    assert member("b@example.com")["is_admin"] is False


def test_admin_cannot_change_own_account(client):
    admin_id = as_admin(client)
    for action in ["admin", "reset", "remove"]:
        post(client, f"/admin/members/{admin_id}/{action}")
    me = member("admin@example.com")
    assert me["is_admin"] is True and me["password_hash"] is not None


def test_reset_password_logs_member_out_and_lets_them_sign_up_again(client):
    as_admin(client)
    other = make_member("b@example.com")
    tracking.set_setting(tracking.SIGNUP_CODE_KEY, "garnet-gold")
    query("INSERT INTO search_events (member_id) VALUES (%s) RETURNING id", (other,))

    post(client, f"/admin/members/{other}/reset")
    row = member("b@example.com")
    assert row["password_hash"] is None and row["activated_at"] is None
    assert query("SELECT count(*) AS n FROM search_events")[0]["n"] == 1  # history kept

    post(client, "/logout")
    assert login(client, "b@example.com").status_code == 401
    post(
        client,
        "/signup",
        {"email": "b@example.com", "code": "garnet-gold", "password": "brand-new-pw", "confirm": "brand-new-pw"},
    )
    assert login(client, "b@example.com", "brand-new-pw").status_code == 302


def test_reset_password_ends_existing_session(client):
    other = make_member("b@example.com")
    login(client, "b@example.com")
    query("UPDATE members SET password_hash = NULL WHERE id = %s RETURNING id", (other,))
    assert client.get("/search").status_code == 302


def test_remove_member_deletes_history(client):
    as_admin(client)
    other = make_member("b@example.com")
    query("INSERT INTO search_events (member_id) VALUES (%s) RETURNING id", (other,))
    post(client, f"/admin/members/{other}/remove")
    assert member("b@example.com") is None
    assert query("SELECT count(*) AS n FROM search_events")[0]["n"] == 0


def test_missing_member_is_404(client):
    as_admin(client)
    assert post(client, "/admin/members/9999/remove").status_code == 404


def test_set_signup_code(client):
    as_admin(client)
    post(client, "/admin/code", {"code": "abc"})
    assert tracking.get_setting(tracking.SIGNUP_CODE_KEY) is None
    post(client, "/admin/code", {"code": "  new-code  "})
    assert tracking.get_setting(tracking.SIGNUP_CODE_KEY) == "new-code"

