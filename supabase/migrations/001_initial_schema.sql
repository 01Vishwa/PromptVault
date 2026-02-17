-- ════════════════════════════════════════════════════════════════════════════
-- PromptVault MVP — Initial Schema
-- Run in Supabase SQL Editor or via supabase db push
-- ════════════════════════════════════════════════════════════════════════════

-- 1. prompts — logical prompt namespace
CREATE TABLE IF NOT EXISTS prompts (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL,
    description     TEXT,
    tags            TEXT[] DEFAULT '{}',
    is_archived     BOOLEAN DEFAULT false NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at      TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(user_id, slug)
);

CREATE INDEX IF NOT EXISTS ix_prompts_user ON prompts(user_id);
CREATE INDEX IF NOT EXISTS ix_prompts_slug ON prompts(slug);

-- 2. prompt_versions — immutable, append-only snapshots
CREATE TABLE IF NOT EXISTS prompt_versions (
    id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    prompt_id         UUID REFERENCES prompts(id) ON DELETE CASCADE NOT NULL,
    version_number    INT NOT NULL,
    version_hash      TEXT NOT NULL,
    template_text     TEXT NOT NULL,
    system_prompt     TEXT,
    variables         TEXT[] DEFAULT '{}',
    model_config      JSONB,
    commit_message    TEXT NOT NULL,
    author_id         UUID REFERENCES auth.users(id) NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT now() NOT NULL,
    UNIQUE(prompt_id, version_number),
    UNIQUE(prompt_id, version_hash)
);

CREATE INDEX IF NOT EXISTS ix_pv_prompt ON prompt_versions(prompt_id);
CREATE INDEX IF NOT EXISTS ix_pv_created ON prompt_versions(created_at);

-- 3. deployments — one active pointer per prompt+environment
CREATE TABLE IF NOT EXISTS deployments (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    prompt_id           UUID REFERENCES prompts(id) ON DELETE CASCADE NOT NULL,
    prompt_version_id   UUID REFERENCES prompt_versions(id) ON DELETE RESTRICT NOT NULL,
    environment         TEXT DEFAULT 'production'
                        CHECK (environment IN ('production', 'staging', 'development')),
    deployed_by         UUID REFERENCES auth.users(id) NOT NULL,
    deployed_at         TIMESTAMPTZ DEFAULT now() NOT NULL,
    is_active           BOOLEAN DEFAULT true NOT NULL,
    UNIQUE(prompt_id, environment)
);

CREATE INDEX IF NOT EXISTS ix_deploy_prompt ON deployments(prompt_id);

-- 4. executions — full log of every LLM call
CREATE TABLE IF NOT EXISTS executions (
    id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    prompt_version_id   UUID REFERENCES prompt_versions(id) ON DELETE SET NULL,
    user_id             UUID REFERENCES auth.users(id) NOT NULL,
    model_provider      TEXT NOT NULL,
    model_name          TEXT NOT NULL,
    rendered_prompt     TEXT,
    system_prompt       TEXT,
    variables_used      JSONB,
    response_text       TEXT,
    tokens_in           INT,
    tokens_out          INT,
    latency_ms          INT,
    cost_estimate       FLOAT,
    status              TEXT DEFAULT 'success'
                        CHECK (status IN ('success', 'error', 'timeout')),
    error_message       TEXT,
    created_at          TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_exec_pv ON executions(prompt_version_id);
CREATE INDEX IF NOT EXISTS ix_exec_user ON executions(user_id);
CREATE INDEX IF NOT EXISTS ix_exec_created ON executions(created_at);


-- ════════════════════════════════════════════════════════════════════════════
-- Row Level Security
-- ════════════════════════════════════════════════════════════════════════════

ALTER TABLE prompts ENABLE ROW LEVEL SECURITY;
CREATE POLICY prompts_select ON prompts FOR SELECT USING (user_id = auth.uid());
CREATE POLICY prompts_insert ON prompts FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY prompts_update ON prompts FOR UPDATE USING (user_id = auth.uid());
CREATE POLICY prompts_delete ON prompts FOR DELETE USING (user_id = auth.uid());

ALTER TABLE prompt_versions ENABLE ROW LEVEL SECURITY;
CREATE POLICY pv_select ON prompt_versions FOR SELECT USING (
    prompt_id IN (SELECT id FROM prompts WHERE user_id = auth.uid())
);
CREATE POLICY pv_insert ON prompt_versions FOR INSERT WITH CHECK (
    author_id = auth.uid()
);

-- Versions are IMMUTABLE: no update or delete policies
-- (Postgres will deny UPDATE/DELETE by default when RLS is on with no matching policy)

ALTER TABLE deployments ENABLE ROW LEVEL SECURITY;
CREATE POLICY deploy_select ON deployments FOR SELECT USING (
    deployed_by = auth.uid()
);
CREATE POLICY deploy_insert ON deployments FOR INSERT WITH CHECK (
    deployed_by = auth.uid()
);
CREATE POLICY deploy_update ON deployments FOR UPDATE USING (
    deployed_by = auth.uid()
);

ALTER TABLE executions ENABLE ROW LEVEL SECURITY;
CREATE POLICY exec_select ON executions FOR SELECT USING (user_id = auth.uid());
CREATE POLICY exec_insert ON executions FOR INSERT WITH CHECK (user_id = auth.uid());

-- Serve endpoint needs to read deployments + versions without auth context
-- Use a service_role key on the backend for that path.


-- ════════════════════════════════════════════════════════════════════════════
-- Helper: auto-update updated_at on prompts
-- ════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prompts_updated_at
    BEFORE UPDATE ON prompts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
