// Follow-ups queue queries

export interface PendingFollowup {
  business_id: string;
  question_text: string;
  severity: string;
  triggered_by_field: string;
  created_at: string;
  response_status: string;
}

export const getPendingFollowups = (): PendingFollowup[] => {
  const query = `
    SELECT
      business_id,
      question_text,
      severity,
      triggered_by_field,
      created_at,
      response_status
    FROM follow_up_questions
    WHERE response_status = 'pending'
    ORDER BY
      CASE severity
        WHEN 'critical' THEN 4
        WHEN 'high' THEN 3
        WHEN 'medium' THEN 2
        WHEN 'low' THEN 1
      END DESC,
      created_at ASC
  `;

  // TODO: Execute query
  // This is a placeholder - actual database execution would go here
  return [];
};
