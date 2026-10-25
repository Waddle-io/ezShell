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

-- ---------------------------------------------------------------------------
-- v2 : comptes, plans, mesure. Additif et idempotent : rien n'est supprimé ni modifié.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
  id                   text PRIMARY KEY,                 -- uuid en texte (devices.user_id est de type text)
  email                text NULL,                        -- toujours vérifié (GitHub ou lien magique)
  github_id            text NULL,
  github_login         text NULL,
  plan                 text NOT NULL DEFAULT 'free' CHECK (plan IN ('free','premium','unlimited')),
  daily_limit_override integer NULL,                     -- limite personnalisée (ignorée pour 'unlimited')
  override_expires_at  timestamptz NULL,
  status               text NOT NULL DEFAULT 'active' CHECK (status IN ('active','banned')),
  created_at           timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS users_email_idx ON users (lower(email)) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS users_github_idx ON users (github_id) WHERE github_id IS NOT NULL;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'devices_user_fk') THEN
    ALTER TABLE devices ADD CONSTRAINT devices_user_fk FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
  END IF;
END $$;

-- Liens magiques par e-mail : seul le haché du jeton est stocké, usage unique.
CREATE TABLE IF NOT EXISTS login_tokens (
  token_hash text PRIMARY KEY,
  email      text NOT NULL,
  user_code  text NULL,                                  -- code d'appareil à approuver (NULL = simple connexion web)
  expires_at timestamptz NOT NULL,
  used_at    timestamptz NULL
);

-- Mesure d'usage. AUCUN contenu : ni requête, ni contexte, ni commande, ni réponse.
-- fingerprint = HMAC(pepper, forme normalisée de la demande) : sert uniquement à compter les doublons.
CREATE TABLE IF NOT EXISTS ask_metrics (
  id                bigserial PRIMARY KEY,
  at                timestamptz NOT NULL DEFAULT now(),
  tier              text NOT NULL CHECK (tier IN ('anonymous','free','premium','unlimited')),
  mode              text NOT NULL,
  outcome           text NOT NULL,
  prompt_tokens     integer NULL,
  completion_tokens integer NULL,
  latency_ms        integer NULL,
  fingerprint       text NULL
);
CREATE INDEX IF NOT EXISTS ask_metrics_at_idx ON ask_metrics (at);
