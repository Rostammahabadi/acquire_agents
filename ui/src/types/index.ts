// Types for the acquisition pipeline UI

export interface BusinessListing {
  business_id: string;
  marketplace: string;
  listing_url: string;
  latest_scrape: string;
  asking_price?: number;
  latest_tier?: "A" | "B" | "C" | "D";
  latest_total_score?: number;
  pipeline_status: {
    scraped: boolean;
    canonicalized: boolean;
    scored: boolean;
    follow_up_generated: boolean;
    awaiting_response: boolean;
  };
  created_at: string;
}

export interface RawListing {
  business_id: string;
  marketplace: string;
  listing_url: string;
  scrape_timestamp: string;
  raw_text: string;
}

export interface CanonicalRecord {
  id: string;
  business_id: string;
  version: number;
  agent_run_id: string;
  created_at: string;
  financials?: {
    asking_price_usd?: number;
    monthly_revenue_usd?: number;
    annual_revenue_usd?: number;
    monthly_profit_usd?: number;
    annual_profit_usd?: number;
    profit_margin_percent?: number;
    revenue_growth_rate_percent?: number;
  };
  product?: {
    business_type?: string;
    vertical?: string;
    product_category?: string;
    features?: string[];
    target_market?: string;
    business_model?: string;
  };
  customers?: {
    total_customers?: number;
    monthly_active_users?: number;
    paying_customers?: number;
    churn_rate_percent?: number;
    customer_concentration_risk?: string;
    customer_segments?: string[];
  };
  operations?: {
    owner_hours_per_week?: number;
    full_time_employees?: number;
    part_time_employees?: number;
    key_dependencies?: string[];
    key_person_risk?: string;
    scalability_factors?: string[];
  };
  technology?: {
    tech_stack?: string[];
    hosting_provider?: string;
    code_ownership?: string;
    api_dependencies?: string[];
    data_storage?: string;
    development_status?: string;
  };
  growth?: {
    growth_channels?: string[];
    monthly_growth_rate_percent?: number;
    marketing_spend_percent?: number;
    customer_acquisition_cost?: number;
    lifetime_value?: number;
    growth_trends?: string;
  };
  risks?: {
    platform_dependency_risk?: string;
    regulatory_risk?: string;
    ip_risk?: string;
    competitive_risk?: string;
    technical_debt?: string;
    market_risk?: string;
  };
  seller?: {
    location?: string;
    selling_reason?: string;
    post_sale_involvement?: string;
    transition_period?: string;
    seller_experience?: string;
    business_age_years?: number;
  };
  confidence_flags?: {
    missing_financial_data?: boolean;
    assumed_values?: string[];
    contradictory_information?: string[];
    requires_followup?: string[];
    data_quality_score?: number;
    confidence_level?: string;
  };
}

export interface ScoringRecord {
  id: string;
  business_id: string;
  canonical_record_id: string;
  scoring_run_id: string;
  total_score: number;
  tier: "A" | "B" | "C" | "D";
  price_efficiency_score: number;
  revenue_quality_score: number;
  moat_score: number;
  ai_leverage_score: number;
  operations_score: number;
  risk_score: number;
  trust_score: number;
  top_buy_reasons: string[];
  top_risks: string[];
  scoring_timestamp: string;
  created_at: string;
}

export interface FollowUpQuestion {
  id: string;
  business_id: string;
  canonical_record_id: string;
  question_text: string;
  triggered_by_field: string;
  severity: "critical" | "high" | "medium" | "low";
  seller_response?: string;
  response_timestamp?: string;
  response_status: "pending" | "responded" | "no_response" | "escalated";
  created_at: string;
}

export interface BusinessDetail {
  business_id: string;
  raw_listing: RawListing;
  canonical_record?: CanonicalRecord;
  scoring_record?: ScoringRecord;
  follow_up_questions: FollowUpQuestion[];
  deep_research_results?: DeepResearchResults;
}

export interface SWOTAnalysis {
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  threats: string[];
}

export interface DeepResearchResults {
  swot: SWOTAnalysis;
  non_obvious_risks: string[];
  time_sensitive_opportunities: string[];
  sector_fit_verdict: "High" | "Medium" | "Low";
  justification: string;
}
