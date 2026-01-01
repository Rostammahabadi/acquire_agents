#!/usr/bin/env python3
"""
Database initialization script
Run this to create all tables and optionally add some sample data
"""

from database import create_db_and_tables, get_session_sync
from models import (
    RawListing, CanonicalBusinessRecord, ScoringRecord,
    FollowUpQuestion, AgentExecutionLog
)
from datetime import datetime
from uuid import uuid4

def init_database():
    """Initialize the database with tables"""
    print("Creating database tables...")
    create_db_and_tables()
    print("Database tables created successfully!")

def add_sample_data():
    """Add some sample data for testing the acquisition system"""
    session = get_session_sync()

    try:
        # Create sample raw listing
        business_id = uuid4()
        raw_listing = RawListing(
            business_id=business_id,
            marketplace="acquire.com",
            listing_url="https://acquire.com/business/sample-saas-001",
            scrape_timestamp=datetime.utcnow(),
            raw_html="<html><body><h1>Sample SaaS Business</h1><p>Asking Price: $500,000</p></body></html>",
            raw_text="Sample SaaS Business - Asking Price: $500,000 - Monthly Revenue: $50,000",
            listing_category="SaaS",
            seller_country="United States",
            asking_price_raw="$500,000",
            revenue_raw="$50,000/month",
            profit_raw="$25,000/month"
        )
        session.add(raw_listing)
        session.commit()
        session.refresh(raw_listing)

        # Create sample canonical business record
        canonical_record = CanonicalBusinessRecord(
            business_id=business_id,
            version=1,
            agent_run_id="categorization-run-001",
            financials={
                "asking_price_usd": 500000,
                "monthly_revenue_usd": 50000,
                "monthly_profit_usd": 25000,
                "revenue_model": "subscription",
                "seller_add_backs_present": False,
                "financials_verified": False
            },
            product={
                "product_type": "SaaS",
                "primary_use_case": "Project Management",
                "vertical": "Technology",
                "b2b_or_b2c": "B2B",
                "core_features": ["Task Management", "Team Collaboration", "Reporting"]
            },
            customers={
                "customer_count_estimate": 500,
                "customer_type": "SMEs",
                "customer_concentration_risk": "medium",
                "churn_disclosed": True,
                "churn_rate_percent": 5.2
            },
            operations={
                "owner_hours_per_week": 10,
                "support_required": "minimal",
                "dependencies": ["AWS", "Stripe"],
                "key_person_risk": "low"
            },
            technology={
                "tech_stack": ["React", "Node.js", "PostgreSQL"],
                "hosting_provider": "AWS",
                "code_ownership_confirmed": True,
                "third_party_api_dependency": ["Stripe", "SendGrid"]
            },
            growth={
                "acquisition_channels": ["Content Marketing", "SEO", "Partnerships"],
                "recent_growth_trend": "stable",
                "marketing_spend_disclosed": True
            },
            risks={
                "platform_dependency": ["Stripe"],
                "regulatory_risk": "low",
                "ip_risk": "medium"
            },
            seller={
                "seller_location": "San Francisco, CA",
                "reason_for_selling": "Retirement",
                "seller_involvement_post_sale": "3 months transition"
            },
            confidence_flags={
                "missing_financials": False,
                "ambiguous_metrics": [],
                "assumptions_made": ["Growth trend based on limited data"],
                "requires_follow_up": True
            }
        )
        session.add(canonical_record)
        session.commit()
        session.refresh(canonical_record)

        # Create sample scoring record
        scoring_record = ScoringRecord(
            business_id=business_id,
            canonical_record_id=canonical_record.id,
            scoring_run_id="scoring-run-001",
            total_score=78.5,
            tier="B",
            price_efficiency_score=75.0,
            revenue_quality_score=82.0,
            moat_score=70.0,
            ai_leverage_score=85.0,
            operations_score=80.0,
            risk_score=65.0,
            trust_score=90.0,
            top_buy_reasons=["Strong recurring revenue", "Low owner dependency", "Growing market"],
            top_risks=["Platform dependency on Stripe", "Limited historical data"]
        )
        session.add(scoring_record)
        session.commit()

        # Create sample follow-up question
        followup_question = FollowUpQuestion(
            business_id=business_id,
            canonical_record_id=canonical_record.id,
            question_text="Can you provide the last 12 months of detailed financial statements?",
            triggered_by_field="financials_verified",
            severity="high",
            response_status="pending"
        )
        session.add(followup_question)
        session.commit()

        # Create sample agent execution log
        agent_log = AgentExecutionLog(
            agent_name="categorization",
            business_id=business_id,
            execution_id="exec-001",
            input_snapshot={"marketplace": "acquire.com", "raw_text_length": 150},
            status="success",
            execution_metadata={"processing_time_seconds": 45, "tokens_used": 1250}
        )
        session.add(agent_log)
        session.commit()

        print("Sample acquisition system data added successfully!")

    except Exception as e:
        session.rollback()
        print(f"Error adding sample data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    init_database()

    # Uncomment the line below to add sample data
    # add_sample_data()
