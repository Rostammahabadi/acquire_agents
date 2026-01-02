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


def platform_risk_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    Platform risk research node.

    Analyzes platform dependencies, policy changes, and historical failure modes.
    Assesses overall risk level based on factual analysis.
    """
    sector_description = state["sector_description"]

    with log_agent_execution(
        agent_name="platform_risk",
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

            # Create prompt for platform risk analysis
            prompt = f"""You are a platform and ecosystem risk analysis agent.

Your role:
- Identify platform dependencies and policy risks
- Surface historical failure patterns
- Highlight asymmetric downside risks

Rules:
- Focus on historical and documented platform behavior
- Avoid hypothetical or unverified risks
- Do not propose mitigations
- Do not evaluate individual listings
- Respond ONLY in valid JSON matching the required schema

Analyze platform risks for the following sector: {sector_description}

Focus on factual analysis of:
- Platform dependencies (APIs, services, infrastructure)
- Historical policy changes that impacted businesses
- Documented failure modes and outages

Output ONLY valid JSON with exactly these keys:
- platform_dependencies: List of key platform dependencies
- historical_policy_changes: Documented policy changes that affected businesses
- failure_modes: Historical failure modes and outages
- risk_level: Overall risk assessment (Low/Medium/High)
- sources: Key data sources or references used in analysis

Avoid speculation. Base analysis on documented facts only. Do not include mitigation strategies."""

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
                print(f"[PLATFORM_RISK] JSON parsing failed: {e}")
                print(f"[PLATFORM_RISK] Raw content: {content[:500]}...")

                # Try to fix escape sequences by using raw string
                try:
                    # Remove invalid escape sequences by treating as raw string
                    fixed_json = json_str.encode().decode('unicode_escape')
                    result = json.loads(fixed_json)
                    print(f"[PLATFORM_RISK] Fixed JSON parsing with unicode_escape")
                except Exception:
                    # If that fails, try a more aggressive approach
                    try:
                        # Replace problematic backslashes
                        fixed_json = json_str.replace('\\', '\\\\')
                        result = json.loads(fixed_json)
                        print(f"[PLATFORM_RISK] Fixed JSON parsing by escaping backslashes")
                    except Exception as e2:
                        print(f"[PLATFORM_RISK] All JSON parsing attempts failed: {e2}")
                        raise ValueError(f"Failed to parse JSON response from LLM: {e}")

            # Validate required keys
            required_keys = {
                "platform_dependencies", "historical_policy_changes",
                "failure_modes", "risk_level", "sources"
            }
            if not all(key in result for key in required_keys):
                raise ValueError(f"Missing required keys in response. Expected: {required_keys}")

            # Persist to database
            persist_sector_research_record(
                business_id=state.get("business_id"),  # Business-specific or sector-only research
                sector_key=state["sector_key"],
                agent_type="platform_risk",
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
                "risk_level": result.get("risk_level"),
                "keys_validated": len(required_keys)
            })

            # Return only the field this agent updates
            return {
                "platform_risk": result
            }

        except Exception as e:
            logger.log_failure(str(e), {
                "sector_description": sector_description[:100] + "..." if len(sector_description) > 100 else sector_description
            })

            # In case of error, return state with error information
            return {
                **state,
                "platform_risk": {
                    "error": f"Failed to analyze platform risk: {str(e)}",
                    "platform_dependencies": [],
                    "historical_policy_changes": [],
                    "failure_modes": [],
                    "risk_level": "Unable to assess",
                    "sources": []
                }
            }
