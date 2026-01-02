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


def market_structure_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    Market structure research node.

    Analyzes market demand trends, identifies tailwinds/headwinds,
    and assesses small-operator viability for the given sector.
    """
    sector_description = state["sector_description"]

    with log_agent_execution(
        agent_name="market_structure",
        business_id=state.get("business_id"),
        input_snapshot={
            "sector_description": sector_description,
            "sector_key": state.get("sector_key"),
            "research_run_id": state.get("research_run_id")
        }
    ) as logger:
        try:
            # Initialize OpenAI client
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Create prompt for market structure analysis
            prompt = f"""You are a sector-level market structure research agent.

Your role:
- Analyze macro and structural forces affecting the sector
- Focus on demand trends, tailwinds, and headwinds
- Evaluate viability for small independent operators

Rules:
- Do not analyze individual companies
- Do not speculate beyond evidence
- Do not suggest strategies or actions
- Output must be factual, concise, and structured
- Respond ONLY in valid JSON matching the required schema

Analyze the market structure for the following sector: {sector_description}

Perform a comprehensive analysis focusing on:
- Demand trends and growth patterns
- Key drivers of market demand
- Major headwinds (challenges and obstacles)
- Significant tailwinds (opportunities and advantages)
- Viability for small operators in this market

Output ONLY valid JSON with exactly these keys:
- market_trend: Current market trend and growth trajectory
- demand_drivers: Key factors driving market demand
- headwinds: Major challenges and obstacles
- tailwinds: Significant opportunities and advantages
- small_operator_viability: Assessment of viability for small operators
- sources: Key data sources or references used in analysis

Do not include any text outside the JSON object."""

            # Get response from OpenAI responses API
            response = client.responses.create(
                model="o4-mini-deep-research",
                input=prompt,
                tools=[{"type": "web_search_preview"}]
            )

            # Get raw response
            raw_response = response

            # Parse JSON response
            # The model should output only JSON, so we extract it
            content = raw_response.output_text.strip()

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
                print(f"[MARKET_STRUCTURE] JSON parsing failed: {e}")
                print(f"[MARKET_STRUCTURE] Raw content: {content[:500]}...")

                # Try to fix escape sequences by using raw string
                try:
                    # Remove invalid escape sequences by treating as raw string
                    fixed_json = json_str.encode().decode('unicode_escape')
                    result = json.loads(fixed_json)
                    print(f"[MARKET_STRUCTURE] Fixed JSON parsing with unicode_escape")
                except Exception:
                    # If that fails, try a more aggressive approach
                    try:
                        # Replace problematic backslashes
                        fixed_json = json_str.replace('\\', '\\\\')
                        result = json.loads(fixed_json)
                        print(f"[MARKET_STRUCTURE] Fixed JSON parsing by escaping backslashes")
                    except Exception as e2:
                        print(f"[MARKET_STRUCTURE] All JSON parsing attempts failed: {e2}")
                        raise ValueError(f"Failed to parse JSON response from LLM: {e}")

            # Validate required keys
            required_keys = {
                "market_trend", "demand_drivers", "headwinds",
                "tailwinds", "small_operator_viability", "sources"
            }
            if not all(key in result for key in required_keys):
                raise ValueError(f"Missing required keys in response. Expected: {required_keys}")

            # Persist to database
            persist_sector_research_record(
                business_id=state.get("business_id"),  # Business-specific or sector-only research
                sector_key=state["sector_key"],
                agent_type="market_structure",
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
                "market_structure": result
            }

        except Exception as e:
            logger.log_failure(str(e), {
                "sector_description": sector_description[:100] + "..." if len(sector_description) > 100 else sector_description
            })

            # In case of error, return state with error information
            return {
                **state,
                "market_structure": {
                    "error": f"Failed to analyze market structure: {str(e)}",
                    "market_trend": "Analysis failed",
                    "demand_drivers": [],
                    "headwinds": [],
                    "tailwinds": [],
                    "small_operator_viability": "Unable to assess",
                    "sources": []
                }
            }
