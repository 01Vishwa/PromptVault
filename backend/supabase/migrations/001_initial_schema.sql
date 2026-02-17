-- PromptVault — Supabase Initial Schema
-- Run this in the Supabase SQL Editor to bootstrap the database.
--
-- Tables:
--   prompts          – prompt namespaces with slug + tags
--   prompt_versions  – immutable, append-only version snapshots
--   deployments      – one active deployment pointer per (prompt, environment)
--   executions       – full LLM invocation audit log

-- ── Extensions ──────────────────────────────────────────────────────────────
create extension if not exists "uuid-ossp";

-- ── 1. Prompts ──────────────────────────────────────────────────────────────
create table if not exists prompts (
    id           uuid primary key default uuid_generate_v4(),
    user_id      uuid not null,  -- references auth.users(id) via RLS
    name         text not null,
    slug         text not null,
    description  text,
    tags         text[] not null default '{}',
    is_archived  boolean not null default false,
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now(),

    constraint uq_prompts_slug unique (slug)
);

-- Row-Level Security: users can only see their own prompts
alter table prompts enable row level security;

create policy "Users can manage their own prompts"
    on prompts for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

-- Auto-update updated_at
create or replace function update_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger trg_prompts_updated_at
    before update on prompts
    for each row execute function update_updated_at();

-- Indexes
create index if not exists idx_prompts_user_id on prompts (user_id);
create index if not exists idx_prompts_slug on prompts (slug);
create index if not exists idx_prompts_tags on prompts using gin (tags);

-- ── 2. Prompt Versions ──────────────────────────────────────────────────────
create table if not exists prompt_versions (
    id              uuid primary key default uuid_generate_v4(),
    prompt_id       uuid not null references prompts(id) on delete cascade,
    version_number  integer not null,
    version_hash    text not null,
    template_text   text not null,
    system_prompt   text,
    variables       text[] not null default '{}',
    model_config    jsonb,
    commit_message  text not null,
    author_id       uuid not null,
    created_at      timestamptz not null default now(),

    constraint uq_version_number unique (prompt_id, version_number),
    constraint uq_version_hash unique (prompt_id, version_hash)
);

-- RLS: versions inherit access from the parent prompt
alter table prompt_versions enable row level security;

create policy "Users can manage versions of their prompts"
    on prompt_versions for all
    using (
        exists (
            select 1 from prompts
            where prompts.id = prompt_versions.prompt_id
              and prompts.user_id = auth.uid()
        )
    )
    with check (
        exists (
            select 1 from prompts
            where prompts.id = prompt_versions.prompt_id
              and prompts.user_id = auth.uid()
        )
    );

-- Indexes
create index if not exists idx_versions_prompt_id on prompt_versions (prompt_id);
create index if not exists idx_versions_number on prompt_versions (prompt_id, version_number desc);

-- ── 3. Deployments ──────────────────────────────────────────────────────────
create table if not exists deployments (
    id                 uuid primary key default uuid_generate_v4(),
    prompt_id          uuid not null references prompts(id) on delete cascade,
    prompt_version_id  uuid not null references prompt_versions(id) on delete cascade,
    environment        text not null default 'production',
    deployed_by        text not null,  -- user UUID as string
    deployed_at        timestamptz not null default now(),
    is_active          boolean not null default true,

    constraint uq_deployment_env unique (prompt_id, environment)
);

-- RLS: deployments inherit access from the parent prompt
alter table deployments enable row level security;

create policy "Users can manage deployments of their prompts"
    on deployments for all
    using (
        exists (
            select 1 from prompts
            where prompts.id = deployments.prompt_id
              and prompts.user_id = auth.uid()
        )
    )
    with check (
        exists (
            select 1 from prompts
            where prompts.id = deployments.prompt_id
              and prompts.user_id = auth.uid()
        )
    );

-- Indexes
create index if not exists idx_deployments_prompt_env on deployments (prompt_id, environment);

-- ── 4. Executions ───────────────────────────────────────────────────────────
create table if not exists executions (
    id                  uuid primary key default uuid_generate_v4(),
    prompt_version_id   uuid not null references prompt_versions(id) on delete cascade,
    user_id             text not null,
    model_provider      text not null,
    model_name          text not null,
    rendered_prompt     text not null,
    system_prompt       text,
    response_text       text,
    tokens_in           integer not null default 0,
    tokens_out          integer not null default 0,
    latency_ms          integer not null default 0,
    cost_estimate       double precision not null default 0.0,
    status              text not null default 'success',
    error_message       text,
    created_at          timestamptz not null default now()
);

-- RLS: users can see their own executions
alter table executions enable row level security;

create policy "Users can view their own executions"
    on executions for all
    using (user_id = auth.uid()::text)
    with check (user_id = auth.uid()::text);

-- Indexes
create index if not exists idx_executions_version on executions (prompt_version_id);
create index if not exists idx_executions_user on executions (user_id);
create index if not exists idx_executions_created on executions (created_at desc);

-- ── Service Role Access ─────────────────────────────────────────────────────
-- The /serve endpoint uses the service_role key which bypasses RLS.
-- No additional policies needed for server-side access.
