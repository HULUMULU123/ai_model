"""Сборка графа `init_persona` (LangGraph)."""

from __future__ import annotations

from functools import partial

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from gen.graph.init_persona import nodes
from gen.graph.init_persona.nodes import NodeDeps
from gen.graph.init_persona.state import InitPersonaState


def build_init_persona_graph(deps: NodeDeps):
    graph = StateGraph(InitPersonaState)

    graph.add_node("write_character", partial(nodes.write_character, deps=deps))
    graph.add_node("save_bible_files", partial(nodes.save_bible_files, deps=deps))
    graph.add_node("build_reference_prompt", partial(nodes.build_reference_prompt, deps=deps))
    graph.add_node("generate_canon_batch", partial(nodes.generate_canon_batch, deps=deps))
    graph.add_node("qc_embedding", partial(nodes.qc_embedding, deps=deps))
    graph.add_node("save_canon", partial(nodes.save_canon, deps=deps))

    graph.add_edge(START, "write_character")
    graph.add_edge("write_character", "save_bible_files")
    graph.add_edge("save_bible_files", "build_reference_prompt")
    graph.add_edge("build_reference_prompt", "generate_canon_batch")
    graph.add_edge("generate_canon_batch", "qc_embedding")
    graph.add_edge("qc_embedding", "save_canon")
    graph.add_edge("save_canon", END)

    return graph.compile(checkpointer=InMemorySaver())
