from typing import Optional, TypedDict, Any, Annotated


def _update_dict(old: Optional[dict[str, Any]], new: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Reducer that returns new value if present, otherwise old value."""
    return new if new is not None else old


def _keep_value(old: str, new: Optional[str]) -> str:
    """Reducer that keeps the existing value (for read-only fields)."""
    return new if new is not None else old


class DeepResearchState(TypedDict):
    """State for the deep research workflow."""

    # Input - use Annotated to allow parallel reads
    sector_description: Annotated[str, _keep_value]
    business_id: Annotated[Optional[str], _keep_value]

    # Persistence metadata - use Annotated to allow parallel reads
    research_run_id: Annotated[str, _keep_value]
    sector_key: Annotated[str, _keep_value]

    # Agent outputs - all optional and JSON-serializable
    # Use Annotated to allow concurrent updates from parallel nodes
    market_structure: Annotated[Optional[dict[str, Any]], _update_dict]
    platform_risk: Annotated[Optional[dict[str, Any]], _update_dict]
    monetization: Annotated[Optional[dict[str, Any]], _update_dict]
    competition: Annotated[Optional[dict[str, Any]], _update_dict]
    exit: Annotated[Optional[dict[str, Any]], _update_dict]

    # Final synthesis
    synthesis: Annotated[Optional[dict[str, Any]], _update_dict]
