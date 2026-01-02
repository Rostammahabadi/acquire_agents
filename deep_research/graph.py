from langgraph.graph import StateGraph, START, END
from .state import DeepResearchState
from .orchestrator import orchestrator_node
from .agents.market_structure import market_structure_node
from .agents.platform_risk import platform_risk_node
from .agents.monetization import monetization_node
from .agents.competition import competition_node
from .agents.exit import exit_node
from .synthesis import synthesis_node


def build_deep_research_graph():
    """Build the deep research LangGraph workflow."""

    # Create the graph
    graph = StateGraph(DeepResearchState)

    # Add nodes
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("market_structure", market_structure_node)
    graph.add_node("platform_risk", platform_risk_node)
    graph.add_node("monetization", monetization_node)
    graph.add_node("competition", competition_node)
    graph.add_node("exit", exit_node)
    graph.add_node("synthesis", synthesis_node)

    # Define the workflow edges
    # Start -> orchestrator
    graph.add_edge(START, "orchestrator")

    # Orchestrator -> parallel execution of all research agents
    graph.add_edge("orchestrator", "market_structure")
    graph.add_edge("orchestrator", "platform_risk")
    graph.add_edge("orchestrator", "monetization")
    graph.add_edge("orchestrator", "competition")
    graph.add_edge("orchestrator", "exit")

    # All research agents join at synthesis
    graph.add_edge("market_structure", "synthesis")
    graph.add_edge("platform_risk", "synthesis")
    graph.add_edge("monetization", "synthesis")
    graph.add_edge("competition", "synthesis")
    graph.add_edge("exit", "synthesis")

    # Synthesis -> End
    graph.add_edge("synthesis", END)

    # Compile the graph
    return graph.compile()


def run_deep_research(sector_description: str, business_id: str = None) -> dict:
    """
    Run the deep research workflow for a given sector description.

    Args:
        sector_description: Description of the sector to research
        business_id: Optional business ID to associate research with

    Returns:
        dict: The synthesis results containing SWOT, risks, opportunities, and verdict
    """
    # Build the graph
    app = build_deep_research_graph()

    # Initialize state (research_run_id and sector_key will be set by orchestrator)
    initial_state = DeepResearchState(
        sector_description=sector_description,
        business_id=business_id,
        research_run_id="",  # Will be set by orchestrator
        sector_key="",  # Will be set by orchestrator
        market_structure=None,
        platform_risk=None,
        monetization=None,
        competition=None,
        exit=None,
        synthesis=None
    )

    # Run the workflow
    final_state = app.invoke(initial_state)

    # Return only the synthesis results
    return final_state.get("synthesis", {})
