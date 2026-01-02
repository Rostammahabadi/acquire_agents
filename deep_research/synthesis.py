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


def synthesis_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    Synthesis node that reasons over completed research.

    Generates SWOT analysis, identifies non-obvious risks,
    time-sensitive opportunities, and produces sector fit verdict.
    """
    # Extract research outputs
    market_structure = state.get("market_structure", {})
    platform_risk = state.get("platform_risk", {})
    monetization = state.get("monetization", {})
    competition = state.get("competition", {})
    exit_data = state.get("exit", {})

    # Validate that all required research is available
    required_research = {
        "market_structure": market_structure,
        "platform_risk": platform_risk,
        "monetization": monetization,
        "competition": competition,
        "exit": exit_data
    }

    missing_research = [name for name, data in required_research.items() if not data]
    if missing_research:
        raise ValueError(f"Synthesis cannot proceed: missing research data for {missing_research}. "
                        f"All research agents must complete successfully before synthesis can run.")

    with log_agent_execution(
        agent_name="synthesis",
        business_id=state.get("business_id"),
        input_snapshot={
            "sector_key": state.get("sector_key"),
            "research_run_id": state.get("research_run_id"),
            "available_research": {
                "market_structure": bool(market_structure),
                "platform_risk": bool(platform_risk),
                "monetization": bool(monetization),
                "competition": bool(competition),
                "exit": bool(exit_data)
            },
            "validation_passed": True
        }
    ) as logger:
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Create synthesis prompt
        prompt = f"""You are a synthesis and reasoning agent.

Your role:
- Reason over completed research outputs
- Identify cross-cutting patterns and second-order risks
- Produce a concise SWOT analysis
- Assess sector suitability for a high-risk, short-horizon buyer

Rules:
- Do NOT introduce new facts
- Do NOT repeat research verbatim
- Only reason over provided inputs
- Be decisive and concise
- Respond ONLY in valid JSON matching the required schema

Synthesize the following research outputs into a comprehensive sector analysis:

MARKET STRUCTURE:
{json.dumps(market_structure)}

PLATFORM RISK:
{json.dumps(platform_risk)}

MONETIZATION:
{json.dumps(monetization)}

COMPETITION:
{json.dumps(competition)}

EXIT ANALYSIS:
{json.dumps(exit_data)}

Based on these research findings, perform the following synthesis tasks:

1. Generate a SWOT analysis by reasoning over all research areas
2. Identify non-obvious risks that emerge from combining multiple research areas
3. Identify time-sensitive opportunities that require immediate action
4. Produce a sector_fit_verdict assessing overall attractiveness for a high-risk, short-horizon buyer

Output ONLY valid JSON with exactly this structure:
{{
  "swot": {{
    "strengths": ["list of key strengths"],
    "weaknesses": ["list of key weaknesses"],
    "opportunities": ["list of key opportunities"],
    "threats": ["list of key threats"]
  }},
  "non_obvious_risks": ["list of risks that emerge from combining research areas"],
  "time_sensitive_opportunities": ["list of opportunities requiring immediate action"],
  "sector_fit_verdict": "High/Medium/Low attractiveness assessment",
  "justification": "1-2 sentence justification for the verdict"
}}

Do not repeat individual research findings. Do not introduce new facts. Focus on synthesis and reasoning across all research areas."""

        # Get response from OpenAI responses API
        response = client.responses.create(
            model="gpt-5-mini",
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
            print(f"[SYNTHESIS] JSON parsing failed: {e}")
            print(f"[SYNTHESIS] Raw content: {content[:500]}...")

            # Try to fix escape sequences by using raw string
            try:
                # Remove invalid escape sequences by treating as raw string
                fixed_json = json_str.encode().decode('unicode_escape')
                result = json.loads(fixed_json)
                print(f"[SYNTHESIS] Fixed JSON parsing with unicode_escape")
            except Exception:
                # If that fails, try a more aggressive approach
                try:
                    # Replace problematic backslashes
                    fixed_json = json_str.replace('\\', '\\\\')
                    result = json.loads(fixed_json)
                    print(f"[SYNTHESIS] Fixed JSON parsing by escaping backslashes")
                except Exception as e2:
                    print(f"[SYNTHESIS] All JSON parsing attempts failed: {e2}")
                    raise ValueError(f"Failed to parse JSON response from LLM: {e}")

        # Validate required keys
        required_keys = {"swot", "non_obvious_risks", "time_sensitive_opportunities", "sector_fit_verdict", "justification"}
        if not all(key in result for key in required_keys):
            raise ValueError(f"Missing required keys in response. Expected: {required_keys}")

        # Validate SWOT structure
        swot = result.get("swot", {})
        swot_keys = {"strengths", "weaknesses", "opportunities", "threats"}
        if not all(key in swot for key in swot_keys):
            raise ValueError(f"SWOT missing required keys. Expected: {swot_keys}")

        # Persist to database
        persist_sector_research_record(
            business_id=state.get("business_id"),  # Business-specific or sector-only research
            sector_key=state["sector_key"],
            agent_type="synthesis",
            research_run_id=state["research_run_id"],
            version=1,
            agent_output=result,
            model_name="o4-mini-deep-research",  # Synthesis uses o4-mini-deep-research
            prompt_version="v1.0",
            sources=None,  # Synthesis doesn't have sources field
            confidence_level=None
        )

    logger.log_success({
        "model_name": "o4-mini-deep-research",
        "response_length": len(content),
        "swot_keys_validated": len(swot_keys),
        "research_inputs_used": sum([
            bool(market_structure), bool(platform_risk),
            bool(monetization), bool(competition), bool(exit_data)
        ])
    })

    # Return only the field this agent updates
    return {
        "synthesis": result
    }
