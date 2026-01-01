import { Pool } from "pg";

// Database configuration - should match the Python backend
const DATABASE_URL =
  process.env.DATABASE_URL ||
  "postgresql://acquire_user:acquire_pass@localhost:5432/acquire_agents";

// Create a connection pool
const pool = new Pool({
  connectionString: DATABASE_URL,
  ssl:
    process.env.NODE_ENV === "production"
      ? { rejectUnauthorized: false }
      : false,
});

export interface RawListingRow {
  id: string;
  business_id: string;
  marketplace: string;
  listing_url: string;
  scrape_timestamp: string;
  raw_html?: string;
  raw_text?: string;
  listing_category?: string;
  seller_country?: string;
  asking_price_raw?: string;
  revenue_raw?: string;
  profit_raw?: string;
  created_at: string;
}

export interface CanonicalRecordRow {
  id: string;
  business_id: string;
  version: number;
  agent_run_id: string;
  // content_hash is missing from database but exists in schema
  financials?: any;
  product?: any;
  customers?: any;
  operations?: any;
  technology?: any;
  growth?: any;
  risks?: any;
  seller?: any;
  confidence_flags?: any;
  created_at: string;
}

export interface ScoringRecordRow {
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
  top_buy_reasons?: any;
  top_risks?: any;
  scoring_timestamp: string;
  created_at: string;
}

export interface FollowUpQuestionRow {
  id: string;
  business_id: string;
  canonical_record_id: string;
  question_text: string;
  triggered_by_field: string;
  severity: string;
  seller_response?: string;
  response_timestamp?: string;
  response_status: string;
  created_at: string;
}

export async function getBusinesses() {
  const client = await pool.connect();
  try {
    // Get all unique business IDs from raw listings, ordered by latest scrape
    const businessIdsQuery = `
      SELECT business_id::text as business_id, MAX(scrape_timestamp) as latest_scrape
      FROM raw_listings
      GROUP BY business_id
      ORDER BY latest_scrape DESC
    `;

    const businessIdsResult = await client.query(businessIdsQuery);
    const businesses = [];

    // For each business, get the latest data
    for (const { business_id } of businessIdsResult.rows) {
      // Get latest raw listing
      const rawQuery = `
        SELECT marketplace, listing_url, scrape_timestamp, asking_price_raw
        FROM raw_listings
        WHERE business_id::text = $1
        ORDER BY scrape_timestamp DESC
        LIMIT 1
      `;
      const rawResult = await client.query(rawQuery, [business_id]);
      const rawData = rawResult.rows[0];

      // Check if canonicalized
      const canonicalQuery = `SELECT COUNT(*)::int > 0 as canonicalized FROM canonical_business_records WHERE business_id::text = $1`;
      const canonicalResult = await client.query(canonicalQuery, [business_id]);
      const canonicalized = canonicalResult.rows[0].canonicalized;

      // Check if scored and get latest score
      const scoringCountQuery = `SELECT COUNT(*)::int as count FROM scoring_records WHERE business_id::text = $1`;
      const scoringCountResult = await client.query(scoringCountQuery, [
        business_id,
      ]);
      const scoringCount = scoringCountResult.rows[0].count;

      let scoringData = null;
      if (scoringCount > 0) {
        const scoringQuery = `
          SELECT total_score, tier
          FROM scoring_records
          WHERE business_id::text = $1
          ORDER BY scoring_timestamp DESC
          LIMIT 1
        `;
        const scoringResult = await client.query(scoringQuery, [business_id]);
        scoringData = {
          total_score: scoringResult.rows[0].total_score,
          tier: scoringResult.rows[0].tier,
          scored: true,
        };
      } else {
        scoringData = { scored: false };
      }

      // Check follow-up status
      const followupCountQuery = `SELECT COUNT(*)::int as total FROM follow_up_questions WHERE business_id::text = $1`;
      const followupCountResult = await client.query(followupCountQuery, [
        business_id,
      ]);
      const totalQuestions = followupCountResult.rows[0].total;

      const pendingCountQuery = `SELECT COUNT(*)::int as pending FROM follow_up_questions WHERE business_id::text = $1 AND response_status = 'pending'`;
      const pendingCountResult = await client.query(pendingCountQuery, [
        business_id,
      ]);
      const pendingQuestions = pendingCountResult.rows[0].pending;

      const followupData = {
        follow_up_generated: totalQuestions > 0,
        awaiting_response: pendingQuestions > 0,
      };

      businesses.push({
        business_id,
        marketplace: rawData.marketplace,
        listing_url: rawData.listing_url,
        latest_scrape: rawData.scrape_timestamp,
        asking_price: rawData.asking_price_raw
          ? parseInt(rawData.asking_price_raw.replace(/[$,]/g, ""))
          : undefined,
        latest_tier: scoringData?.tier,
        latest_total_score: scoringData?.total_score
          ? parseFloat(scoringData.total_score)
          : undefined,
        pipeline_status: {
          scraped: true,
          canonicalized,
          scored: scoringData?.scored || false,
          follow_up_generated: followupData?.follow_up_generated || false,
          awaiting_response: followupData?.awaiting_response || false,
        },
        created_at: rawData.scrape_timestamp,
      });
    }

    return businesses;
  } finally {
    client.release();
  }
}

export async function getBusinessDetail(businessId: string) {
  const client = await pool.connect();
  try {
    // Get raw listing
    const rawQuery = `
      SELECT * FROM raw_listings
      WHERE business_id::text = $1
      ORDER BY scrape_timestamp DESC
      LIMIT 1
    `;
    const rawResult = await client.query(rawQuery, [businessId]);
    const rawListing = rawResult.rows[0];

    if (!rawListing) {
      throw new Error("Business not found");
    }

    // Get canonical record
    const canonicalQuery = `
      SELECT * FROM canonical_business_records
      WHERE business_id::text = $1
      ORDER BY created_at DESC
      LIMIT 1
    `;
    const canonicalResult = await client.query(canonicalQuery, [businessId]);
    const canonicalRecord = canonicalResult.rows[0];

    // Get scoring record
    const scoringQuery = `
      SELECT * FROM scoring_records
      WHERE business_id::text = $1
      ORDER BY scoring_timestamp DESC
      LIMIT 1
    `;
    const scoringResult = await client.query(scoringQuery, [businessId]);
    const scoringRecord = scoringResult.rows[0];

    // Get follow-up questions
    const followupQuery = `
      SELECT * FROM follow_up_questions
      WHERE business_id::text = $1
      ORDER BY created_at ASC
    `;
    const followupResult = await client.query(followupQuery, [businessId]);
    const followUpQuestions = followupResult.rows;

    return {
      business_id: businessId,
      raw_listing: {
        business_id: rawListing.business_id,
        marketplace: rawListing.marketplace,
        listing_url: rawListing.listing_url,
        scrape_timestamp: rawListing.scrape_timestamp.toISOString(),
        raw_text: rawListing.raw_text || "",
      },
      canonical_record: canonicalRecord
        ? {
            id: canonicalRecord.id,
            business_id: canonicalRecord.business_id,
            version: canonicalRecord.version,
            agent_run_id: canonicalRecord.agent_run_id,
            created_at: canonicalRecord.created_at.toISOString(),
            financials: canonicalRecord.financials,
            product: canonicalRecord.product,
            customers: canonicalRecord.customers,
            operations: canonicalRecord.operations,
            technology: canonicalRecord.technology,
            growth: canonicalRecord.growth,
            risks: canonicalRecord.risks,
            seller: canonicalRecord.seller,
            confidence_flags: canonicalRecord.confidence_flags,
          }
        : undefined,
      scoring_record: scoringRecord
        ? {
            id: scoringRecord.id,
            business_id: scoringRecord.business_id,
            canonical_record_id: scoringRecord.canonical_record_id,
            scoring_run_id: scoringRecord.scoring_run_id,
            total_score: parseFloat(scoringRecord.total_score),
            tier: scoringRecord.tier,
            price_efficiency_score: parseFloat(
              scoringRecord.price_efficiency_score
            ),
            revenue_quality_score: parseFloat(
              scoringRecord.revenue_quality_score
            ),
            moat_score: parseFloat(scoringRecord.moat_score),
            ai_leverage_score: parseFloat(scoringRecord.ai_leverage_score),
            operations_score: parseFloat(scoringRecord.operations_score),
            risk_score: parseFloat(scoringRecord.risk_score),
            trust_score: parseFloat(scoringRecord.trust_score),
            top_buy_reasons: scoringRecord.top_buy_reasons,
            top_risks: scoringRecord.top_risks,
            scoring_timestamp: scoringRecord.scoring_timestamp.toISOString(),
            created_at: scoringRecord.created_at.toISOString(),
          }
        : undefined,
      follow_up_questions: followUpQuestions.map((q) => ({
        id: q.id,
        business_id: q.business_id,
        canonical_record_id: q.canonical_record_id,
        question_text: q.question_text,
        triggered_by_field: q.triggered_by_field,
        severity: q.severity,
        seller_response: q.seller_response,
        response_timestamp: q.response_timestamp?.toISOString(),
        response_status: q.response_status,
        created_at: q.created_at.toISOString(),
      })),
    };
  } finally {
    client.release();
  }
}

export async function triggerCanonicalization(businessId: string) {
  try {
    // Get auth token from backend
    const authResponse = await fetch(
      "http://localhost:8000/int-agent-mvp/api/v1/auth/demo-token",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    if (!authResponse.ok) {
      throw new Error("Failed to get auth token");
    }

    const { token } = await authResponse.json();

    // Trigger canonicalization with auth token
    const triggerResponse = await fetch(
      "http://localhost:8000/api/run/canonicalize",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ business_id: businessId }),
      }
    );

    if (!triggerResponse.ok) {
      const error = await triggerResponse.text();
      throw new Error(`Canonicalization failed: ${error}`);
    }

    const result = await triggerResponse.json();
    return {
      success: true,
      message: "Canonicalization triggered successfully",
      business_id: businessId,
      run_id: result.run_id || `canonicalize-${Date.now()}`,
    };
  } catch (error) {
    console.error("Error triggering canonicalization:", error);
    return {
      success: false,
      message: `Failed to trigger canonicalization: ${
        error instanceof Error ? error.message : "Unknown error"
      }`,
      business_id: businessId,
    };
  }
}

export async function triggerScoring(businessId: string) {
  try {
    // Get auth token from backend
    const authResponse = await fetch(
      "http://localhost:8000/int-agent-mvp/api/v1/auth/demo-token",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    if (!authResponse.ok) {
      throw new Error("Failed to get auth token");
    }

    const { token } = await authResponse.json();

    // Trigger scoring with auth token
    const triggerResponse = await fetch("http://localhost:8000/api/run/score", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ business_id: businessId }),
    });

    if (!triggerResponse.ok) {
      const error = await triggerResponse.text();
      throw new Error(`Scoring failed: ${error}`);
    }

    const result = await triggerResponse.json();
    return {
      success: true,
      message: "Scoring triggered successfully",
      business_id: businessId,
      run_id: result.run_id || `score-${Date.now()}`,
    };
  } catch (error) {
    console.error("Error triggering scoring:", error);
    return {
      success: false,
      message: `Failed to trigger scoring: ${
        error instanceof Error ? error.message : "Unknown error"
      }`,
      business_id: businessId,
    };
  }
}

export async function triggerFollowUpGeneration(businessId: string) {
  try {
    // Get auth token from backend
    const authResponse = await fetch(
      "http://localhost:8000/int-agent-mvp/api/v1/auth/demo-token",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    if (!authResponse.ok) {
      throw new Error("Failed to get auth token");
    }

    const { token } = await authResponse.json();

    // Trigger follow-up generation with auth token
    const triggerResponse = await fetch(
      "http://localhost:8000/api/run/follow-ups",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ business_id: businessId }),
      }
    );

    if (!triggerResponse.ok) {
      const error = await triggerResponse.text();
      throw new Error(`Follow-up generation failed: ${error}`);
    }

    const result = await triggerResponse.json();
    return {
      success: true,
      message: "Follow-up generation triggered successfully",
      business_id: businessId,
      run_id: result.run_id || `followups-${Date.now()}`,
    };
  } catch (error) {
    console.error("Error triggering follow-up generation:", error);
    return {
      success: false,
      message: `Failed to trigger follow-up generation: ${
        error instanceof Error ? error.message : "Unknown error"
      }`,
      business_id: businessId,
    };
  }
}

export async function saveFollowUpResponse(
  questionId: string,
  response: string
) {
  const client = await pool.connect();
  try {
    const query = `
      UPDATE follow_up_questions
      SET
        seller_response = $1,
        response_timestamp = NOW(),
        response_status = 'responded'
      WHERE id::text = $2
      RETURNING *
    `;
    const result = await client.query(query, [response, questionId]);

    if (result.rows.length === 0) {
      throw new Error("Question not found");
    }

    return {
      success: true,
      message: "Response saved successfully",
      question_id: questionId,
      response_timestamp: new Date().toISOString(),
    };
  } finally {
    client.release();
  }
}
