CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE source_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type TEXT NOT NULL,
    canonical_uri TEXT,
    title TEXT,
    author TEXT,
    language_code TEXT,
    mime_type TEXT,
    first_captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    latest_captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_source_items_source_type ON source_items (source_type);
CREATE INDEX idx_source_items_canonical_uri ON source_items (canonical_uri);
CREATE INDEX idx_source_items_metadata_gin ON source_items USING GIN (metadata);

CREATE TABLE source_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_item_id UUID NOT NULL REFERENCES source_items(id) ON DELETE CASCADE,
    version_no INTEGER NOT NULL,
    capture_method TEXT NOT NULL,
    content_sha256 TEXT,
    size_bytes BIGINT,
    occurred_at TIMESTAMPTZ,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    original_created_at TIMESTAMPTZ,
    original_updated_at TIMESTAMPTZ,
    extractor_version TEXT,
    schema_version TEXT NOT NULL DEFAULT '1',
    referrer_uri TEXT,
    user_agent TEXT,
    browser_profile TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (source_item_id, version_no)
);

CREATE INDEX idx_source_versions_source_item_id ON source_versions (source_item_id);
CREATE INDEX idx_source_versions_captured_at ON source_versions (captured_at DESC);
CREATE INDEX idx_source_versions_occurred_at ON source_versions (occurred_at DESC);
CREATE INDEX idx_source_versions_metadata_gin ON source_versions USING GIN (metadata);

CREATE TABLE binary_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_version_id UUID NOT NULL REFERENCES source_versions(id) ON DELETE CASCADE,
    asset_role TEXT NOT NULL,
    storage_backend TEXT NOT NULL DEFAULT 'local_fs',
    relative_path TEXT NOT NULL,
    file_name TEXT,
    mime_type TEXT,
    size_bytes BIGINT,
    sha256 TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_binary_assets_source_version_id ON binary_assets (source_version_id);
CREATE INDEX idx_binary_assets_asset_role ON binary_assets (asset_role);
CREATE INDEX idx_binary_assets_sha256 ON binary_assets (sha256);

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    source_item_id UUID REFERENCES source_items(id) ON DELETE SET NULL,
    source_version_id UUID REFERENCES source_versions(id) ON DELETE SET NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id TEXT,
    session_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_events_event_type ON events (event_type);
CREATE INDEX idx_events_occurred_at ON events (occurred_at DESC);
CREATE INDEX idx_events_source_item_id ON events (source_item_id);
CREATE INDEX idx_events_metadata_gin ON events USING GIN (metadata);
