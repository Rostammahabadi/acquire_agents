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


def monetization_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    Monetization dynamics research node.

    Analyzes dominant monetization models, high-performing strategies,
    common gaps, and revenue ceiling constraints in the sector.
    """
    sector_description = state["sector_description"]

    with log_agent_execution(
        agent_name="monetization",
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

            # Create prompt for monetization analysis
            prompt = f"""You are a monetization dynamics research agent.

Your role:
- Analyze how revenue is generated in this sector
- Identify proven monetization strategies
- Surface common monetization gaps and ceilings

Rules:
- Base conclusions on real-world examples
- Do not invent new monetization ideas
- Do not provide tactical playbooks
- Avoid general business advice
- Respond ONLY in valid JSON matching the required schema

Analyze monetization dynamics for the following sector: {sector_description}

Focus on real-world monetization patterns and constraints:
- Dominant monetization models used by successful businesses
- High-performing revenue strategies with documented results
- Common monetization gaps that businesses struggle with
- Revenue ceiling constraints and scaling limitations

Output ONLY valid JSON with exactly these keys:
- dominant_models: List of dominant monetization models in the sector
- high_performing_strategies: Documented high-performing revenue strategies
- common_monetization_gaps: Common monetization challenges and gaps
- revenue_ceiling_constraints: Factors that constrain revenue scaling
- sources: Key data sources or references used in analysis

Focus only on real-world tactics and documented patterns. Do not include hypothetical strategies."""

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
                print(f"[MONETIZATION] JSON parsing failed: {e}")
                print(f"[MONETIZATION] Raw content: {content[:500]}...")

                # Try to fix escape sequences by using raw string
                try:
                    # Remove invalid escape sequences by treating as raw string
                    fixed_json = json_str.encode().decode('unicode_escape')
                    result = json.loads(fixed_json)
                    print(f"[MONETIZATION] Fixed JSON parsing with unicode_escape")
                except Exception:
                    # If that fails, try a more aggressive approach
                    try:
                        # Replace problematic backslashes
                        fixed_json = json_str.replace('\\', '\\\\')
                        result = json.loads(fixed_json)
                        print(f"[MONETIZATION] Fixed JSON parsing by escaping backslashes")
                    except Exception as e2:
                        print(f"[MONETIZATION] All JSON parsing attempts failed: {e2}")
                        raise ValueError(f"Failed to parse JSON response from LLM: {e}")

            # Validate required keys
            required_keys = {
                "dominant_models", "high_performing_strategies",
                "common_monetization_gaps", "revenue_ceiling_constraints", "sources"
            }
            if not all(key in result for key in required_keys):
                raise ValueError(f"Missing required keys in response. Expected: {required_keys}")

            # Persist to database
            persist_sector_research_record(
                business_id=state.get("business_id"),  # Business-specific or sector-only research
                sector_key=state["sector_key"],
                agent_type="monetization",
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
                "monetization": result
            }

        except Exception as e:
            logger.log_failure(str(e), {
                "sector_description": sector_description[:100] + "..." if len(sector_description) > 100 else sector_description
            })

            # In case of error, return state with error information
            return {
                **state,
                "monetization": {
                    "error": f"Failed to analyze monetization dynamics: {str(e)}",
                    "dominant_models": [],
                    "high_performing_strategies": [],
                    "common_monetization_gaps": [],
                    "revenue_ceiling_constraints": [],
                    "sources": []
                }
            }
