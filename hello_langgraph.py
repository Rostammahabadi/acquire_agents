from langgraph.graph import StateGraph, START, END
from typing import TypedDict

# Define the state
class State(TypedDict):
    messages: list

# Define the nodes
def node_1(state: State) -> State:
    return {"messages": state["messages"] + ["I'm node 1!"]}

def node_2(state: State) -> State:
    return {"messages": state["messages"] + ["I'm node 2!"]}

def node_3(state: State) -> State:
    return {"messages": state["messages"] + ["I'm node 3!"]}

# Build the graph
builder = StateGraph(State)
builder.add_node("node_1", node_1)
builder.add_node("node_2", node_2)
builder.add_node("node_3", node_3)

builder.add_edge(START, "node_1")
builder.add_edge("node_1", "node_2")
builder.add_edge("node_2", "node_3")
builder.add_edge("node_3", END)

# Compile the graph
graph = builder.compile()

# Run the graph
if __name__ == "__main__":
    result = graph.invoke({"messages": []})
    print(result)
