import uuid
from typing import Any, Dict
from deep_research.state import DeepResearchState
from utils import log_agent_execution


def orchestrator_node(state: DeepResearchState) -> Dict[str, Any]:
    """
    Orchestrator node that defines the research tasks to be executed.

    This node is deterministic and validates the sector_description.
    It conceptually defines the 5 research tasks:
    - market_structure
    - platform_risk
    - monetization
    - competition
    - exit

    No LLM calls are made here. The sector_description is passed forward unchanged.
    """
    with log_agent_execution(
        agent_name="orchestrator",
        business_id=state.get("business_id"),
        input_snapshot={"sector_description": state.get("sector_description")}
    ) as logger:
        # Validate that sector_description exists
        if not state.get("sector_description"):
            logger.log_failure("sector_description is required in state")
            raise ValueError("sector_description is required in state")

        # Generate persistence metadata
        research_run_id = str(uuid.uuid4())
        # Create a canonical sector key from the description (simplified for now)
        sector_key = state["sector_description"].lower().replace(" ", "_")[:100]

        # The 5 research tasks are conceptually defined here but not executed
        # They will be handled by separate agent nodes in the graph
        _research_tasks = [
            "market_structure",
            "platform_risk",
            "monetization",
            "competition",
            "exit"
        ]

        logger.log_success({
            "research_run_id": research_run_id,
            "sector_key": sector_key,
            "research_tasks_defined": len(_research_tasks),
            "business_id": state.get("business_id")
        })

        # Return updated state with persistence metadata
        return {
            **state,
            "research_run_id": research_run_id,
            "sector_key": sector_key
        }
