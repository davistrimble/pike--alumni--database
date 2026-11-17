from conftest import CSRF, login, make_member, query


def logged_in(client):
    member_id = make_member("a@example.com")
    login(client, "a@example.com")
    return member_id


def track(client, payload, csrf=CSRF):
    with client.session_transaction() as sess:
        sess["csrf"] = CSRF
    return client.post("/track", json=payload, headers={"X-CSRF-Token": csrf})


def test_search_finds_by_city_industry_company_and_full_name(client):
    logged_in(client)
    assert b"Michael" in client.get("/search?q=nashville").data
    assert b"Deloitte" in client.get("/search?q=consulting").data
    assert b"Smith" in client.get("/search?q=goldman").data
    assert b"Smith" in client.get("/search?q=michael smith").data
    assert b"No alumni match" in client.get("/search?q=zzzz").data


def test_search_counts_only_nonblank_searches_and_stores_no_text(client):
    member_id = logged_in(client)
    client.get("/search")
    client.get("/search?q=++")
    client.get("/search?q=nashville")
    client.get("/search?q=finance")
    rows = query("SELECT * FROM search_events")
    assert len(rows) == 2
    assert all(row["member_id"] == member_id for row in rows)
    assert set(rows[0].keys()) == {"id", "member_id", "created_at"}


def test_track_records_click_and_copy(client):
    member_id = logged_in(client)
    assert track(client, {"alumni_id": 2, "channel": "email", "action": "click"}).status_code == 204
    assert track(client, {"alumni_id": 2, "channel": "linkedin", "action": "copy"}).status_code == 204
    rows = query("SELECT member_id, alumni_id, channel, action FROM contact_events ORDER BY id")
    assert rows == [
        {"member_id": member_id, "alumni_id": 2, "channel": "email", "action": "click"},
        {"member_id": member_id, "alumni_id": 2, "channel": "linkedin", "action": "copy"},
    ]


def test_track_rejects_bad_input(client):
    logged_in(client)
    assert track(client, {"alumni_id": 2, "channel": "phone", "action": "click"}).status_code == 400
    assert track(client, {"alumni_id": 2, "channel": "email", "action": "delete"}).status_code == 400
    assert track(client, {"channel": "email", "action": "click"}, csrf="wrong").status_code == 400
    assert query("SELECT count(*) AS n FROM contact_events")[0]["n"] == 0


def test_track_requires_login(client):
    response = track(client, {"alumni_id": 2, "channel": "email", "action": "click"})
    assert response.status_code == 302
    assert query("SELECT count(*) AS n FROM contact_events")[0]["n"] == 0
