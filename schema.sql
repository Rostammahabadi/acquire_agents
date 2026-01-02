-- SaaS Acquisition System Data Models
-- Production-ready PostgreSQL schema for automated business acquisition platform

-- =============================================================================
-- 1. RAW LISTING INGESTION MODEL
-- Stores verbatim scraped data - append-only, no interpretation
-- =============================================================================

CREATE TABLE raw_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL, -- Stable UUID per unique business listing
    marketplace TEXT NOT NULL, -- e.g., 'acquire.com', 'flippa'
    listing_url TEXT NOT NULL, -- Full URL of the scraped listing
    scrape_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_html TEXT, -- Full raw HTML content (can be large)
    raw_text TEXT, -- Extracted plaintext content
    listing_category TEXT, -- Raw category from marketplace
    seller_country TEXT, -- Raw country/location data
    asking_price_raw TEXT, -- Raw asking price string
    revenue_raw TEXT, -- Raw revenue string
    profit_raw TEXT, -- Raw profit string
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX ix_raw_listings_business_id ON raw_listings(business_id);
CREATE INDEX ix_raw_listings_marketplace ON raw_listings(marketplace);
CREATE INDEX ix_raw_listings_scrape_timestamp ON raw_listings(scrape_timestamp);
-- Composite index for finding latest scrape per business
CREATE INDEX ix_raw_listings_business_scrape ON raw_listings(business_id, scrape_timestamp);

-- Comments explaining design choices
COMMENT ON TABLE raw_listings IS 'Raw scraped listing data - append-only storage preserving verbatim marketplace data';
COMMENT ON COLUMN raw_listings.business_id IS 'Stable UUID per unique business listing across marketplaces';
COMMENT ON COLUMN raw_listings.scrape_timestamp IS 'When this listing was scraped - allows multiple scrapes per listing';

-- =============================================================================
-- 2. CANONICAL BUSINESS RECORD (CATEGORIZATION AGENT OUTPUT)
-- Strictly structured, normalized business facts - append-only versioning
-- =============================================================================

CREATE TABLE canonical_business_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL, -- References business_id in raw_listings (application-level constraint)
    version INTEGER NOT NULL DEFAULT 1, -- Incrementing version for append-only updates
    agent_run_id TEXT NOT NULL, -- ID of the agent run that produced this record
    content_hash TEXT NOT NULL, -- SHA-256 hash of input content for versioning

    -- Financials domain - structured financial metrics
    financials JSONB, -- asking_price_usd, monthly_revenue_usd, ttm_revenue_usd, etc.

    -- Product domain - product/service details
    product JSONB, -- product_type, vertical, b2b_or_b2c, core_features[], etc.

    -- Customers domain - customer metrics and risk
    customers JSONB, -- customer_count_estimate, customer_type, churn_rate_percent, etc.

    -- Operations domain - operational details and dependencies
    operations JSONB, -- owner_hours_per_week, dependencies[], key_person_risk, etc.

    -- Technology domain - tech stack and infrastructure
    technology JSONB, -- tech_stack[], hosting_provider, code_ownership_confirmed, etc.

    -- Growth domain - growth metrics and channels
    growth JSONB, -- acquisition_channels[], recent_growth_trend, marketing_spend_disclosed

    -- Risks domain - risk assessment
    risks JSONB, -- platform_dependency[], regulatory_risk, ip_risk

    -- Seller domain - seller information
    seller JSONB, -- seller_location, reason_for_selling, seller_involvement_post_sale

    -- Confidence and uncertainty flags
    confidence_flags JSONB, -- missing_financials, ambiguous_metrics[], assumptions_made[]

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX ix_canonical_business_business_id ON canonical_business_records(business_id);
CREATE INDEX ix_canonical_business_created_at ON canonical_business_records(created_at);
-- Composite index for finding latest version per business
CREATE INDEX ix_canonical_business_version ON canonical_business_records(business_id, version DESC);

-- Comments explaining design choices
COMMENT ON TABLE canonical_business_records IS 'Normalized business facts from categorization agent - append-only versioning';
COMMENT ON COLUMN canonical_business_records.version IS 'Incrementing version number for append-only updates';
COMMENT ON COLUMN canonical_business_records.financials IS 'Financial metrics with explicit uncertainty representation';

-- =============================================================================
-- 3. SCORING & RANKING MODEL
-- Scoring agent outputs with historical tracking
-- =============================================================================

CREATE TABLE scoring_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL, -- References business_id in raw_listings (application-level constraint)
    canonical_record_id UUID NOT NULL, -- References id in canonical_business_records (application-level constraint)
    scoring_run_id TEXT NOT NULL, -- ID of the scoring run/agent execution

    -- Overall scores
    total_score NUMERIC(5,2) NOT NULL CHECK (total_score >= 0 AND total_score <= 100),
    tier TEXT NOT NULL CHECK (tier IN ('A', 'B', 'C', 'D')),

    -- Component scores (0-100 scale)
    price_efficiency_score NUMERIC(5,2) NOT NULL CHECK (price_efficiency_score >= 0 AND price_efficiency_score <= 100),
    revenue_quality_score NUMERIC(5,2) NOT NULL CHECK (revenue_quality_score >= 0 AND revenue_quality_score <= 100),
    moat_score NUMERIC(5,2) NOT NULL CHECK (moat_score >= 0 AND moat_score <= 100),
    ai_leverage_score NUMERIC(5,2) NOT NULL CHECK (ai_leverage_score >= 0 AND ai_leverage_score <= 100),
    operations_score NUMERIC(5,2) NOT NULL CHECK (operations_score >= 0 AND operations_score <= 100),
    risk_score NUMERIC(5,2) NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
    trust_score NUMERIC(5,2) NOT NULL CHECK (trust_score >= 0 AND trust_score <= 100),

    -- Top factors (arrays for flexible content)
    top_buy_reasons JSONB, -- Array of top reasons to pursue acquisition
    top_risks JSONB, -- Array of top risks identified

    scoring_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes optimized for scoring queries
CREATE INDEX ix_scoring_records_business_id ON scoring_records(business_id);
CREATE INDEX ix_scoring_records_canonical_record_id ON scoring_records(canonical_record_id);
CREATE INDEX ix_scoring_records_total_score ON scoring_records(total_score DESC);
CREATE INDEX ix_scoring_records_tier ON scoring_records(tier);
CREATE INDEX ix_scoring_records_scoring_timestamp ON scoring_records(scoring_timestamp);
-- Composite indexes for common query patterns
CREATE INDEX ix_scoring_tier_timestamp ON scoring_records(tier, scoring_timestamp DESC);
CREATE INDEX ix_scoring_business_timestamp ON scoring_records(business_id, scoring_timestamp DESC);

-- Comments explaining design choices
COMMENT ON TABLE scoring_records IS 'Scoring agent outputs with historical tracking of score changes';
COMMENT ON COLUMN scoring_records.total_score IS 'Overall business score (0-100 scale)';
COMMENT ON COLUMN scoring_records.tier IS 'Score tier classification for easy filtering';

-- =============================================================================
-- 4. FOLLOW-UP QUESTION MODEL
-- Auto-generated questions and seller responses
-- =============================================================================

CREATE TABLE follow_up_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL, -- References business_id in raw_listings (application-level constraint)
    canonical_record_id UUID NOT NULL, -- References id in canonical_business_records (application-level constraint)

    question_text TEXT NOT NULL, -- Generated question for seller
    triggered_by_field TEXT NOT NULL, -- Field/uncertainty that triggered this question
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),

    -- Response tracking
    seller_response TEXT, -- Seller's response text
    response_timestamp TIMESTAMPTZ, -- When seller responded
    response_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (response_status IN ('pending', 'responded', 'no_response', 'escalated')),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for follow-up queries
CREATE INDEX ix_followup_business_id ON follow_up_questions(business_id);
CREATE INDEX ix_followup_canonical_record_id ON follow_up_questions(canonical_record_id);
CREATE INDEX ix_followup_response_status ON follow_up_questions(response_status);
CREATE INDEX ix_followup_severity ON follow_up_questions(severity);
-- Composite indexes for common query patterns
CREATE INDEX ix_followup_business_status ON follow_up_questions(business_id, response_status);
CREATE INDEX ix_followup_severity_created ON follow_up_questions(severity, created_at);

-- Comments explaining design choices
COMMENT ON TABLE follow_up_questions IS 'Auto-generated follow-up questions and seller responses';
COMMENT ON COLUMN follow_up_questions.triggered_by_field IS 'Links question to specific uncertainty in canonical record';
COMMENT ON COLUMN follow_up_questions.response_status IS 'Tracks response workflow state';

-- =============================================================================
-- 5. AGENT EXECUTION LOG
-- Lightweight audit table for agent executions
-- =============================================================================

CREATE TABLE agent_execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL, -- 'categorization', 'scoring', etc.
    business_id UUID NOT NULL, -- References business_id in raw_listings (application-level constraint)

    execution_id TEXT NOT NULL, -- Unique ID for this agent execution
    input_snapshot JSONB, -- Snapshot of input data used by agent
    status TEXT NOT NULL CHECK (status IN ('success', 'failure', 'partial', 'timeout')),
    error_message TEXT, -- Error details if failed
    execution_metadata JSONB, -- Additional details: duration, token usage, etc.

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ -- Completion timestamp
);

-- Indexes for monitoring and debugging queries
CREATE INDEX ix_agent_exec_agent_name ON agent_execution_logs(agent_name);
CREATE INDEX ix_agent_exec_business_id ON agent_execution_logs(business_id);
CREATE INDEX ix_agent_exec_status ON agent_execution_logs(status);
CREATE INDEX ix_agent_exec_started_at ON agent_execution_logs(started_at);
-- Composite indexes for common query patterns
CREATE INDEX ix_agent_exec_business_status ON agent_execution_logs(business_id, status);
CREATE INDEX ix_agent_exec_name_started ON agent_execution_logs(agent_name, started_at DESC);

-- Comments explaining design choices
COMMENT ON TABLE agent_execution_logs IS 'Lightweight audit log for agent executions and debugging';
COMMENT ON COLUMN agent_execution_logs.input_snapshot IS 'Stores input data snapshot for reproducibility';
COMMENT ON COLUMN agent_execution_logs.execution_metadata IS 'Flexible storage for performance metrics and debugging info';

-- =============================================================================
-- ADDITIONAL INDEXES FOR COMMON QUERY PATTERNS
-- Optimized for the specified use cases
-- =============================================================================

-- "Top scored businesses" - get highest scoring businesses
CREATE INDEX ix_top_scored_businesses ON scoring_records(total_score DESC, scoring_timestamp DESC);

-- "Requires follow-up" - businesses needing follow-up questions
CREATE INDEX ix_requires_followup ON follow_up_questions(business_id, created_at DESC)
WHERE response_status = 'pending' AND severity IN ('critical', 'high');

-- "Newly scraped listings" - recent listings that need processing (will be maintained by application)
-- Note: Partial indexes with time-based conditions should be managed by application logic
CREATE INDEX ix_recent_listings ON raw_listings(scrape_timestamp DESC, marketplace);

-- "Business processing status" - check if business has been processed by all agents
CREATE INDEX CONCURRENTLY ix_business_processing_status ON canonical_business_records(business_id, created_at DESC);

-- =============================================================================
-- CONSTRAINTS AND DATA INTEGRITY
-- =============================================================================

-- Ensure business_id uniqueness across marketplaces (optional - depends on business logic)
-- ALTER TABLE raw_listings ADD CONSTRAINT unique_business_per_marketplace UNIQUE (business_id, marketplace);

-- Ensure version increments properly (trigger-based - would need PL/pgSQL function)
-- This ensures append-only versioning works correctly

-- Ensure scoring timestamps are not in the future
ALTER TABLE scoring_records ADD CONSTRAINT check_scoring_timestamp_not_future
    CHECK (scoring_timestamp <= NOW());

-- Ensure response timestamps are after question creation
ALTER TABLE follow_up_questions ADD CONSTRAINT check_response_after_question
    CHECK (response_timestamp IS NULL OR response_timestamp >= created_at);

-- =============================================================================
-- 6. SECTOR DEEP RESEARCH AGENT OUTPUTS
-- Stores structured outputs from deep research agents (market, platform, etc.)
-- Append-only, versioned, reusable across businesses
-- =============================================================================

CREATE TABLE sector_research_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Scope & linkage
    business_id UUID,
    -- Nullable on purpose: allows sector-only research not tied to a specific listing

    sector_key TEXT NOT NULL,
    -- Canonical sector identifier, e.g.:
    -- 'ad_monetized_mobile_word_games'
    -- 'enterprise_crypto_analytics_saas'

    agent_type TEXT NOT NULL
        CHECK (agent_type IN (
            'market_structure',
            'platform_risk',
            'monetization',
            'competition',
            'buyer_exit',
            'synthesis'
        )),

    research_run_id TEXT NOT NULL,
    -- Stable ID for one orchestrated deep-research run

    version INTEGER NOT NULL DEFAULT 1,
    -- Increment when you intentionally re-run research for same sector + agent

    content_hash TEXT NOT NULL,
    -- SHA-256 hash of (sector_key + agent_type + prompt_version)
    -- Used to prevent duplicate inserts

    -- Core payload
    agent_output JSONB NOT NULL,
    -- Must match the strict JSON schema enforced by that agent

    -- Metadata & traceability
    model_name TEXT NOT NULL, -- e.g. 'o4-mini-deep-research'
    prompt_version TEXT NOT NULL,
    -- Allows you to invalidate old research if prompts change

    sources JSONB,
    -- Optional explicit extraction for source URLs if present

    confidence_level TEXT
        CHECK (confidence_level IN ('high', 'medium', 'low')),
    -- Optional synthesis or agent-provided confidence

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Primary lookup: all research for a business
CREATE INDEX ix_sector_research_business_id
    ON sector_research_records(business_id);

-- Sector-level reuse
CREATE INDEX ix_sector_research_sector_key
    ON sector_research_records(sector_key);

-- Agent-specific queries
CREATE INDEX ix_sector_research_agent_type
    ON sector_research_records(agent_type);

-- Versioned lookup
CREATE INDEX ix_sector_research_sector_agent_version
    ON sector_research_records(sector_key, agent_type, version DESC);

-- Fast deduplication / cache checks
CREATE UNIQUE INDEX ux_sector_research_dedup
    ON sector_research_records(sector_key, agent_type, content_hash);

-- Time-based analysis
CREATE INDEX ix_sector_research_created_at
    ON sector_research_records(created_at DESC);

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE sector_research_records IS
'Append-only storage of deep research agent outputs by sector and agent type';

COMMENT ON COLUMN sector_research_records.sector_key IS
'Canonical identifier for the sector being researched';

COMMENT ON COLUMN sector_research_records.agent_type IS
'Type of deep research agent that produced this output';

COMMENT ON COLUMN sector_research_records.agent_output IS
'Structured JSON output produced by the deep research agent';

COMMENT ON COLUMN sector_research_records.content_hash IS
'Deduplication hash to prevent storing identical research outputs';
