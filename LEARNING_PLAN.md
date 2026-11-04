# Pike Alumni Database: Learning Plan

Goal: active members log in, search alumni by **name, city, or industry**, and see their **email and LinkedIn**.

Stack: **PostgreSQL**, **Python 3**, **psycopg 3** (Python ↔ Postgres driver), **Flask** (web framework), **Jinja2** (HTML templates, which come with Flask).

Rule for this project: you write the code. Claude explains, gives hints, and reviews.

---

## Phase 0: Set up your tools (about 1 hour)

1. Install Postgres: `brew install postgresql@17`, then `brew services start postgresql@17`.
   - Homebrew prints a line about adding it to your PATH. Read it and do it.
   - Check it works: `psql postgres` should open a prompt. Type `\q` to quit.
2. Start git in this folder: `git init`. Commit early and often.
3. Make a virtual environment: `python3 -m venv .venv`, then `source .venv/bin/activate`.
   - **Learn:** what a venv is and why each project gets its own.
4. Make a `.gitignore` that ignores `.venv/` and `.env`.

✅ Checkpoint: `psql postgres` opens, and `which python` points inside `.venv`.

## Phase 1: Learn SQL by hand, no Python yet

Work only in `psql`. Save every command you run in `sql/schema.sql` so you can rebuild the database later.

1. `CREATE DATABASE pike_alumni;`, then connect with `\c pike_alumni`.
2. Design an `alumni` table. Choose the columns and types yourself. Some questions to answer first:
   - Which columns are required (`NOT NULL`)? Which can be blank?
   - Is one `name` column enough, or do you want `first_name` and `last_name`? Think about how people will search.
   - Should `email` be `UNIQUE`?
   - Should industry be a plain text column or its own table? (Think: "Finance" vs "finance" vs "Banking".)
3. `INSERT` 5 to 10 made-up alumni.
4. Write queries:
   - all alumni in Nashville
   - names containing "smi" (look up `ILIKE` and `%`)
   - alumni in finance, sorted by graduation year

✅ Checkpoint: you can rebuild the whole database from `schema.sql` with `psql -d pike_alumni -f sql/schema.sql`.

**Concepts:** tables, data types, primary keys, constraints, `SELECT/WHERE/ORDER BY`, `ILIKE`.

## Phase 2: Python talks to Postgres

1. `pip install "psycopg[binary]" python-dotenv`, then `pip freeze > requirements.txt`.
2. Put your connection string in `.env` (never commit it), for example `DATABASE_URL=postgresql://localhost/pike_alumni`.
3. Write `search.py`: a command-line program that asks for a search term and prints matching alumni.
4. **Important lesson:** learn why you must **never** build SQL with f-strings (`f"... WHERE city = '{city}'"`). Look up *SQL injection* and *parameterized queries* (`%s` placeholders in psycopg).

✅ Checkpoint: `python search.py`, then typing "nash", prints the Nashville alumni.

**Concepts:** connections, cursors, parameters, environment variables, functions and modules.

## Phase 3: Load real data

Your chapter probably has alumni in a spreadsheet already. Export it as CSV.

1. Write `import_csv.py` with Python's built-in `csv` module to insert rows.
2. Handle messy data: blank cells, extra spaces, inconsistent city names, duplicate emails.
3. Make it safe to run twice. Look up `ON CONFLICT ... DO UPDATE` (an "upsert").

**Concepts:** file I/O, data cleaning, transactions, idempotent scripts.

## Phase 4: The web app

1. `pip install flask`. Build `app.py` with one route that returns "Hello Pike".
2. Add a search page: an HTML form (a template) that submits to a route, which runs your Phase 2 query and renders the results in a table.
3. Make emails `mailto:` links and LinkedIn URLs clickable links.
4. Move the database code into its own module (`db.py`) so `app.py` only handles web logic.

**Concepts:** HTTP GET/POST, routes, templates, query strings, separating concerns.

## Phase 5: Members-only access (do this before going online)

This is real personal contact info, so the site must not be public.

1. Add a `users` table, plus login and logout. Store **hashed** passwords (`werkzeug.security`, which comes with Flask). Never store plain text.
2. Use Flask sessions to remember who is logged in. Protect the search route.
3. Decide how members get accounts: an admin invites them, or sign-up only works for emails on an approved list.
4. Get alumni's OK to be listed. Even a checkbox on a Google Form is enough.

**Concepts:** authentication, hashing, sessions, cookies, the secret key.

## Phase 6: Put it online

- Database: a free hosted Postgres (Neon or Supabase).
- App: Render or Railway, run with `gunicorn`.
- Learn: production vs. development settings, environment variables on a host, HTTPS.

## Later ideas (pick what interests you)

- A form where alumni can update their own info
- Better search: `pg_trgm` for typo-tolerant matching, plus indexes (learn `EXPLAIN`)
- Tests with `pytest`
- Filters like graduation year range or company
- Admin page to add and edit alumni

---

## How to work with Claude on this

- "I'm on Phase 1 step 2. Here's my table design, what would you change?"
- "Give me a hint, not the answer."
- "Review `search.py`."
- "Explain what a cursor actually is."
