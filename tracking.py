"""Activity tracking (counts only) and site settings."""

from db import connect

CHANNELS = ("email", "linkedin")
ACTIONS = ("click", "copy")
SIGNUP_CODE_KEY = "signup_code"


def log_search(member_id):
    """Record that a member searched. The search text is deliberately not stored."""
    with connect() as conn:
        conn.execute("INSERT INTO search_events (member_id) VALUES (%s)", (member_id,))


def log_contact(member_id, alumni_id, channel, action):
    """Record a click or copy of an alum's email/LinkedIn. Returns False if invalid."""
    if channel not in CHANNELS or action not in ACTIONS:
        return False
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO contact_events (member_id, alumni_id, channel, action)
            VALUES (%s, %s, %s, %s)
            """,
            (member_id, alumni_id, channel, action),
        )
    return True


def member_stats():
    """One row per member with activation info and activity counts, for /admin."""
    with connect() as conn:
        return conn.execute(
            """
            SELECT m.id, m.email, m.is_admin, m.create_time,
                   m.activated_at, m.last_login_at,
                   (SELECT count(*) FROM search_events s WHERE s.member_id = m.id) AS searches,
                   count(c.id) FILTER (WHERE c.channel = 'email' AND c.action = 'click') AS email_clicks,
                   count(c.id) FILTER (WHERE c.channel = 'email' AND c.action = 'copy') AS email_copies,
                   count(c.id) FILTER (WHERE c.channel = 'linkedin' AND c.action = 'click') AS linkedin_clicks,
                   count(c.id) FILTER (WHERE c.channel = 'linkedin' AND c.action = 'copy') AS linkedin_copies
            FROM members m
            LEFT JOIN contact_events c ON c.member_id = m.id
            GROUP BY m.id
            ORDER BY m.activated_at IS NULL, m.email
            """
        ).fetchall()


def get_setting(key):
    with connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = %s", (key,)).fetchone()
        return row["value"] if row else None


def set_setting(key, value):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """,
            (key, value),
        )
