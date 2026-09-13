SET search_path TO public;

-- =============================================================================
-- SMARTAssist Hub V.7 — Migration 001
-- Tambah table yang belum ada: document_versions, audit_logs,
-- login_history, user_preferences, scheduled_tasks
-- Jalankan: python database/run_migration.py
-- =============================================================================


-- =============================================================================
-- 1. VERSI DOKUMEN (document_versions)
--    Sebelum ini dicipta secara lazy dalam backend/doc_versions.py.
--    Ditambah ke schema utama untuk konsistensi.
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_versions (
    id             SERIAL      PRIMARY KEY,
    session_id     TEXT        NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    agent          TEXT        NOT NULL,                    -- 'letter_generator' | 'report_generator'
    version_number INTEGER     NOT NULL,
    doc_type       TEXT        NOT NULL DEFAULT '',
    fields         JSONB       NOT NULL DEFAULT '{}'::jsonb,
    document_text  TEXT        NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, agent, version_number)
);

CREATE INDEX IF NOT EXISTS idx_doc_versions_lookup
    ON document_versions (session_id, agent, version_number DESC);


-- =============================================================================
-- 2. LOG AUDIT (audit_logs)
--    Rekod setiap tindakan penting pengguna — diperlukan untuk pematuhan MOE.
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id             BIGSERIAL   PRIMARY KEY,
    google_sub     TEXT        REFERENCES user_profiles (google_sub) ON DELETE SET NULL,
    email          TEXT,                                    -- disimpan berasingan sekiranya akaun dipadam
    action         TEXT        NOT NULL,                    -- 'login' | 'upload' | 'generate' | 'download' | 'delete'
    resource_type  TEXT,                                    -- 'document' | 'dataset' | 'session' | dll.
    resource_id    TEXT,                                    -- ID sumber yang dikenakan tindakan
    detail         JSONB       NOT NULL DEFAULT '{}',       -- maklumat tambahan (nama fail, ejen, dll.)
    ip_address     TEXT,
    user_agent     TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_user    ON audit_logs (google_sub);
CREATE INDEX IF NOT EXISTS idx_audit_action  ON audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs (created_at DESC);


-- =============================================================================
-- 3. SEJARAH LOG MASUK (login_history)
--    Rekod setiap percubaan log masuk — berjaya atau gagal.
-- =============================================================================

CREATE TABLE IF NOT EXISTS login_history (
    id             BIGSERIAL   PRIMARY KEY,
    google_sub     TEXT        REFERENCES user_profiles (google_sub) ON DELETE SET NULL,
    email          TEXT,
    success        BOOLEAN     NOT NULL DEFAULT TRUE,
    failure_reason TEXT,                                    -- null jika berjaya
    ip_address     TEXT,
    user_agent     TEXT,
    login_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_login_user    ON login_history (google_sub);
CREATE INDEX IF NOT EXISTS idx_login_email   ON login_history (email);
CREATE INDEX IF NOT EXISTS idx_login_created ON login_history (login_at DESC);


-- =============================================================================
-- 4. KEUTAMAAN PENGGUNA (user_preferences)
--    Tetapan individu setiap pengguna — bahasa, ejen lalai, dll.
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_preferences (
    google_sub          TEXT        PRIMARY KEY REFERENCES user_profiles (google_sub) ON DELETE CASCADE,
    language            TEXT        NOT NULL DEFAULT 'BM' CHECK (language IN ('BM', 'EN')),
    default_agent       TEXT        NOT NULL DEFAULT 'letter_generator',
    email_notifications BOOLEAN     NOT NULL DEFAULT FALSE,
    theme               TEXT        NOT NULL DEFAULT 'dark' CHECK (theme IN ('dark', 'light')),
    extra               JSONB       NOT NULL DEFAULT '{}',  -- untuk tetapan tambahan masa depan
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- =============================================================================
-- 5. TUGASAN BERJADUAL (scheduled_tasks)
--    Automasi berkala — analisis mingguan, laporan automatik, dll.
-- =============================================================================

CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id              TEXT        PRIMARY KEY DEFAULT 'sched_' || left(replace(gen_random_uuid()::text, '-', ''), 8),
    google_sub      TEXT        REFERENCES user_profiles (google_sub) ON DELETE CASCADE,
    name            TEXT        NOT NULL DEFAULT '',        -- nama mesra pengguna
    cron_expression TEXT        NOT NULL,                   -- contoh: '0 8 * * 1' = Isnin 8am
    agent_type      TEXT        NOT NULL,                   -- ejen yang akan dijalankan
    payload         JSONB       NOT NULL DEFAULT '{}',      -- parameter tugasan
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    last_run_at     TIMESTAMPTZ,
    next_run_at     TIMESTAMPTZ,
    run_count       INTEGER     NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sched_user   ON scheduled_tasks (google_sub);
CREATE INDEX IF NOT EXISTS idx_sched_active ON scheduled_tasks (is_active, next_run_at);


-- =============================================================================
-- Trigger updated_at untuk jadual baru yang memerlukannya
-- =============================================================================

DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['user_preferences', 'scheduled_tasks'] LOOP
        EXECUTE format('
            CREATE OR REPLACE TRIGGER trg_%s_updated_at
            BEFORE UPDATE ON %s
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        ', t, t);
    END LOOP;
END;
$$;
