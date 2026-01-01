import psycopg2
import json

# Connect to database
conn = psycopg2.connect('postgresql://acquire_user:acquire_pass@localhost:5432/acquire_agents')
cursor = conn.cursor()

business_id = 'eea1dd2c-bf1b-4ab0-bb25-f47cc0df3f33'

print(f'=== VERIFICATION CHECK - Business ID: {business_id} ===\n')

# 1. Count of versions
cursor.execute('SELECT COUNT(*) FROM canonical_business_records WHERE business_id = %s', (business_id,))
version_count = cursor.fetchone()[0]
print(f'Total Canonical Versions: {version_count}')

# 2. Check if any new versions were created after our fix
cursor.execute('SELECT id, agent_run_id, created_at FROM canonical_business_records WHERE business_id = %s ORDER BY created_at DESC', (business_id,))
versions = cursor.fetchall()
print('Version Timeline:')
for version in versions:
    print(f'  {version[0][:8]}... | {version[1]} | {version[2]}')

# 3. Check scoring records
cursor.execute('SELECT COUNT(*) FROM scoring_records WHERE business_id = %s', (business_id,))
scoring_count = cursor.fetchone()[0]
print(f'Total Scoring Records: {scoring_count}')

# 4. Check follow-up questions
cursor.execute('SELECT COUNT(*) FROM follow_up_questions WHERE business_id = %s', (business_id,))
followup_count = cursor.fetchone()[0]
print(f'Total Follow-up Questions: {followup_count}')

# 5. Check if any operations created null data (our fix should prevent this)
cursor.execute('SELECT id, agent_run_id, financials FROM canonical_business_records WHERE business_id = %s AND financials IS NULL', (business_id,))
null_financials = cursor.fetchall()
if null_financials:
    print(f'WARNING: Found {len(null_financials)} canonical records with NULL financials (this indicates the duplication bug)')
    for record in null_financials:
        print(f'  NULL Record: {record[0][:8]}... | Agent: {record[1]}')
else:
    print('✓ No canonical records with NULL financials (good - duplication bug fixed)')

# 6. Verify the latest canonical record has proper data
cursor.execute('SELECT financials, confidence_flags FROM canonical_business_records WHERE business_id = %s ORDER BY created_at DESC LIMIT 1', (business_id,))
latest = cursor.fetchone()
if latest and latest[0]:
    financials = latest[0]
    print(f'Latest Financials: ${financials.get("asking_price_usd", "?")}, ${financials.get("monthly_revenue_usd", "?")}/month revenue')
    if latest[1] and latest[1].get('data_quality_score'):
        print(f'Data Quality Score: {latest[1]["data_quality_score"]}')
else:
    print('WARNING: Latest canonical record has no financials data')

cursor.close()
conn.close()
