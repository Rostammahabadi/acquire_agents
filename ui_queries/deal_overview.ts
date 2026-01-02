// Deal overview queries

export interface CanonicalRecord {
  id: string;
  business_id: string;
  version: number;
  agent_run_id: string;
  content_hash: string;
  financials: any;
  product: any;
  customers: any;
  operations: any;
  technology: any;
  growth: any;
  risks: any;
  seller: any;
  confidence_flags: any;
  created_at: string;
}

export interface ScoringRecord {
  id: string;
  business_id: string;
  canonical_record_id: string;
  scoring_run_id: string;
  total_score: number;
  tier: string;
  price_efficiency_score: number;
  revenue_quality_score: number;
  moat_score: number;
  ai_leverage_score: number;
  operations_score: number;
  risk_score: number;
  trust_score: number;
  top_buy_reasons: any[];
  top_risks: any[];
  scoring_timestamp: string;
  created_at: string;
}

export interface FollowupSummary {
  severity: string;
  count: number;
}

export const getLatestCanonicalRecord = (business_id: string): CanonicalRecord | null => {
  const query = `
    SELECT
      id, business_id, version, agent_run_id, content_hash,
      financials, product, customers, operations, technology,
      growth, risks, seller, confidence_flags, created_at
    FROM canonical_business_records
    WHERE business_id = $1
    ORDER BY version DESC
    LIMIT 1
  `;

  // TODO: Execute query with business_id parameter
  // This is a placeholder - actual database execution would go here
  return null;
};

export const getLatestScore = (business_id: string): ScoringRecord | null => {
  const query = `
    SELECT
      id, business_id, canonical_record_id, scoring_run_id,
      total_score, tier, price_efficiency_score, revenue_quality_score,
      moat_score, ai_leverage_score, operations_score, risk_score,
      trust_score, top_buy_reasons, top_risks, scoring_timestamp, created_at
    FROM scoring_records
    WHERE business_id = $1
    ORDER BY scoring_timestamp DESC
    LIMIT 1
  `;

  // TODO: Execute query with business_id parameter
  // This is a placeholder - actual database execution would go here
  return null;
};

export const getFollowupSummary = (business_id: string): FollowupSummary[] => {
  const query = `
    SELECT
      severity,
      COUNT(*) as count
    FROM follow_up_questions
    WHERE business_id = $1
      AND response_status = 'pending'
    GROUP BY severity
    ORDER BY
      CASE severity
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
      END
  `;

  // TODO: Execute query with business_id parameter
  // This is a placeholder - actual database execution would go here
  return [];
};
