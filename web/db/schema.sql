-- ezShell : schéma Neon/Postgres (DEVELOPMENT.md §6). Idempotent.
-- On NE stocke PAS : query, context, commande générée. Seulement des compteurs.

CREATE TABLE IF NOT EXISTS devices (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  token_hash    text NOT NULL UNIQUE,            -- HMAC-SHA256(token, TOKEN_PEPPER)
  user_id       text NULL,                       -- renseigné à la connexion (M3)
  ip_hash       text NOT NULL,                   -- limite d'enregistrements uniquement
  revoked_at    timestamptz NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  last_seen_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS devices_ip_created_idx ON devices (ip_hash, created_at);

-- Flux d'appareil (M3) : créée dès maintenant pour figer le modèle de données.
CREATE TABLE IF NOT EXISTS device_codes (
  device_code_hash text PRIMARY KEY,
  user_code        text NOT NULL UNIQUE,
  device_id        uuid NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  user_id          text NULL,
  status           text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','denied','expired')),
  expires_at       timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_daily (
  subject_type text NOT NULL CHECK (subject_type IN ('device','user','global')),
  subject_id   text NOT NULL,
  day          date NOT NULL,
  count        integer NOT NULL DEFAULT 0,
  PRIMARY KEY (subject_type, subject_id, day)
);

CREATE TABLE IF NOT EXISTS rate_hits (
  subject_id   text NOT NULL,
  window_start timestamptz NOT NULL,
  count        integer NOT NULL DEFAULT 0,
  PRIMARY KEY (subject_id, window_start)
);

CREATE TABLE IF NOT EXISTS settings (
  key   text PRIMARY KEY,
  value text NOT NULL
);
