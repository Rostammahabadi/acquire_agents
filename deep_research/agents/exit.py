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


def exit_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    Buyer and exit research node.

    Analyzes buyer types, exit multiples, value creation triggers,
    and successful exit narratives based on real acquisitions.
    """
    sector_description = state["sector_description"]

    with log_agent_execution(
        agent_name="buyer_exit",
        business_id=state.get("business_id"),
        input_snapshot={
            "sector_description": sector_description,
            "sector_key": state.get("sector_key"),
            "research_run_id": state.get("research_run_id")
        }
    ) as logger:
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Create prompt for exit analysis
        prompt = f"""You are a buyer behavior and exit dynamics research agent.

Your role:
- Identify who acquires businesses in this sector
- Analyze typical exit multiples
- Determine what changes increase exit value

Rules:
- Reference real acquisition behavior where possible
- Avoid speculation about future buyers
- Do not advise on deal structuring
- Focus on observed patterns, not opinions
- Respond ONLY in valid JSON matching the required schema

Analyze buyer types and exit dynamics for the following sector: {sector_description}

Focus on documented acquisition patterns:
- Types of buyers that acquire businesses in this sector
- Typical exit valuation multiples based on real transactions
- Key triggers that create enterprise value
- Narratives from successful business exits

Output ONLY valid JSON with exactly these keys:
- buyer_types: Types of buyers that acquire businesses in this sector
- typical_multiples: Typical exit valuation multiples from real transactions
- value_creation_triggers: Key factors that trigger enterprise value creation
- successful_exit_narratives: Documented narratives from successful exits
- sources: Key data sources or references used in analysis

Focus only on real acquisitions and documented exit patterns. Avoid speculation."""

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
            print(f"[EXIT] JSON parsing failed: {e}")
            print(f"[EXIT] Raw content: {content[:500]}...")

            # Try to fix escape sequences by using raw string
            try:
                # Remove invalid escape sequences by treating as raw string
                fixed_json = json_str.encode().decode('unicode_escape')
                result = json.loads(fixed_json)
                print(f"[EXIT] Fixed JSON parsing with unicode_escape")
            except Exception:
                # If that fails, try a more aggressive approach
                try:
                    # Replace problematic backslashes
                    fixed_json = json_str.replace('\\', '\\\\')
                    result = json.loads(fixed_json)
                    print(f"[EXIT] Fixed JSON parsing by escaping backslashes")
                except Exception as e2:
                    print(f"[EXIT] All JSON parsing attempts failed: {e2}")
                    raise ValueError(f"Failed to parse JSON response from LLM: {e}")

    # Validate required keys
    required_keys = {
        "buyer_types", "typical_multiples", "value_creation_triggers",
        "successful_exit_narratives", "sources"
    }
    if not all(key in result for key in required_keys):
        raise ValueError(f"Missing required keys in response. Expected: {required_keys}")

    # Persist to database
    persist_sector_research_record(
        business_id=state.get("business_id"),  # Business-specific or sector-only research
        sector_key=state["sector_key"],
        agent_type="buyer_exit",
        research_run_id=state["research_run_id"],
        version=1,
        agent_output=result,
        model_name="gpt-5-mini",
        prompt_version="v1.0",
        sources=result.get("sources"),
        confidence_level=None
    )

    logger.log_success({
        "model_name": "gpt-5-mini",
        "response_length": len(content),
        "keys_validated": len(required_keys)
    })

    # Return only the field this agent updates
    return {
        "exit": result
    }
