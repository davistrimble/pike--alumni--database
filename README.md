# Pike Alumni Network

A members-only directory for the Vanderbilt chapter of Pi Kappa Alpha. Active
members log in, search alumni by name, city, state, industry, or company, and
get each alum's email and LinkedIn. Chapter admins approve who can join and see
how the tool is being used.

**Stack:** Python 3 · Flask · PostgreSQL (raw SQL through psycopg 3) · Jinja
templates · vanilla JS · pytest

## Features

- **Invite-only sign-up.** An email must be on the admin-approved list *and* the
  member must enter the chapter code. Passwords are hashed with Werkzeug.
- **Search.** Case-insensitive matching on first, last, or full name, city,
  state, industry, and company. Parameterized queries throughout (no SQL
  injection).
- **One-click contact.** Email and LinkedIn links plus copy buttons.
- **Admin dashboard.** Shows how many members have activated, plus
  per-member last login, search count, and email/LinkedIn click and copy
  counts. Admins can bulk-approve emails, make or remove admins, reset
  passwords, remove members, and rotate the chapter code.
- **Privacy by design.** Tracking stores counts only. Search text is never saved.
- **Security basics.** CSRF tokens on every POST, HttpOnly + SameSite session
  cookies, no open redirects after login, and sessions end immediately when a
  member is removed or their password is reset.
- **Data import.** `scripts/import_alumni.py` cleans messy CSVs: it normalizes
  LinkedIn URLs, states, and grad years, merges duplicates, and upserts safely
  (dry run by default).

## Run it locally

Requires PostgreSQL (tested on 17) and Python 3.12+.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # then set SECRET_KEY

createdb pike_alumni
psql pike_alumni -f sql/schema.sql     # alumni table + fake sample rows (drops alumni!)
psql pike_alumni -f sql/members.sql    # members table
psql pike_alumni -f sql/tracking.sql   # activity tracking + settings (safe to re-run)
```

Create the first admin by hand, then sign up through the site:

```bash
psql pike_alumni -c "INSERT INTO members (email, is_admin) VALUES ('you@example.com', true)"
psql pike_alumni -c "INSERT INTO settings VALUES ('signup_code', 'pick-a-code')"
flask --app app run --debug --port 5001
```

Open http://localhost:5001/signup. After that, manage everything from **/admin**.

> On macOS, AirPlay Receiver holds port 5000, which is why these commands use 5001.

## Tests

```bash
createdb pike_alumni_test   # once
pytest
```

The suite rebuilds `pike_alumni_test` from `sql/*.sql` before every test, and
refuses to run against a database whose name doesn't end in `_test`.

## Importing alumni

```bash
python scripts/import_alumni.py data/alumni.csv            # dry run: report only
python scripts/import_alumni.py data/alumni.csv --commit   # write
```

Keep real CSVs in `data/`, which is git-ignored. See the script's docstring for
the accepted columns.

## Project layout

```
app.py           routes, sessions, CSRF, access control
db.py            connect() helper (rows come back as dicts)
members.py       member accounts and admin actions
search.py        alumni search query
tracking.py      activity counts, admin stats, settings
scripts/         CSV import
sql/             schema files
templates/       Jinja pages (base, login, signup, search, admin, error)
static/          garnet & gold CSS, click/copy tracking JS
tests/           pytest suite
```

## Before deploying

- Add real email verification (or a magic-link login) on top of the chapter code.
- Set `SESSION_COOKIE_SECURE=1` and a strong `SECRET_KEY`, and run with gunicorn.
- Get alumni consent to be listed, and give them a way to opt out.
