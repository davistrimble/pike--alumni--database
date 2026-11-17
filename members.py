"""Member accounts: lookups, passwords, admin management."""

from db import connect


def normalize_email(email):
    return (email or "").strip().lower()


def get_member(email):
    """Return the member with this email (any case/spacing), or None."""
    with connect() as conn:
        return conn.execute(
            "SELECT id, email, password_hash, is_admin FROM members WHERE email = %s",
            (normalize_email(email),),
        ).fetchone()


def get_member_by_id(member_id):
    with connect() as conn:
        return conn.execute(
            "SELECT id, email, password_hash, is_admin FROM members WHERE id = %s",
            (member_id,),
        ).fetchone()


def set_password(email, password_hash):
    """Store a password hash and mark the account activated (first time only)."""
    with connect() as conn:
        conn.execute(
            """
            UPDATE members
            SET password_hash = %s,
                activated_at = COALESCE(activated_at, now())
            WHERE email = %s
            """,
            (password_hash, normalize_email(email)),
        )


def record_login(member_id):
    with connect() as conn:
        conn.execute(
            "UPDATE members SET last_login_at = now() WHERE id = %s", (member_id,)
        )


def add_member(email):
    """Approve an email for sign-up. Returns False if it was already on the list."""
    with connect() as conn:
        row = conn.execute(
            """
            INSERT INTO members (email) VALUES (%s)
            ON CONFLICT (email) DO NOTHING
            RETURNING id
            """,
            (normalize_email(email),),
        ).fetchone()
        return row is not None


def remove_member(member_id):
    """Delete a member and (via ON DELETE CASCADE) their activity history."""
    with connect() as conn:
        conn.execute("DELETE FROM members WHERE id = %s", (member_id,))


def set_admin(member_id, is_admin):
    with connect() as conn:
        conn.execute(
            "UPDATE members SET is_admin = %s WHERE id = %s", (is_admin, member_id)
        )


def reset_password(member_id):
    """Clear a member's password so they can sign up again with the chapter code.

    Activity history is kept; activated_at is cleared so the admin page shows
    they still need to finish signing up.
    """
    with connect() as conn:
        conn.execute(
            """
            UPDATE members
            SET password_hash = NULL, activated_at = NULL
            WHERE id = %s
            """,
            (member_id,),
        )
