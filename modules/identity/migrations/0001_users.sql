-- People who can sign in. One row per account; the sign-in provider's id is `subject`.
-- Names, birth dates and relationships live elsewhere: this table holds only what sign-in needs.
CREATE TABLE IF NOT EXISTS users (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    subject     text        NOT NULL UNIQUE,
    email       text        NOT NULL,
    role        text        NOT NULL,
    status      text        NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'disabled')),
    invited_by  uuid        REFERENCES users (id) ON DELETE SET NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower ON users (lower(email));
