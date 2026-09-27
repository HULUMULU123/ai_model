"""Сборка графа `generate` (LangGraph)."""

from __future__ import annotations

from functools import partial

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from gen.graph.generate import nodes
from gen.graph.generate.nodes import NodeDeps
from gen.graph.generate.state import GenerateState


def build_generate_graph(deps: NodeDeps, *, max_retries: int = 1):
    graph = StateGraph(GenerateState)

    graph.add_node("build_prompt", partial(nodes.build_prompt, deps=deps))
    graph.add_node("generate_one", partial(nodes.generate_one, deps=deps))
    graph.add_node("qc_one", partial(nodes.qc_one, deps=deps))
    graph.add_node("finalize_accepted", nodes.finalize_accepted)
    graph.add_node("finalize_low_confidence", nodes.finalize_low_confidence)

    graph.add_edge(START, "build_prompt")
    graph.add_edge("build_prompt", "generate_one")
    graph.add_edge("generate_one", "qc_one")
    graph.add_conditional_edges(
        "qc_one",
        partial(nodes.should_retry, max_retries=max_retries),
        {
            "accept": "finalize_accepted",
            "retry": "generate_one",
            "escalate": "finalize_low_confidence",
        },
    )
    graph.add_edge("finalize_accepted", END)
    graph.add_edge("finalize_low_confidence", END)

    return graph.compile(checkpointer=InMemorySaver())
