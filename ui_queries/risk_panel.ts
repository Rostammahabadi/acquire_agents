// Risk panel queries

export interface CriticalFollowup {
  id: string;
  business_id: string;
  canonical_record_id: string;
  question_text: string;
  triggered_by_field: string;
  severity: string;
  response_status: string;
  created_at: string;
}

export const getCriticalFollowups = (
  business_id: string
): CriticalFollowup[] => {
  const query = `
    SELECT
      id, business_id, canonical_record_id, question_text,
      triggered_by_field, severity, response_status, created_at
    FROM follow_up_questions
    WHERE business_id = $1
      AND response_status = 'pending'
      AND severity IN ('critical', 'high')
    ORDER BY
      CASE severity
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
      END,
      created_at DESC
  `;

  // TODO: Execute query with business_id parameter
  // This is a placeholder - actual database execution would go here
  return [];
};

export const getSectorThreats = (sector_key: string): string[] => {
  const query = `
    SELECT
      agent_output->'swot'->'threats' as threats
    FROM sector_research_records
    WHERE sector_key = $1
      AND agent_type = 'synthesis'
    ORDER BY version DESC
    LIMIT 1
  `;

  // TODO: Execute query with sector_key parameter and extract threats array
  // This is a placeholder - actual database execution would go here
  return [];
};
