import json
from typing import Any, Dict
import os
from dotenv import load_dotenv
from openai import OpenAI
from deep_research.state import DeepResearchState
from deep_research.db import persist_sector_research_record
from utils import log_agent_execution

# Load environment variables
load_dotenv()


def competition_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    Competitive landscape analysis node.

    Analyzes dominant players, independent success cases,
    differentiation patterns, and competition intensity in the sector.
    """
    sector_description = state["sector_description"]

    with log_agent_execution(
        agent_name="competition",
        business_id=state.get("business_id"),
        input_snapshot={
            "sector_description": sector_description,
            "sector_key": state.get("sector_key"),
            "research_run_id": state.get("research_run_id")
        }
    ) as logger:
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Create prompt for competition analysis
        prompt = f"""You are a competitive landscape analysis agent.

Your role:
- Assess competitive intensity and structure
- Identify dominant players and successful independents
- Determine how winners differentiate

Rules:
- Avoid exhaustive competitor lists
- Ignore vanity metrics and marketing claims
- Do not provide strategic recommendations
- Focus on observable patterns only
- Respond ONLY in valid JSON matching the required schema

Analyze the competitive landscape for the following sector: {sector_description}

Focus on factual competitive dynamics:
- Dominant players with significant market share
- Independent businesses that have achieved success
- Key differentiation patterns that drive competitive advantage
- Competition intensity and market concentration

Output ONLY valid JSON with exactly these keys:
- dominant_players: List of dominant players with significant market share
- independent_success_cases: Documented cases of independent businesses succeeding
- winner_differentiation: Key patterns of differentiation among winners
- competition_intensity: Assessment of competition intensity (Low/Medium/High)
- sources: Key data sources or references used in analysis

Avoid vanity competitor lists and marketing language. Focus on factual competitive dynamics."""

        # Get response from OpenAI responses API
        response = client.responses.create(
            model="o4-mini-deep-research",
            input=prompt,
            tools=[{"type": "web_search_preview"}]
        )

        # Parse JSON response
        content = response.output_text.strip()

        # Find JSON object (in case there's any extra text)
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        if start_idx != -1 and end_idx != -1:
            json_str = content[start_idx:end_idx]
        else:
            json_str = content

        # Try to parse JSON, with fallback for malformed responses
        try:
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try to fix common issues
            print(f"[COMPETITION] JSON parsing failed: {e}")
            print(f"[COMPETITION] Raw content: {content[:500]}...")

            # Try to fix escape sequences by using raw string
            try:
                # Remove invalid escape sequences by treating as raw string
                fixed_json = json_str.encode().decode('unicode_escape')
                result = json.loads(fixed_json)
                print(f"[COMPETITION] Fixed JSON parsing with unicode_escape")
            except Exception:
                # If that fails, try a more aggressive approach
                try:
                    # Replace problematic backslashes
                    fixed_json = json_str.replace('\\', '\\\\')
                    result = json.loads(fixed_json)
                    print(f"[COMPETITION] Fixed JSON parsing by escaping backslashes")
                except Exception as e2:
                    print(f"[COMPETITION] All JSON parsing attempts failed: {e2}")
                    raise ValueError(f"Failed to parse JSON response from LLM: {e}")

        # Validate required keys
        required_keys = {
            "dominant_players", "independent_success_cases",
            "winner_differentiation", "competition_intensity", "sources"
        }
        if not all(key in result for key in required_keys):
            raise ValueError(f"Missing required keys in response. Expected: {required_keys}")

        # Persist to database
        persist_sector_research_record(
            business_id=state.get("business_id"),  # Business-specific or sector-only research
            sector_key=state["sector_key"],
            agent_type="competition",
            research_run_id=state["research_run_id"],
            version=1,
            agent_output=result,
            model_name="o4-mini-deep-research",
            prompt_version="v1.0",
            sources=result.get("sources"),
            confidence_level=None
        )

        logger.log_success({
            "model_name": "o4-mini-deep-research",
            "response_length": len(content),
            "keys_validated": len(required_keys)
        })

        # Return only the field this agent updates
        return {
            "competition": result
        }
