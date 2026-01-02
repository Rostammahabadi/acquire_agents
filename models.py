from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, JSON, Index


class RawListing(SQLModel, table=True):
    """
    Raw scraped listing data - append-only storage preserving verbatim marketplace data.

    Design choices:
    - business_id is stable UUID per unique listing across marketplaces
    - Multiple scrapes per listing allowed (composite index on business_id + scrape_timestamp)
    - Stores full raw HTML/text without any interpretation or parsing
    - No foreign keys to allow independent ingestion from parallel scrapers
    """
    __tablename__ = "raw_listings"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    business_id: str = Field(index=True, description="Stable UUID per unique business listing")
    marketplace: str = Field(index=True, description="e.g., 'acquire.com', 'flippa'")
    listing_url: str = Field(description="Full URL of the scraped listing")
    scrape_timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    raw_html: Optional[str] = Field(description="Full raw HTML content")
    raw_text: Optional[str] = Field(description="Extracted plaintext content")
    listing_category: Optional[str] = Field(description="Raw category from marketplace")
    seller_country: Optional[str] = Field(description="Raw country/location data")
    asking_price_raw: Optional[str] = Field(description="Raw asking price string")
    revenue_raw: Optional[str] = Field(description="Raw revenue string")
    profit_raw: Optional[str] = Field(description="Raw profit string")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Composite index for finding latest scrape per business
    __table_args__ = (
        Index('ix_raw_listings_business_scrape', 'business_id', 'scrape_timestamp'),
    )


class CanonicalBusinessRecord(SQLModel, table=True):
    """
    Normalized, structured business facts extracted by categorization agent.

    Design choices:
    - Append-only: each analysis creates new version with incremented version_id
    - JSONB fields for flexible nested structures while maintaining queryability
    - Explicit confidence flags and uncertainty representation
    - business_id references raw_listings (enforced at application level)
    """
    __tablename__ = "canonical_business_records"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    business_id: str = Field(index=True, description="References business_id in raw_listings")
    version: int = Field(default=1, description="Incrementing version for append-only updates")
    agent_run_id: str = Field(description="ID of the agent run that produced this record")
    content_hash: str = Field(description="SHA-256 hash of input content for versioning")

    # Financials domain
    financials: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Financial metrics: asking_price_usd, monthly_revenue_usd, etc."
    )

    # Product domain
    product: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Product details: type, vertical, features array, etc."
    )

    # Customers domain
    customers: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Customer metrics: count, type, churn, concentration risk"
    )

    # Operations domain
    operations: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Operational details: owner hours, dependencies, key person risk"
    )

    # Technology domain
    technology: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Tech stack, hosting, code ownership, API dependencies"
    )

    # Growth domain
    growth: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Growth metrics: channels, trends, marketing spend"
    )

    # Risks domain
    risks: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Risk assessment: platform dependency, regulatory, IP"
    )

    # Seller domain
    seller: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Seller details: location, selling reason, post-sale involvement"
    )

    # Confidence and uncertainty flags
    confidence_flags: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Uncertainty indicators: missing data, assumptions, follow-up needs"
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Indexes for common queries
    __table_args__ = (
        Index('ix_canonical_business_version', 'business_id', 'version'),
        Index('ix_canonical_business_created', 'created_at'),
    )


class ScoringRecord(SQLModel, table=True):
    """
    Scoring agent outputs with historical tracking of score changes.

    Design choices:
    - One score per business per run (versioned by scoring_run_id)
    - Individual score components as numeric fields for easy querying/aggregation
    - Arrays for top reasons/risks as JSONB for flexible content
    - business_id references raw_listings, canonical_record_id references canonical_business_records
    """
    __tablename__ = "scoring_records"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    business_id: str = Field(index=True, description="References business_id in raw_listings")
    canonical_record_id: str = Field(index=True, description="References id in canonical_business_records")
    scoring_run_id: str = Field(description="ID of the scoring run/agent execution")

    # Overall scores
    total_score: float = Field(description="Overall business score (0-100)")
    tier: str = Field(description="Score tier: 'A', 'B', 'C', 'D'")

    # Component scores (0-100 scale)
    price_efficiency_score: float = Field(description="Price relative to revenue/profit quality")
    revenue_quality_score: float = Field(description="Revenue stability and growth quality")
    moat_score: float = Field(description="Competitive moat and defensibility")
    ai_leverage_score: float = Field(description="AI/ML automation potential")
    operations_score: float = Field(description="Operational efficiency and scalability")
    risk_score: float = Field(description="Overall risk assessment")
    trust_score: float = Field(description="Trust in reported data quality")

    # Top factors (arrays for flexible content)
    top_buy_reasons: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Array of top reasons to pursue acquisition"
    )
    top_risks: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Array of top risks identified"
    )

    scoring_timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Indexes for scoring queries
    __table_args__ = (
        Index('ix_scoring_total_score', 'total_score'),
        Index('ix_scoring_tier_timestamp', 'tier', 'scoring_timestamp'),
        Index('ix_scoring_business_timestamp', 'business_id', 'scoring_timestamp'),
    )


class FollowUpQuestion(SQLModel, table=True):
    """
    Auto-generated follow-up questions and seller responses.

    Design choices:
    - Links questions to specific uncertainty triggers
    - Tracks response status and timestamps
    - Supports multiple questions per business
    - Append-only response history
    """
    __tablename__ = "follow_up_questions"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    business_id: str = Field(index=True, description="References business_id in raw_listings")
    canonical_record_id: str = Field(index=True, description="References id in canonical_business_records")

    question_text: str = Field(description="Generated question for seller")
    triggered_by_field: str = Field(description="Field/uncertainty that triggered this question")
    severity: str = Field(description="Question priority: 'critical', 'high', 'medium', 'low'")

    # Response tracking
    seller_response: Optional[str] = Field(description="Seller's response text")
    response_timestamp: Optional[datetime] = Field(description="When seller responded")
    response_status: str = Field(
        default="pending",
        description="'pending', 'responded', 'no_response', 'escalated'"
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Indexes for follow-up queries
    __table_args__ = (
        Index('ix_followup_business_status', 'business_id', 'response_status'),
        Index('ix_followup_severity_created', 'severity', 'created_at'),
    )


class AgentExecutionLog(SQLModel, table=True):
    """
    Lightweight audit log for agent executions.

    Design choices:
    - Tracks agent runs for debugging and optimization
    - Stores input snapshot for reproducibility
    - Success/failure status for monitoring
    - Minimal storage footprint (JSONB for flexible metadata)
    """
    __tablename__ = "agent_execution_logs"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    agent_name: str = Field(index=True, description="Name of agent: 'categorization', 'scoring', etc.")
    business_id: Optional[str] = Field(default=None, index=True, description="References business_id in raw_listings (null for sector-level research)")

    execution_id: str = Field(description="Unique ID for this agent execution")
    input_snapshot: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Snapshot of input data used by agent"
    )

    status: str = Field(description="'success', 'failure', 'partial', 'timeout'")
    error_message: Optional[str] = Field(description="Error details if failed")
    execution_metadata: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Additional execution details: duration, token usage, etc."
    )

    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(description="Completion timestamp")

    # Indexes for monitoring queries
    __table_args__ = (
        Index('ix_agent_exec_business_status', 'business_id', 'status'),
        Index('ix_agent_exec_name_started', 'agent_name', 'started_at'),
    )


# Pydantic models for API requests/responses (separate from database models)
class BusinessListingResponse(SQLModel):
    """Response model for business listings with latest data"""
    business_id: str
    marketplace: str
    listing_url: str
    latest_scrape: datetime
    canonical_data: Optional[dict]
    latest_score: Optional[dict]
    requires_followup: bool
    created_at: datetime


class ScoringRunResponse(SQLModel):
    """Response model for scoring runs"""
    scoring_run_id: str
    business_id: str
    total_score: float
    tier: str
    component_scores: dict
    top_buy_reasons: List[str]
    top_risks: List[str]
    scoring_timestamp: datetime
