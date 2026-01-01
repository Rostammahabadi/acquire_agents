"""
LangGraph workflow for converting raw scraped listing data into canonical structured business records.
This implements a single deterministic agent that extracts canonical data without scoring or evaluation.
"""

from typing import TypedDict, Optional, Dict, Any, List
from uuid import uuid4
import hashlib
import json
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field, ValidationError

from database import get_session_sync
from models import CanonicalBusinessRecord


# =============================================================================
# GRAPH STATE DEFINITION
# =============================================================================

class CategorizationState(TypedDict):
    """LangGraph state for the categorization workflow"""
    business_id: str
    raw_listing_id: str
    raw_text: str
    raw_html: str
    listing_metadata: Dict[str, Any]
    agent_run_id: str
    canonical_record: Optional[Dict[str, Any]]
    canonical_record_id: Optional[str]
    scoring_run_id: Optional[str]
    scoring_output: Optional[Dict[str, Any]]
    scoring_record: Optional[Dict[str, Any]]
    follow_up_questions: Optional[List[Dict[str, Any]]]


# =============================================================================
# CANONICAL SCHEMA DEFINITION
# =============================================================================

class FinancialsDomain(BaseModel):
    """Financial metrics and valuation data"""
    asking_price_usd: Optional[float] = Field(None, description="Asking price in USD")
    monthly_revenue_usd: Optional[float] = Field(None, description="Monthly recurring revenue in USD")
    annual_revenue_usd: Optional[float] = Field(None, description="Annual revenue in USD")
    monthly_profit_usd: Optional[float] = Field(None, description="Monthly profit in USD")
    annual_profit_usd: Optional[float] = Field(None, description="Annual profit in USD")
    profit_margin_percent: Optional[float] = Field(None, description="Profit margin as percentage")
    revenue_growth_rate_percent: Optional[float] = Field(None, description="Year-over-year revenue growth rate")


class ProductDomain(BaseModel):
    """Product and business model details"""
    business_type: Optional[str] = Field(None, description="Type of business (SaaS, e-commerce, etc.)")
    vertical: Optional[str] = Field(None, description="Industry vertical")
    product_category: Optional[str] = Field(None, description="Specific product category")
    features: Optional[list[str]] = Field(None, description="Key product features")
    target_market: Optional[str] = Field(None, description="Target customer segment")
    business_model: Optional[str] = Field(None, description="Revenue model (subscription, transaction, etc.)")


class CustomersDomain(BaseModel):
    """Customer metrics and segmentation"""
    total_customers: Optional[int] = Field(None, description="Total number of customers")
    monthly_active_users: Optional[int] = Field(None, description="Monthly active users")
    paying_customers: Optional[int] = Field(None, description="Number of paying customers")
    churn_rate_percent: Optional[float] = Field(None, description="Monthly churn rate as percentage")
    customer_concentration_risk: Optional[str] = Field(None, description="Assessment of customer concentration risk")
    customer_segments: Optional[list[str]] = Field(None, description="Customer segments served")


class OperationsDomain(BaseModel):
    """Operational details and requirements"""
    owner_hours_per_week: Optional[int] = Field(None, description="Hours per week owner spends on business")
    full_time_employees: Optional[int] = Field(None, description="Number of full-time employees")
    part_time_employees: Optional[int] = Field(None, description="Number of part-time employees")
    key_dependencies: Optional[list[str]] = Field(None, description="Critical operational dependencies")
    key_person_risk: Optional[str] = Field(None, description="Assessment of key person dependency risk")
    scalability_factors: Optional[list[str]] = Field(None, description="Factors limiting or enabling scalability")


class TechnologyDomain(BaseModel):
    """Technology stack and infrastructure"""
    tech_stack: Optional[list[str]] = Field(None, description="Primary technologies used")
    hosting_provider: Optional[str] = Field(None, description="Hosting/cloud provider")
    code_ownership: Optional[str] = Field(None, description="Code ownership status (owned, leased, etc.)")
    api_dependencies: Optional[list[str]] = Field(None, description="External API dependencies")
    data_storage: Optional[str] = Field(None, description="Primary data storage solution")
    development_status: Optional[str] = Field(None, description="Development/documentation status")


class GrowthDomain(BaseModel):
    """Growth metrics and strategies"""
    growth_channels: Optional[list[str]] = Field(None, description="Primary customer acquisition channels")
    monthly_growth_rate_percent: Optional[float] = Field(None, description="Monthly growth rate")
    marketing_spend_percent: Optional[float] = Field(None, description="Marketing spend as percentage of revenue")
    customer_acquisition_cost: Optional[float] = Field(None, description="Customer acquisition cost")
    lifetime_value: Optional[float] = Field(None, description="Customer lifetime value")
    growth_trends: Optional[str] = Field(None, description="Growth trend assessment")


class RisksDomain(BaseModel):
    """Risk assessment and mitigation factors"""
    platform_dependency_risk: Optional[str] = Field(None, description="Dependency on specific platforms")
    regulatory_risk: Optional[str] = Field(None, description="Regulatory or compliance risks")
    ip_risk: Optional[str] = Field(None, description="Intellectual property risks")
    competitive_risk: Optional[str] = Field(None, description="Competitive landscape risks")
    technical_debt: Optional[str] = Field(None, description="Technical debt assessment")
    market_risk: Optional[str] = Field(None, description="Market-related risks")


class SellerDomain(BaseModel):
    """Seller details and motivations"""
    location: Optional[str] = Field(None, description="Seller's location/country")
    selling_reason: Optional[str] = Field(None, description="Primary reason for selling")
    post_sale_involvement: Optional[str] = Field(None, description="Willingness to assist post-sale")
    transition_period: Optional[str] = Field(None, description="Available transition support period")
    seller_experience: Optional[str] = Field(None, description="Seller's experience level")
    business_age_years: Optional[float] = Field(None, description="Age of business in years")


class ConfidenceFlagsDomain(BaseModel):
    """Uncertainty indicators and data quality flags"""
    missing_financial_data: Optional[bool] = Field(None, description="Critical financial data is missing")
    assumed_values: Optional[list[str]] = Field(None, description="Fields where assumptions were made")
    contradictory_information: Optional[list[str]] = Field(None, description="Areas with contradictory data")
    requires_followup: Optional[list[str]] = Field(None, description="Topics requiring seller clarification")
    data_quality_score: Optional[int] = Field(None, description="Overall data quality score (1-10)")
    confidence_level: Optional[str] = Field(None, description="Overall confidence in extracted data")


class CanonicalRecord(BaseModel):
    """Complete canonical business record schema"""
    financials: Optional[FinancialsDomain] = Field(None)
    product: Optional[ProductDomain] = Field(None)
    customers: Optional[CustomersDomain] = Field(None)
    operations: Optional[OperationsDomain] = Field(None)
    technology: Optional[TechnologyDomain] = Field(None)
    growth: Optional[GrowthDomain] = Field(None)
    risks: Optional[RisksDomain] = Field(None)
    seller: Optional[SellerDomain] = Field(None)
    confidence_flags: Optional[ConfidenceFlagsDomain] = Field(None)


# =============================================================================
# SCORING SCHEMA DEFINITION
# =============================================================================

class ScoringComponents(BaseModel):
    """Component scores from LLM analysis (0-100 scale)"""
    price_efficiency_score: float = Field(..., ge=0, le=100, description="Price relative to revenue/profit quality")
    revenue_quality_score: float = Field(..., ge=0, le=100, description="Revenue stability and growth quality")
    moat_score: float = Field(..., ge=0, le=100, description="Competitive moat and defensibility")
    ai_leverage_score: float = Field(..., ge=0, le=100, description="AI/ML automation potential")
    operations_score: float = Field(..., ge=0, le=100, description="Operational efficiency and scalability")
    risk_score: float = Field(..., ge=0, le=100, description="Overall risk assessment")
    trust_score: float = Field(..., ge=0, le=100, description="Trust in reported data quality")


class ScoringOutput(BaseModel):
    """Complete scoring output from LLM"""
    component_scores: ScoringComponents
    top_buy_reasons: List[str] = Field(..., min_items=1, max_items=5, description="Top reasons to pursue acquisition")
    top_risks: List[str] = Field(..., min_items=1, max_items=5, description="Top risks identified")


# =============================================================================
# FOLLOW-UP QUESTION SCHEMA DEFINITION
# =============================================================================

class FollowUpQuestion(BaseModel):
    """Individual follow-up question with metadata"""
    question_text: str = Field(..., min_length=10, max_length=500, description="Generated question for seller")
    triggered_by_field: str = Field(..., min_length=1, max_length=100, description="Field/uncertainty that triggered this question")
    severity: str = Field(..., pattern="^(critical|high|medium|low)$", description="Question priority level")


class FollowUpQuestionsOutput(BaseModel):
    """Complete follow-up questions output from LLM"""
    questions: List[FollowUpQuestion] = Field(..., max_items=8, description="Generated follow-up questions")


# =============================================================================
# VERSIONING AND DATABASE LOGIC
# =============================================================================

def calculate_content_hash(raw_text: str, raw_html: str, listing_metadata: Dict[str, Any]) -> str:
    """Calculate SHA-256 hash of raw content for versioning"""
    content = {
        "raw_text": raw_text,
        "raw_html": raw_html,
        "listing_metadata": listing_metadata
    }
    content_str = json.dumps(content, sort_keys=True)
    return hashlib.sha256(content_str.encode()).hexdigest()


def get_latest_version(business_id: str, session) -> tuple[int, str]:
    """Get the latest version and content hash for a business_id"""
    result = session.query(
        CanonicalBusinessRecord.version,
        CanonicalBusinessRecord.content_hash
    ).filter(
        CanonicalBusinessRecord.business_id == business_id
    ).order_by(
        CanonicalBusinessRecord.version.desc()
    ).first()

    if result:
        return result.version, result.content_hash
    return 0, ""


def should_create_new_version(business_id: str, content_hash: str, session) -> tuple[bool, int]:
    """Determine if a new version should be created based on content hash"""
    latest_version, latest_hash = get_latest_version(business_id, session)

    # Create new version if content has changed
    if content_hash != latest_hash:
        return True, latest_version + 1

    return False, latest_version


def insert_canonical_record(
    business_id: str,
    agent_run_id: str,
    canonical_data: CanonicalRecord,
    content_hash: str,
    session
) -> str:
    """Insert a new canonical business record with proper versioning"""
    should_create, version = should_create_new_version(business_id, content_hash, session)

    if not should_create:
        # Return existing record ID if no changes
        existing = session.query(CanonicalBusinessRecord).filter(
            CanonicalBusinessRecord.business_id == business_id,
            CanonicalBusinessRecord.version == version
        ).first()
        return existing.id if existing else ""

    # Create new canonical record
    record = CanonicalBusinessRecord(
        business_id=business_id,
        version=version,
        agent_run_id=agent_run_id,
        content_hash=content_hash,
        financials=canonical_data.financials.dict() if canonical_data.financials else None,
        product=canonical_data.product.dict() if canonical_data.product else None,
        customers=canonical_data.customers.dict() if canonical_data.customers else None,
        operations=canonical_data.operations.dict() if canonical_data.operations else None,
        technology=canonical_data.technology.dict() if canonical_data.technology else None,
        growth=canonical_data.growth.dict() if canonical_data.growth else None,
        risks=canonical_data.risks.dict() if canonical_data.risks else None,
        seller=canonical_data.seller.dict() if canonical_data.seller else None,
        confidence_flags=canonical_data.confidence_flags.dict() if canonical_data.confidence_flags else None,
    )

    session.add(record)
    session.commit()
    session.refresh(record)

    return record.id


# =============================================================================
# SCORING LOGIC
# =============================================================================

def calculate_total_score(component_scores: ScoringComponents) -> float:
    """Calculate deterministic total score using weighted averages"""
    weights = {
        'price_efficiency_score': 0.20,
        'revenue_quality_score': 0.15,
        'moat_score': 0.20,
        'ai_leverage_score': 0.15,
        'operations_score': 0.10,
        'risk_score': 0.10,
        'trust_score': 0.10
    }

    total = 0.0
    for field_name, weight in weights.items():
        score_value = getattr(component_scores, field_name)
        total += score_value * weight

    return round(total, 2)


def determine_tier(total_score: float) -> str:
    """Determine tier based on total score"""
    if total_score >= 85:
        return 'A'
    elif total_score >= 70:
        return 'B'
    elif total_score >= 55:
        return 'C'
    else:
        return 'D'


def apply_data_quality_penalties(
    component_scores: ScoringComponents,
    confidence_flags: Optional[ConfidenceFlagsDomain]
) -> ScoringComponents:
    """Apply penalties for missing or ambiguous data"""
    penalties = {
        'price_efficiency_score': 0,
        'revenue_quality_score': 0,
        'moat_score': 0,
        'ai_leverage_score': 0,
        'operations_score': 0,
        'risk_score': 0,
        'trust_score': 0
    }

    # Apply penalties based on confidence flags
    if confidence_flags:
        if confidence_flags.missing_financial_data:
            penalties['price_efficiency_score'] = max(0, penalties['price_efficiency_score'] - 20)
            penalties['revenue_quality_score'] = max(0, penalties['revenue_quality_score'] - 15)
            penalties['trust_score'] = max(0, penalties['trust_score'] - 25)

        if confidence_flags.assumed_values:
            penalties['trust_score'] = max(0, penalties['trust_score'] - 10)

        if confidence_flags.requires_followup:
            penalties['trust_score'] = max(0, penalties['trust_score'] - 15)

        if confidence_flags.contradictory_information:
            penalties['trust_score'] = max(0, penalties['trust_score'] - 10)

    # Apply penalties to component scores
    updated_scores = {}
    for field_name in penalties:
        original_score = getattr(component_scores, field_name)
        penalty = penalties[field_name]
        updated_scores[field_name] = max(0, original_score + penalty)

    return ScoringComponents(**updated_scores)


def validate_scoring_output(scoring_output: ScoringOutput) -> bool:
    """Validate scoring output meets requirements"""
    # Ensure all component scores are present and in valid range
    for field_name in ScoringComponents.__fields__:
        score = getattr(scoring_output.component_scores, field_name)
        if not isinstance(score, (int, float)) or not (0 <= score <= 100):
            return False

    # Ensure we have buy reasons and risks
    if not scoring_output.top_buy_reasons or not scoring_output.top_risks:
        return False

    return True


def insert_scoring_record(
    business_id: str,
    canonical_record_id: str,
    scoring_run_id: str,
    scoring_output: ScoringOutput,
    session
) -> str:
    """Insert a new scoring record"""
    from models import ScoringRecord

    # Apply data quality penalties
    # Note: confidence_flags would need to be passed from canonical record
    # For now, we'll assume penalties are applied before this function

    # Calculate total score and tier
    total_score = calculate_total_score(scoring_output.component_scores)
    tier = determine_tier(total_score)

    # Create scoring record
    record = ScoringRecord(
        business_id=business_id,
        canonical_record_id=canonical_record_id,
        scoring_run_id=scoring_run_id,
        total_score=total_score,
        tier=tier,
        price_efficiency_score=scoring_output.component_scores.price_efficiency_score,
        revenue_quality_score=scoring_output.component_scores.revenue_quality_score,
        moat_score=scoring_output.component_scores.moat_score,
        ai_leverage_score=scoring_output.component_scores.ai_leverage_score,
        operations_score=scoring_output.component_scores.operations_score,
        risk_score=scoring_output.component_scores.risk_score,
        trust_score=scoring_output.component_scores.trust_score,
        top_buy_reasons=scoring_output.top_buy_reasons,
        top_risks=scoring_output.top_risks,
    )

    session.add(record)
    session.commit()
    session.refresh(record)

    return record.id


# =============================================================================
# FOLLOW-UP QUESTION LOGIC
# =============================================================================

def should_generate_follow_up_questions(scoring_output: Dict[str, Any]) -> bool:
    """Determine if follow-up questions should be generated based on gating criteria"""
    if not scoring_output:
        return False

    tier = scoring_output.get('tier')
    total_score = scoring_output.get('total_score')

    # Gating logic: tier ∈ ('A', 'B') AND total_score >= 70
    return tier in ('A', 'B') and total_score is not None and total_score >= 70


def analyze_uncertainty_sources(
    canonical_record: Dict[str, Any],
    confidence_flags: Optional[ConfidenceFlagsDomain]
) -> List[Dict[str, Any]]:
    """Analyze canonical record and confidence flags for uncertainty sources"""
    uncertainties = []

    # Check for missing/null canonical fields
    canonical_domains = ['financials', 'product', 'customers', 'operations', 'technology', 'growth', 'risks', 'seller']

    for domain in canonical_domains:
        if not canonical_record.get(domain):
            uncertainties.append({
                'field': f'{domain}.missing',
                'type': 'missing_domain',
                'severity': 'high' if domain in ['financials', 'customers', 'risks'] else 'medium'
            })

    # Check confidence flags for specific uncertainties
    if confidence_flags:
        if confidence_flags.missing_financial_data:
            uncertainties.append({
                'field': 'financials.missing_financial_data',
                'type': 'missing_financials',
                'severity': 'critical'
            })

        if confidence_flags.assumed_values:
            for assumption in (confidence_flags.assumed_values or []):
                uncertainties.append({
                    'field': f'assumptions.{assumption}',
                    'type': 'assumed_value',
                    'severity': 'high'
                })

        if confidence_flags.requires_followup:
            for followup_topic in (confidence_flags.requires_followup or []):
                uncertainties.append({
                    'field': f'followup.{followup_topic}',
                    'type': 'requires_followup',
                    'severity': 'high'
                })

        if confidence_flags.contradictory_information:
            for contradiction in (confidence_flags.contradictory_information or []):
                uncertainties.append({
                    'field': f'contradictory.{contradiction}',
                    'type': 'contradictory_data',
                    'severity': 'medium'
                })

    # Prioritize and deduplicate uncertainties
    seen_fields = set()
    prioritized_uncertainties = []

    # Sort by severity (critical > high > medium > low)
    severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    uncertainties.sort(key=lambda x: severity_order.get(x['severity'], 4))

    for uncertainty in uncertainties[:8]:  # Max 8 questions
        if uncertainty['field'] not in seen_fields:
            seen_fields.add(uncertainty['field'])
            prioritized_uncertainties.append(uncertainty)

    return prioritized_uncertainties


def generate_question_for_uncertainty(uncertainty: Dict[str, Any]) -> str:
    """Generate a specific question for a given uncertainty"""
    field = uncertainty['field']
    uncertainty_type = uncertainty['type']

    question_templates = {
        'financials.missing_financial_data': "Can you provide detailed financial statements for the past 12-24 months, including revenue, expenses, and profit/loss?",
        'financials.missing': "What are the current monthly/annual revenue figures and profit margins for this business?",
        'customers.missing': "Can you provide details about customer count, churn rate, and any large customer concentrations?",
        'risks.missing': "What are the main business risks or dependencies that could impact operations?",
        'operations.missing': "How many hours per week does the current owner spend on the business?",
        'technology.missing': "Do you own the code, data, and infrastructure, or are there any leased/cloud dependencies?",
        'assumed_value': "Regarding the {field} assumption, can you provide the actual details?",
        'requires_followup': "Can you clarify the uncertainty around {field}?",
        'ambiguous_data': "Can you provide more specific details about {field}?",
        'product.missing': "What is the core product offering and target market for this business?",
        'growth.missing': "What are the primary growth channels and recent growth trends?",
        'seller.missing': "What is the seller's motivation for selling and timeline for transition?"
    }

    # Try specific template first
    if field in question_templates:
        return question_templates[field]

    # Fallback to generic template based on type
    if uncertainty_type == 'missing_domain':
        return f"Can you provide details about the {field.replace('.missing', '')} aspects of the business?"

    return f"Can you clarify the uncertainty regarding {field}?"


def insert_follow_up_questions(
    business_id: str,
    canonical_record_id: str,
    questions: List[FollowUpQuestion],
    session
) -> List[str]:
    """Insert follow-up questions into database"""
    from models import FollowUpQuestion as DBFollowUpQuestion

    inserted_ids = []
    for question in questions:
        db_question = DBFollowUpQuestion(
            business_id=business_id,
            canonical_record_id=canonical_record_id,
            question_text=question.question_text,
            triggered_by_field=question.triggered_by_field,
            severity=question.severity
        )

        session.add(db_question)
        session.commit()
        session.refresh(db_question)
        inserted_ids.append(db_question.id)

    return inserted_ids


# =============================================================================
# LLM INTEGRATION AND PROMPTING
# =============================================================================

SYSTEM_PROMPT = """
You are a data extraction specialist. Your task is to extract structured business information from raw marketplace listings.

CRITICAL INSTRUCTIONS:
- Output ONLY valid JSON matching the exact schema provided
- NEVER make assumptions or fabricate data
- If information is missing, use null values
- If information is unclear, use null and flag in confidence_flags.requires_followup
- NEVER score, rank, or evaluate the business
- NEVER add commentary or explanations
- Extract data exactly as stated in the listing

SCHEMA: {schema}

Extract canonical business data from the following listing:
"""

SCORING_SYSTEM_PROMPT = """
You are a business valuation expert analyzing SaaS companies for acquisition.

CRITICAL INSTRUCTIONS:
- Output ONLY valid JSON matching the exact schema provided
- Evaluate each component score independently (0-100 scale)
- Penalize missing or ambiguous data explicitly in component scores
- Use conservative defaults when data quality is poor
- NEVER compute total_score or assign tier - these are calculated deterministically
- Focus on objective, data-driven analysis
- Consider market context and industry standards

COMPONENT SCORING GUIDELINES:

price_efficiency_score: Price relative to revenue/profit quality
- 90-100: Excellent value (<3x annual revenue)
- 70-89: Good value (3-5x annual revenue)
- 50-69: Fair value (5-8x annual revenue)
- 30-49: Expensive (8-12x annual revenue)
- 0-29: Overpriced (>12x annual revenue)

revenue_quality_score: Revenue stability and growth quality
- 90-100: Predictable, growing ARR with long-term contracts
- 70-89: Growing revenue with some predictability
- 50-69: Stable revenue but limited growth visibility
- 30-49: Volatile or declining revenue
- 0-29: High churn, unpredictable revenue

moat_score: Competitive moat and defensibility
- 90-100: Strong network effects, proprietary technology
- 70-89: Defensible position with switching costs
- 50-69: Some competitive advantages
- 30-49: Commodity business with low barriers
- 0-29: Highly competitive, easy to replicate

ai_leverage_score: AI/ML automation potential
- 90-100: High automation potential, data-rich processes
- 70-89: Moderate automation opportunities
- 50-69: Some automation possible
- 30-49: Limited automation potential
- 0-29: Manual processes, low automation potential

operations_score: Operational efficiency and scalability
- 90-100: Highly scalable, documented processes
- 70-89: Scalable with some process documentation
- 50-69: Scalable but needs process improvements
- 30-49: Limited scalability, owner-dependent
- 0-29: Not scalable, high owner dependency

risk_score: Overall risk assessment
- 90-100: Low risk, diversified revenue, strong contracts
- 70-89: Moderate risk with mitigation strategies
- 50-69: Some identifiable risks
- 30-49: High risk factors present
- 0-29: Very high risk, major red flags

trust_score: Trust in reported data quality
- 90-100: Verified financials, third-party audits
- 70-89: Detailed financials with supporting documentation
- 50-69: Basic financials provided
- 30-49: Limited financial transparency
- 0-29: Poor data quality, missing key metrics

SCHEMA: {schema}

Analyze the canonical business data and provide component scores:
"""

FOLLOWUP_SYSTEM_PROMPT = """
You are a due diligence expert generating targeted follow-up questions for SaaS business acquisitions.

CRITICAL INSTRUCTIONS:
- Output ONLY valid JSON matching the exact schema provided
- Generate questions that resolve decision-blocking uncertainty for acquisition
- Each question must be tied to exactly one missing or ambiguous field
- Questions must be answerable in 1-2 sentences
- Focus on acquisition risk, pricing, or contract terms
- Avoid generic diligence checklists or operational details
- Prefer fewer, high-signal questions over completeness
- Maximum 8 questions total

SEVERITY MAPPING:
- critical: IP ownership unclear, financials unverifiable, revenue ownership uncertain
- high: Churn unknown, customer concentration unknown, platform dependency unclear
- medium: Owner hours unclear, support burden unclear
- low: Minor operational or tooling details

QUESTION RULES:
- Tie each question to a specific uncertainty source
- Make questions concrete and actionable
- Focus on information gaps that would change buy/no-buy decision
- Avoid overlapping or duplicate questions

SCHEMA: {schema}

Generate targeted follow-up questions based on the identified uncertainties:
"""

def create_extraction_prompt() -> ChatPromptTemplate:
    """Create the LLM prompt for data extraction"""
    return ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", "Raw Text: {raw_text}\n\nHTML: {raw_html}\n\nMetadata: {metadata}")
    ])


def create_scoring_prompt() -> ChatPromptTemplate:
    """Create the LLM prompt for business scoring"""
    return ChatPromptTemplate.from_messages([
        ("system", SCORING_SYSTEM_PROMPT),
        ("user", "Canonical Business Data: {canonical_data}")
    ])


def create_followup_prompt() -> ChatPromptTemplate:
    """Create the LLM prompt for follow-up question generation"""
    return ChatPromptTemplate.from_messages([
        ("system", FOLLOWUP_SYSTEM_PROMPT),
        ("user", "Uncertainties: {uncertainties}\n\nCanonical Data: {canonical_data}")
    ])


# =============================================================================
# LANGGRAPH NODE IMPLEMENTATION
# =============================================================================

def categorize_listing(state: CategorizationState) -> CategorizationState:
    """
    LangGraph node that extracts canonical business data from raw listings.

    This node:
    - Uses LLM with structured output for data extraction
    - Validates output against canonical schema
    - Implements append-only versioning based on content hash
    - Never scores or evaluates the business
    """
    # Initialize LLM (assuming OpenAI GPT-4 for structured output)
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-5-mini", temperature=0)

    # Create extraction chain
    prompt = create_extraction_prompt()
    parser = JsonOutputParser(pydantic_object=CanonicalRecord)
    chain = prompt | llm | parser

    try:
        # Extract canonical data using LLM
        raw_result = chain.invoke({
            "raw_text": state["raw_text"],
            "raw_html": state["raw_html"],
            "metadata": json.dumps(state["listing_metadata"]),
            "schema": json.dumps(CanonicalRecord.model_json_schema())
        })

        # Validate with Pydantic model
        canonical_data = CanonicalRecord(**raw_result)

        # Calculate content hash for versioning
        content_hash = calculate_content_hash(
            state["raw_text"],
            state["raw_html"],
            state["listing_metadata"]
        )

        # Insert into database with versioning
        session = get_session_sync()
        try:
            record_id = insert_canonical_record(
                business_id=state["business_id"],
                agent_run_id=state["agent_run_id"],
                canonical_data=canonical_data,
                content_hash=content_hash,
                session=session
            )

            # Return updated state with canonical record
            return {
                **state,
                "canonical_record": {
                    "record_id": record_id,
                    "data": canonical_data.dict(),
                    "content_hash": content_hash,
                    "version": get_latest_version(state["business_id"], session)[0]
                }
            }

        finally:
            session.close()

    except ValidationError as e:
        # Log validation error and return state with error
        print(f"Schema validation failed: {e}")
        return {
            **state,
            "canonical_record": {
                "error": "schema_validation_failed",
                "details": str(e)
            }
        }
    except Exception as e:
        # Log general error and return state
        print(f"Categorization failed: {e}")
        return {
            **state,
            "canonical_record": {
                "error": "extraction_failed",
                "details": str(e)
            }
        }


# =============================================================================
# SCORING NODE IMPLEMENTATION
# =============================================================================

def score_business(state: CategorizationState) -> CategorizationState:
    """
    LangGraph node that scores businesses for acquisition potential.

    This node:
    - Loads canonical business record by ID
    - Uses LLM with structured output for component scoring
    - Applies deterministic total score calculation and tier mapping
    - Inserts immutable scoring record to database
    """
    if not state.get("canonical_record_id"):
        return {
            **state,
            "scoring_output": {
                "error": "no_canonical_record_id"
            }
        }

    # Load canonical record from database
    session = get_session_sync()
    try:
        from models import CanonicalBusinessRecord
        canonical_record = session.query(CanonicalBusinessRecord).filter(
            CanonicalBusinessRecord.id == state["canonical_record_id"]
        ).first()

        if not canonical_record:
            return {
                **state,
                "scoring_output": {
                    "error": "canonical_record_not_found"
                }
            }

        # Prepare canonical data for LLM
        canonical_data = {
            "financials": canonical_record.financials,
            "product": canonical_record.product,
            "customers": canonical_record.customers,
            "operations": canonical_record.operations,
            "technology": canonical_record.technology,
            "growth": canonical_record.growth,
            "risks": canonical_record.risks,
            "seller": canonical_record.seller,
            "confidence_flags": canonical_record.confidence_flags,
        }

        # Initialize LLM for scoring
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-5-mini", temperature=0)

        # Create scoring chain
        prompt = create_scoring_prompt()
        parser = JsonOutputParser(pydantic_object=ScoringOutput)
        chain = prompt | llm | parser

        # Get scoring output from LLM
        raw_result = chain.invoke({
            "canonical_data": json.dumps(canonical_data),
            "schema": json.dumps(ScoringOutput.model_json_schema())
        })

        print(f"DEBUG: Raw LLM result: {raw_result}")

        # Validate with Pydantic model
        try:
            scoring_output = ScoringOutput(**raw_result)
        except Exception as validation_error:
            print(f"DEBUG: Validation error: {validation_error}")
            print(f"DEBUG: Raw result type: {type(raw_result)}")
            raise validation_error

        # Apply data quality penalties
        confidence_flags = None
        if canonical_record.confidence_flags:
            confidence_flags = ConfidenceFlagsDomain(**canonical_record.confidence_flags)

        penalized_scores = apply_data_quality_penalties(
            scoring_output.component_scores,
            confidence_flags
        )

        # Update scoring output with penalized scores
        scoring_output.component_scores = penalized_scores

        # Validate final output
        if not validate_scoring_output(scoring_output):
            return {
                **state,
                "scoring_output": {
                    "error": "validation_failed",
                    "details": "Scoring output failed validation"
                }
            }

        # Calculate deterministic total score and tier
        total_score = calculate_total_score(scoring_output.component_scores)
        tier = determine_tier(total_score)

        # Insert scoring record
        scoring_run_id = state.get("scoring_run_id") or f"scoring-{uuid4()}"
        record_id = insert_scoring_record(
            business_id=state["business_id"],
            canonical_record_id=state["canonical_record_id"],
            scoring_run_id=scoring_run_id,
            scoring_output=scoring_output,
            session=session
        )

        # Return updated state with scoring results
        return {
            **state,
            "scoring_run_id": scoring_run_id,
            "scoring_output": {
                "record_id": record_id,
                "component_scores": scoring_output.component_scores.dict(),
                "top_buy_reasons": scoring_output.top_buy_reasons,
                "top_risks": scoring_output.top_risks,
                "total_score": total_score,
                "tier": tier
            }
        }

    except ValidationError as e:
        return {
            **state,
            "scoring_output": {
                "error": "schema_validation_failed",
                "details": str(e)
            }
        }
    except Exception as e:
        return {
            **state,
            "scoring_output": {
                "error": "scoring_failed",
                "details": str(e)
            }
        }
    finally:
        session.close()


# =============================================================================
# FOLLOW-UP QUESTION NODE IMPLEMENTATION
# =============================================================================

def generate_follow_up_questions(state: CategorizationState) -> CategorizationState:
    """
    LangGraph node that generates targeted follow-up questions for high-potential businesses.

    This node:
    - Checks gating criteria (tier A/B, score >= 70)
    - Analyzes canonical record and confidence flags for uncertainties
    - Generates minimal, high-signal questions via LLM
    - Inserts questions as immutable records to database
    """
    # Check gating criteria
    if not state.get("scoring_output") or not should_generate_follow_up_questions(state["scoring_output"]):
        return {
            **state,
            "follow_up_questions": []
        }

    # Validate required data
    if not state.get("canonical_record_id") or not state.get("canonical_record"):
        return {
            **state,
            "follow_up_questions": {
                "error": "missing_canonical_data"
            }
        }

    # Analyze uncertainties from canonical record
    confidence_flags = None
    if state["canonical_record"].get("confidence_flags"):
        confidence_flags = ConfidenceFlagsDomain(**state["canonical_record"]["confidence_flags"])

    uncertainties = analyze_uncertainty_sources(state["canonical_record"], confidence_flags)

    # If no significant uncertainties, skip question generation
    if not uncertainties:
        return {
            **state,
            "follow_up_questions": []
        }

    # Generate questions using LLM
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-5-mini", temperature=0)

        prompt = create_followup_prompt()
        parser = JsonOutputParser(pydantic_object=FollowUpQuestionsOutput)
        chain = prompt | llm | parser

        uncertainties_json = json.dumps(uncertainties)
        canonical_data_json = json.dumps(state["canonical_record"])

        raw_result = chain.invoke({
            "uncertainties": uncertainties_json,
            "canonical_data": canonical_data_json,
            "schema": json.dumps(FollowUpQuestionsOutput.model_json_schema())
        })

        # Validate with Pydantic model
        followup_output = FollowUpQuestionsOutput(**raw_result)

        # Insert questions into database
        session = get_session_sync()
        try:
            question_ids = insert_follow_up_questions(
                business_id=state["business_id"],
                canonical_record_id=state["canonical_record_id"],
                questions=followup_output.questions,
                session=session
            )

            # Return updated state with generated questions
            questions_data = []
            for i, question in enumerate(followup_output.questions):
                questions_data.append({
                    "id": question_ids[i],
                    "question_text": question.question_text,
                    "triggered_by_field": question.triggered_by_field,
                    "severity": question.severity
                })

            return {
                **state,
                "follow_up_questions": {
                    "questions": questions_data,
                    "count": len(questions_data)
                }
            }

        finally:
            session.close()

    except ValidationError as e:
        return {
            **state,
            "follow_up_questions": {
                "error": "schema_validation_failed",
                "details": str(e)
            }
        }
    except Exception as e:
        return {
            **state,
            "follow_up_questions": {
                "error": "followup_generation_failed",
                "details": str(e)
            }
        }


# =============================================================================
# LANGGRAPH DEFINITION
# =============================================================================

def create_categorization_graph() -> StateGraph:
    """
    Create the complete LangGraph for business categorization, scoring, and follow-up.

    This graph processes one raw listing at a time through the full acquisition pipeline:
    categorization → scoring → follow-up questions (conditional).
    """
    # Create graph builder
    builder = StateGraph(CategorizationState)

    # Add nodes
    builder.add_node("categorize_listing", categorize_listing)
    builder.add_node("score_business", score_business)
    builder.add_node("generate_follow_up_questions", generate_follow_up_questions)

    # Define the flow: START → categorize_listing → score_business → generate_follow_up_questions → END
    builder.add_edge(START, "categorize_listing")
    builder.add_edge("categorize_listing", "score_business")
    builder.add_edge("score_business", "generate_follow_up_questions")
    builder.add_edge("generate_follow_up_questions", END)

    # Compile the graph
    return builder.compile()


# =============================================================================
# STANDALONE FUNCTIONS FOR API ENDPOINTS
# =============================================================================

def run_standalone_scoring(business_id: str) -> dict:
    """
    Run scoring for a business that already has a canonical record.
    This function can be called directly from API endpoints without running the full graph.
    """
    # Get database session
    session = get_session_sync()
    try:
        from models import CanonicalBusinessRecord
        # Get the latest canonical record for this business
        canonical_record = session.query(CanonicalBusinessRecord).filter(
            CanonicalBusinessRecord.business_id == business_id
        ).order_by(CanonicalBusinessRecord.created_at.desc()).first()

        if not canonical_record:
            return {"error": "no_canonical_record_found"}

        # Prepare canonical data for LLM
        canonical_data = {
            "financials": canonical_record.financials,
            "product": canonical_record.product,
            "customers": canonical_record.customers,
            "operations": canonical_record.operations,
            "technology": canonical_record.technology,
            "growth": canonical_record.growth,
            "risks": canonical_record.risks,
            "seller": canonical_record.seller,
            "confidence_flags": canonical_record.confidence_flags,
        }

        # Initialize LLM for scoring
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-5-mini", temperature=0)

        # Create scoring chain
        prompt = create_scoring_prompt()
        parser = JsonOutputParser(pydantic_object=ScoringOutput)
        chain = prompt | llm | parser

        # Get scoring output from LLM
        raw_result = chain.invoke({
            "canonical_data": json.dumps(canonical_data),
            "schema": json.dumps(ScoringOutput.model_json_schema())
        })

        print(f"DEBUG: Raw LLM result: {raw_result}")

        # Validate with Pydantic model
        try:
            scoring_output = ScoringOutput(**raw_result)
        except Exception as validation_error:
            print(f"DEBUG: Validation error: {validation_error}")
            print(f"DEBUG: Raw result type: {type(raw_result)}")
            raise validation_error

        # Apply data quality penalties
        confidence_flags = None
        if canonical_record.confidence_flags:
            confidence_flags = ConfidenceFlagsDomain(**canonical_record.confidence_flags)

        penalized_scores = apply_data_quality_penalties(
            scoring_output.component_scores,
            confidence_flags
        )

        # Update scoring output with penalized scores
        scoring_output.component_scores = penalized_scores

        # Validate final output
        if not validate_scoring_output(scoring_output):
            return {
                "error": "validation_failed",
                "details": "Scoring output failed validation"
            }

        # Calculate deterministic total score and tier
        total_score = calculate_total_score(scoring_output.component_scores)
        tier = determine_tier(total_score)

        # Insert scoring record
        scoring_run_id = f"score-{uuid4()}"
        record_id = insert_scoring_record(
            business_id=business_id,
            canonical_record_id=str(canonical_record.id),
            scoring_run_id=scoring_run_id,
            scoring_output=scoring_output,
            session=session
        )

        return {
            "success": True,
            "record_id": record_id,
            "scoring_run_id": scoring_run_id,
            "component_scores": scoring_output.component_scores.dict(),
            "top_buy_reasons": scoring_output.top_buy_reasons,
            "top_risks": scoring_output.top_risks,
            "total_score": total_score,
            "tier": tier
        }

    except Exception as e:
        return {
            "error": "scoring_failed",
            "details": str(e)
        }
    finally:
        session.close()


def run_standalone_followup_generation(business_id: str) -> dict:
    """
    Generate follow-up questions for a business that has been scored.
    This function can be called directly from API endpoints.
    """
    # Get database session
    session = get_session_sync()
    try:
        from models import ScoringRecord, CanonicalBusinessRecord
        # Get the latest scoring record for this business
        scoring_record = session.query(ScoringRecord).filter(
            ScoringRecord.business_id == business_id
        ).order_by(ScoringRecord.scoring_timestamp.desc()).first()

        if not scoring_record:
            return {"error": "no_scoring_record_found"}

        # Check gating criteria (tier A/B, score >= 70)
        scoring_output = {
            "tier": scoring_record.tier,
            "total_score": scoring_record.total_score
        }
        if not should_generate_follow_up_questions(scoring_output):
            return {
                "error": "business_not_eligible_for_followups",
                "tier": scoring_record.tier,
                "score": scoring_record.total_score
            }

        # Get canonical record
        canonical_record = session.query(CanonicalBusinessRecord).filter(
            CanonicalBusinessRecord.id == scoring_record.canonical_record_id
        ).first()

        if not canonical_record:
            return {"error": "canonical_record_not_found"}

        # Prepare canonical data for analysis
        canonical_data = {
            "financials": canonical_record.financials,
            "product": canonical_record.product,
            "customers": canonical_record.customers,
            "operations": canonical_record.operations,
            "technology": canonical_record.technology,
            "growth": canonical_record.growth,
            "risks": canonical_record.risks,
            "seller": canonical_record.seller,
            "confidence_flags": canonical_record.confidence_flags,
        }

        # Analyze uncertainties
        confidence_flags = None
        if canonical_record.confidence_flags:
            confidence_flags = ConfidenceFlagsDomain(**canonical_record.confidence_flags)

        uncertainties = analyze_uncertainty_sources(canonical_data, confidence_flags)

        # If no significant uncertainties, skip
        if not uncertainties:
            return {
                "success": True,
                "followup_run_id": f"followup-{uuid4()}",
                "questions": [],
                "message": "No significant uncertainties found"
            }

        # Generate questions using LLM
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-5-mini", temperature=0)

        prompt = create_followup_prompt()
        parser = JsonOutputParser(pydantic_object=FollowUpQuestionsOutput)
        chain = prompt | llm | parser

        uncertainties_json = json.dumps(uncertainties)
        canonical_data_json = json.dumps(canonical_data)

        raw_result = chain.invoke({
            "uncertainties": uncertainties_json,
            "canonical_data": canonical_data_json,
            "schema": json.dumps(FollowUpQuestionsOutput.model_json_schema())
        })

        # Validate with Pydantic model
        followup_output = FollowUpQuestionsOutput(**raw_result)

        # Insert questions into database
        question_ids = insert_follow_up_questions(
            business_id=business_id,
            canonical_record_id=str(canonical_record.id),
            questions=followup_output.questions,
            session=session
        )

        # Prepare response data
        questions_data = []
        for i, question in enumerate(followup_output.questions):
            questions_data.append({
                "id": question_ids[i],
                "question_text": question.question_text,
                "triggered_by_field": question.triggered_by_field,
                "severity": question.severity
            })

        return {
            "success": True,
            "followup_run_id": f"followup-{uuid4()}",
            "questions": questions_data,
            "count": len(questions_data)
        }

    except Exception as e:
        return {
            "error": "followup_generation_failed",
            "details": str(e)
        }
    finally:
        session.close()


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

def process_listing_example():
    """
    Example of how to use the categorization and scoring graph for a single listing.
    """
    # Create the graph
    graph = create_categorization_graph()

    # Example input state
    initial_state: CategorizationState = {
        "business_id": str(uuid4()),
        "raw_listing_id": str(uuid4()),
        "raw_text": "SaaS business for sale. $500,000 asking price. $50k monthly revenue.",
        "raw_html": "<div>SaaS business for sale. <strong>$500,000</strong> asking price. <em>$50k</em> monthly revenue.</div>",
        "listing_metadata": {
            "marketplace": "acquire.com",
            "listing_url": "https://acquire.com/listing/123",
            "scrape_timestamp": datetime.utcnow().isoformat()
        },
        "agent_run_id": f"categorization-{uuid4()}",
        "canonical_record": None,
        "canonical_record_id": None,
        "scoring_run_id": None,
        "scoring_output": None,
        "scoring_record": None,
        "follow_up_questions": None
    }

    # Execute the graph
    result = graph.invoke(initial_state)

    # Result contains both canonical record and scoring output
    return result


if __name__ == "__main__":
    # Run example processing
    result = process_listing_example()
    print("Processing complete:")
    print("- Canonical record:", result.get("canonical_record"))
    print("- Scoring output:", result.get("scoring_output"))
    print("- Follow-up questions:", result.get("follow_up_questions"))
