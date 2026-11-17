"""Alumni search."""

from db import connect

MAX_RESULTS = 50


def search_it(term, limit=MAX_RESULTS):
    """Find alumni whose name, city, industry, or company contains `term`.

    A full name like "michael smith" also matches first + last name together.
    Returns an empty list for a blank search.
    """
    term = (term or "").strip()
    if not term:
        return []
    pattern = f"%{term}%"
    with connect() as conn:
        return conn.execute(
            """
            SELECT id, first_name, last_name, email, linkedin, grad_year,
                   industry, company_name, city, state_name
            FROM alumni
            WHERE first_name ILIKE %(p)s
               OR last_name ILIKE %(p)s
               OR (first_name || ' ' || last_name) ILIKE %(p)s
               OR city ILIKE %(p)s
               OR state_name ILIKE %(p)s
               OR industry ILIKE %(p)s
               OR company_name ILIKE %(p)s
            ORDER BY grad_year DESC NULLS LAST, last_name, first_name
            LIMIT %(limit)s
            """,
            {"p": pattern, "limit": limit},
        ).fetchall()
