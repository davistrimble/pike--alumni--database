-- Activity tracking + site settings.
-- Safe to run more than once: only adds what's missing, never drops data.
--   psql pike_alumni -f sql/tracking.sql

-- When a member set their password, and when they last logged in.
ALTER TABLE members ADD COLUMN IF NOT EXISTS activated_at TIMESTAMPTZ;
ALTER TABLE members ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;

-- Anyone who already had a password before this column existed counts as activated.
UPDATE members
SET activated_at = create_time
WHERE password_hash IS NOT NULL AND activated_at IS NULL;

-- One row per search. Counts only: the search text is deliberately not stored.
CREATE TABLE IF NOT EXISTS search_events (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per click or copy of an alum's email or LinkedIn.
-- alumni_id is not a foreign key on purpose: schema.sql drops and rebuilds alumni.
CREATE TABLE IF NOT EXISTS contact_events (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    alumni_id INTEGER,
    channel TEXT NOT NULL CHECK (channel IN ('email', 'linkedin')),
    action TEXT NOT NULL CHECK (action IN ('click', 'copy')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS search_events_member_idx ON search_events (member_id);
CREATE INDEX IF NOT EXISTS contact_events_member_idx ON contact_events (member_id);

-- Small key/value table for site settings (the chapter sign-up code lives here).
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
