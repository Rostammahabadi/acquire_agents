// Deal inbox queries

export interface DealInboxItem {
  business_id: string;
  marketplace: string;
  listing_url: string;
  asking_price_usd: number | null;
  ttm_revenue_usd: number | null;
  ttm_profit_usd: number | null;
  total_score: number;
  tier: string;
  sector_key: string | null;
}

export const getDealInbox = (): DealInboxItem[] => {
  // Single SQL query that joins latest records per business
  const query = `
    SELECT
      rl.business_id,
      rl.marketplace,
      rl.listing_url,
      cbr.financials->>'asking_price_usd' as asking_price_usd,
      cbr.financials->>'ttm_revenue_usd' as ttm_revenue_usd,
      cbr.financials->>'ttm_profit_usd' as ttm_profit_usd,
      sr.total_score,
      sr.tier,
      cbr.product->>'vertical' as sector_key
    FROM raw_listings rl
    -- Get latest scrape per business
    INNER JOIN (
      SELECT business_id, MAX(scrape_timestamp) as latest_scrape
      FROM raw_listings
      GROUP BY business_id
    ) latest_rl ON rl.business_id = latest_rl.business_id
                AND rl.scrape_timestamp = latest_rl.latest_scrape
    -- Get latest canonical record per business
    INNER JOIN (
      SELECT business_id, MAX(version) as latest_version
      FROM canonical_business_records
      GROUP BY business_id
    ) latest_cbr ON rl.business_id = latest_cbr.business_id
    INNER JOIN canonical_business_records cbr ON cbr.business_id = latest_cbr.business_id
                                               AND cbr.version = latest_cbr.latest_version
    -- Get latest scoring record per business
    INNER JOIN (
      SELECT business_id, MAX(scoring_timestamp) as latest_scoring
      FROM scoring_records
      GROUP BY business_id
    ) latest_sr ON rl.business_id = latest_sr.business_id
    INNER JOIN scoring_records sr ON sr.business_id = latest_sr.business_id
                                  AND sr.scoring_timestamp = latest_sr.latest_scoring
    ORDER BY sr.total_score DESC
  `;

  // TODO: Execute query and return results
  // This is a placeholder - actual database execution would go here
  return [];
};

export const updateDealStatus = () => {
  // TODO: Implement deal status update
};
