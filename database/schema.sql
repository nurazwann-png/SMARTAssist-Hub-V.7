-- =============================================================================
-- SMARTAssist Hub V.7 — PostgreSQL Schema
-- =============================================================================
-- Jalankan sekali untuk sediakan semua jadual:
--   psql -U <user> -d smartassist -f schema.sql
-- =============================================================================

-- Aktifkan UUID generator (PostgreSQL 13+)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- =============================================================================
-- 1. PENGGUNA (user_profiles)
--    Sumber: OAuth Google — satu rekod per akaun Google
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    google_sub      TEXT        PRIMARY KEY,            -- Google OAuth unique ID
    email           TEXT        NOT NULL UNIQUE,
    nama            TEXT        NOT NULL DEFAULT '',
    jawatan         TEXT        NOT NULL DEFAULT '',
    stesen          TEXT        NOT NULL DEFAULT '',
    daerah          TEXT        NOT NULL DEFAULT '',
    negeri          TEXT        NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles (email);


-- =============================================================================
-- 2. SESI CHAT (sessions)
--    Satu rekod per sesi perbualan; setiap sesi terikat kepada satu pengguna
--    dan satu ejen (agent).
-- =============================================================================

CREATE TABLE IF NOT EXISTS sessions (
    session_id      TEXT        PRIMARY KEY,
    google_sub      TEXT        REFERENCES user_profiles (google_sub) ON DELETE SET NULL,
    agent           TEXT        NOT NULL DEFAULT '',    -- 'letter_generator', 'document_reviewer', dll.
    title           TEXT        NOT NULL DEFAULT '',    -- 60 aksara pertama mesej pertama
    msg_count       INTEGER     NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user   ON sessions (google_sub);
CREATE INDEX IF NOT EXISTS idx_sessions_agent  ON sessions (agent);
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions (updated_at DESC);


-- =============================================================================
-- 3. MESEJ CHAT (messages)
--    Setiap baris ialah satu giliran perbualan (user / assistant).
-- =============================================================================

CREATE TABLE IF NOT EXISTS messages (
    id              BIGSERIAL   PRIMARY KEY,
    session_id      TEXT        NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    role            TEXT        NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT        NOT NULL DEFAULT '',
    meta            JSONB       NOT NULL DEFAULT '{}', -- maklumat tambahan (ejen, dll.)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_session  ON messages (session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created  ON messages (session_id, created_at);


-- =============================================================================
-- 4. KV STORE — Keadaan Ejen (kv_store)
--    Simpanan serba-guna JSON per-sesi untuk semua ejen.
--    namespace: 'letter' | 'report' | 'reviewer' | 'kpm' | 'report_images'
-- =============================================================================

CREATE TABLE IF NOT EXISTS kv_store (
    session_id      TEXT        NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    namespace       TEXT        NOT NULL,
    key             TEXT        NOT NULL,
    value           JSONB       NOT NULL DEFAULT 'null',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (session_id, namespace, key)
);

CREATE INDEX IF NOT EXISTS idx_kv_session_ns ON kv_store (session_id, namespace);


-- =============================================================================
-- 5. MAKLUM BALAS PENGGUNA (feedback)
--    Sebelum ini hilang ketika server dimulakan semula (in-memory sahaja).
-- =============================================================================

CREATE TABLE IF NOT EXISTS feedback (
    id              BIGSERIAL   PRIMARY KEY,
    session_id      TEXT        NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    message_index   INTEGER     NOT NULL,               -- kedudukan mesej dalam sesi
    rating          TEXT        NOT NULL CHECK (rating IN ('up', 'down')),
    agent           TEXT        NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback (session_id);
CREATE INDEX IF NOT EXISTS idx_feedback_agent   ON feedback (agent);


-- =============================================================================
-- 6. KOP SURAT / LOGO (letterheads)
--    Sebelum ini disimpan dalam fail JSON rata (static/letterheads/metadata.json).
-- =============================================================================

CREATE TABLE IF NOT EXISTS letterheads (
    id                      TEXT        PRIMARY KEY DEFAULT 'lh_' || encode(gen_random_bytes(4), 'hex'),
    google_sub              TEXT        REFERENCES user_profiles (google_sub) ON DELETE SET NULL,
    name                    TEXT        NOT NULL DEFAULT '',
    filename                TEXT        NOT NULL,       -- nama fail fizikal di disk
    original_name           TEXT        NOT NULL DEFAULT '',
    type                    TEXT        NOT NULL DEFAULT 'letterhead' CHECK (type IN ('letterhead', 'logo')),
    is_active               BOOLEAN     NOT NULL DEFAULT FALSE,
    uploaded_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_letterheads_user ON letterheads (google_sub);


-- =============================================================================
-- 7. DOKUMEN DIJANA — Surat Rasmi & Memo (generated_letters)
--    Dokumen yang dihasilkan oleh ejen letter_generator.
-- =============================================================================

CREATE TABLE IF NOT EXISTS generated_letters (
    id              BIGSERIAL   PRIMARY KEY,
    session_id      TEXT        NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    google_sub      TEXT        REFERENCES user_profiles (google_sub) ON DELETE SET NULL,
    doc_type        TEXT        NOT NULL CHECK (doc_type IN ('surat', 'memo')),

    -- Medan dokumen (boleh null jika tidak berkenaan dengan jenis dokumen)
    rujukan         TEXT,
    tarikh          TEXT,
    tajuk           TEXT,
    isi             TEXT,

    -- Penerima (surat rasmi)
    penerima_nama           TEXT,
    penerima_jawatan        TEXT,
    penerima_organisasi     TEXT,
    penerima_alamat         TEXT,

    -- Memo — peserta
    pengerusi       TEXT,
    penyelaras      TEXT,
    ahli            TEXT,
    urus_setia      TEXT,

    -- Acara (memo)
    tarikh_acara    TEXT,
    masa_acara      TEXT,
    tempat_acara    TEXT,

    -- Penandatangan
    penandatangan_nama      TEXT,
    penandatangan_jawatan   TEXT,
    nama_pejabat            TEXT,

    -- Salinan kepada (surat)
    salinan_kepada  TEXT,

    -- Teks penuh dokumen yang dijana
    document_text   TEXT        NOT NULL DEFAULT '',

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_letters_session ON generated_letters (session_id);
CREATE INDEX IF NOT EXISTS idx_letters_user    ON generated_letters (google_sub);


-- =============================================================================
-- 8. LAPORAN DIJANA (generated_reports)
--    Laporan Satu Muka Surat yang dihasilkan oleh ejen report_generator.
-- =============================================================================

CREATE TABLE IF NOT EXISTS generated_reports (
    id              BIGSERIAL   PRIMARY KEY,
    session_id      TEXT        NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    google_sub      TEXT        REFERENCES user_profiles (google_sub) ON DELETE SET NULL,

    nama_program            TEXT,
    tarikh_program          TEXT,
    hari                    TEXT,
    masa                    TEXT,
    organisasi              TEXT,

    pegawai_nama            TEXT,
    pegawai_jawatan         TEXT,

    objektif                TEXT,
    rumusan                 TEXT,
    cadangan                TEXT,

    penyedia_nama           TEXT,
    penyedia_jawatan        TEXT,
    tarikh_disediakan       TEXT,

    pengesah_nama           TEXT,
    pengesah_jawatan        TEXT,

    document_text           TEXT        NOT NULL DEFAULT '',

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_session ON generated_reports (session_id);
CREATE INDEX IF NOT EXISTS idx_reports_user    ON generated_reports (google_sub);


-- =============================================================================
-- 9. IMEJ LAPORAN (report_images)
--    Imej yang dimuat naik semasa sesi report_generator.
--    Fail fizikal disimpan di static/report_images/.
-- =============================================================================

CREATE TABLE IF NOT EXISTS report_images (
    id              BIGSERIAL   PRIMARY KEY,
    session_id      TEXT        NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    filename        TEXT        NOT NULL,               -- nama fail asal
    safe_name       TEXT        NOT NULL,               -- nama fail selamat di disk
    file_path       TEXT        NOT NULL,               -- laluan mutlak
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_report_images_session ON report_images (session_id);


-- =============================================================================
-- 10. SEMAKAN DOKUMEN (document_reviews)
--     Keputusan semakan yang dihasilkan oleh ejen document_reviewer.
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_reviews (
    id              BIGSERIAL   PRIMARY KEY,
    session_id      TEXT        NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    google_sub      TEXT        REFERENCES user_profiles (google_sub) ON DELETE SET NULL,

    filename        TEXT        NOT NULL DEFAULT '',
    doc_type        TEXT        NOT NULL DEFAULT '',    -- 'Surat Rasmi', 'Memo Dalaman', dll.
    char_count      INTEGER     NOT NULL DEFAULT 0,

    score           TEXT,                               -- 'A', 'B', 'C', 'D'
    summary         TEXT,
    issues          JSONB       NOT NULL DEFAULT '[]',  -- array isu dari AI

    doc_text        TEXT        NOT NULL DEFAULT '',    -- teks dokumen yang disemak
    doc_html        TEXT,                               -- HTML kaya (untuk DOCX)

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reviews_session ON document_reviews (session_id);
CREATE INDEX IF NOT EXISTS idx_reviews_user    ON document_reviews (google_sub);
CREATE INDEX IF NOT EXISTS idx_reviews_score   ON document_reviews (score);


-- =============================================================================
-- 11. SET DATA ANALISIS (uploaded_datasets)
--     Fail CSV/Excel yang dimuat naik untuk ejen data_analysis.
--     Sebelum ini hanya dalam memori + fail JSON sementara.
-- =============================================================================

CREATE TABLE IF NOT EXISTS uploaded_datasets (
    id              BIGSERIAL   PRIMARY KEY,
    session_id      TEXT        NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    google_sub      TEXT        REFERENCES user_profiles (google_sub) ON DELETE SET NULL,

    filename        TEXT        NOT NULL,
    row_count       INTEGER     NOT NULL DEFAULT 0,
    col_count       INTEGER     NOT NULL DEFAULT 0,
    columns         JSONB       NOT NULL DEFAULT '[]',  -- senarai nama lajur
    summary         TEXT        NOT NULL DEFAULT '',    -- ringkasan statistik
    full_data_csv   TEXT        NOT NULL DEFAULT '',    -- data CSV (sehingga 500 baris)

    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_datasets_session ON uploaded_datasets (session_id);
CREATE INDEX IF NOT EXISTS idx_datasets_user    ON uploaded_datasets (google_sub);


-- =============================================================================
-- TRIGGER: kemaskini updated_at secara automatik
-- =============================================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Pasang trigger pada jadual yang ada lajur updated_at
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['user_profiles', 'sessions'] LOOP
        EXECUTE format('
            CREATE OR REPLACE TRIGGER trg_%s_updated_at
            BEFORE UPDATE ON %s
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        ', t, t);
    END LOOP;
END;
$$;
