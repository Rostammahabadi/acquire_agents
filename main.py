"""
FastAPI server for the Acquire Agents platform.
Provides REST API endpoints for triggering LangGraph workflows.
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uuid
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# Ensure OpenAI API key is set
if not os.getenv("OPENAI_API_KEY"):
    print(f"Current directory: {os.getcwd()}")
    print(f"Env file exists: {os.path.exists('.env')}")
    raise ValueError("OPENAI_API_KEY environment variable is not set. Please check your .env file.")

print(f"OpenAI API key loaded: {os.getenv('OPENAI_API_KEY')[:20]}...")

# Import our LangGraph workflow functions
from categorization_workflow import (
    CategorizationState,
    categorize_listing,
    score_business,
    generate_follow_up_questions,
    create_categorization_graph
)
from database import get_session_sync
from models import RawListing

# Initialize FastAPI app
app = FastAPI(
    title="Acquire Agents API",
    description="AI-powered business acquisition platform",
    version="1.0.0"
)

# Add CORS middleware to allow requests from the UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # UI runs on port 3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic models for request/response
class AuthResponse(BaseModel):
    token: str
    token_type: str = "bearer"

class RunCanonicalizeRequest(BaseModel):
    business_id: str

class RunScoreRequest(BaseModel):
    business_id: str

class RunFollowUpRequest(BaseModel):
    business_id: str

class RunResponse(BaseModel):
    success: bool
    message: str
    business_id: str
    run_id: str

# Demo authentication - in production, implement proper JWT
@app.post("/int-agent-mvp/api/v1/auth/demo-token", response_model=AuthResponse)
async def get_demo_token():
    """Get a demo authentication token"""
    # Generate a simple demo token
    token = f"demo-{uuid.uuid4()}"
    return AuthResponse(token=token)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify the authentication token"""
    # For demo purposes, accept any token that starts with "demo-"
    if not credentials.credentials.startswith("demo-"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    return credentials.credentials

@app.post("/api/run/canonicalize", response_model=RunResponse)
async def run_canonicalize(
    request: RunCanonicalizeRequest,
    token: str = Depends(verify_token)
):
    """Trigger canonicalization workflow for a business"""
    try:
        # Get the raw listing data from database
        session = get_session_sync()
        try:
            raw_listing = session.query(RawListing).filter(
                RawListing.business_id == request.business_id
            ).order_by(RawListing.scrape_timestamp.desc()).first()

            if not raw_listing:
                raise HTTPException(status_code=404, detail="Business not found")

            # Create initial state for LangGraph
            initial_state: CategorizationState = {
                "business_id": str(raw_listing.business_id),
                "raw_listing_id": str(raw_listing.id),
                "raw_text": raw_listing.raw_text or "",
                "raw_html": raw_listing.raw_html or "",
                "listing_metadata": {
                    "marketplace": raw_listing.marketplace,
                    "listing_url": raw_listing.listing_url,
                    "scrape_timestamp": raw_listing.scrape_timestamp.isoformat(),
                    "asking_price_raw": raw_listing.asking_price_raw,
                    "revenue_raw": raw_listing.revenue_raw,
                    "profit_raw": raw_listing.profit_raw,
                },
                "agent_run_id": f"canonicalize-{uuid.uuid4()}",
                "canonical_record": None,
                "canonical_record_id": None,
                "scoring_run_id": None,
                "scoring_output": None,
                "follow_up_questions": None
            }

            # Run the canonicalization workflow
            graph = create_categorization_graph()
            # Set the API key in environment for the workflow
            os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
            result = graph.invoke(initial_state)

            # Check if canonicalization was successful
            if result.get("canonical_record", {}).get("error"):
                raise HTTPException(
                    status_code=500,
                    detail=f"Canonicalization failed: {result['canonical_record']['error']}"
                )

            run_id = result["agent_run_id"]
            return RunResponse(
                success=True,
                message="Canonicalization completed successfully",
                business_id=request.business_id,
                run_id=run_id
            )

        finally:
            session.close()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Canonicalization failed: {str(e)}")

@app.post("/api/run/score", response_model=RunResponse)
async def run_score(
    request: RunScoreRequest,
    token: str = Depends(verify_token)
):
    """Trigger scoring workflow for a business"""
    try:
        # Check if canonical record exists
        session = get_session_sync()
        try:
            from models import CanonicalBusinessRecord
            canonical_record = session.query(CanonicalBusinessRecord).filter(
                CanonicalBusinessRecord.business_id == request.business_id
            ).order_by(CanonicalBusinessRecord.created_at.desc()).first()

            if not canonical_record:
                raise HTTPException(
                    status_code=400,
                    detail="No canonical record found. Run canonicalization first."
                )

        finally:
            session.close()

        # Set the API key in environment for the workflow
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

        # Run standalone scoring function
        result = run_standalone_scoring(request.business_id)

        # Check if scoring was successful
        if result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=f"Scoring failed: {result['error']}"
            )

        return RunResponse(
            success=True,
            message="Scoring completed successfully",
            business_id=request.business_id,
            run_id=result["scoring_run_id"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")

@app.post("/api/run/follow-ups", response_model=RunResponse)
async def run_follow_ups(
    request: RunFollowUpRequest,
    token: str = Depends(verify_token)
):
    """Trigger follow-up question generation for a business"""
    try:
        # Check if scoring record exists and business is eligible
        session = get_session_sync()
        try:
            from models import ScoringRecord
            scoring_record = session.query(ScoringRecord).filter(
                ScoringRecord.business_id == request.business_id
            ).order_by(ScoringRecord.scoring_timestamp.desc()).first()

            if not scoring_record:
                raise HTTPException(
                    status_code=400,
                    detail="No scoring record found. Run scoring first."
                )

            # Check if business qualifies for follow-up questions (tier A/B, score >= 70)
            if scoring_record.tier not in ['A', 'B'] or scoring_record.total_score < 70:
                raise HTTPException(
                    status_code=400,
                    detail=f"Business does not qualify for follow-up questions (tier: {scoring_record.tier}, score: {scoring_record.total_score}). Must be tier A/B with score >= 70."
                )

        finally:
            session.close()

        # Set the API key in environment for the workflow
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

        # Run standalone follow-up generation function
        result = run_standalone_followup_generation(request.business_id)

        # Check if follow-up generation was successful
        if result.get("error"):
            if result["error"] == "business_not_eligible_for_followups":
                raise HTTPException(
                    status_code=400,
                    detail=f"Business does not qualify for follow-up questions (tier: {result.get('tier', 'unknown')}, score: {result.get('score', 'unknown')}). Must be tier A/B with score >= 70."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Follow-up generation failed: {result['error']}"
                )

        return RunResponse(
            success=True,
            message="Follow-up questions generated successfully",
            business_id=request.business_id,
            run_id=result["followup_run_id"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Follow-up generation failed: {str(e)}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Acquire Agents API is running", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
