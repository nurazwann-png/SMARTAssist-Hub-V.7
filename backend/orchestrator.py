from __future__ import annotations

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END

from backend.deepseek_client import chat_completion


# ── State ──

class OrchestratorState(TypedDict):
    user_query: str
    intent: str
    conversation_history: list[dict]
    active_agent: str
    agent_output: str
    session_id: str


INTENT_LABELS = [
    "data_analysis",
    "letter_generator",
    "report_generator",
    "document_reviewer",
    "kpm_support",
    "fallback",
]


# ── Nodes ──

def classify_intent(state: OrchestratorState) -> dict:
    query = state["user_query"]
    history = state.get("conversation_history", [])

    history_context = ""
    if history:
        recent = history[-6:]
        history_context = "\n".join(
            f"{m['role']}: {m['content']}" for m in recent
        )

    system_prompt = f"""Anda ialah pengelas niat (intent classifier) untuk sistem SMARTAssist Hub.
Klasifikasikan mesej pengguna ke SALAH SATU kategori berikut sahaja:

- data_analysis : soalan tentang data, statistik, analisis, enrolmen, bilangan pelajar/guru, graf, carta
- letter_generator : permintaan menulis/menjana surat rasmi, memo dalaman, surat siaran
- report_generator : permintaan menjana laporan rasmi, laporan satu muka surat, ringkasan laporan
- document_reviewer : permintaan semak, proofread, review dokumen/surat/memo/laporan sedia ada
- kpm_support : soalan tentang sistem KPM (EMIS, DTPCare, Cerdik, PBPPP, idMe), masalah teknikal, polisi KPM, prosedur
- fallback : soalan umum, perbualan biasa, atau apa-apa yang tidak sesuai dengan kategori di atas

PENTING:
- "laporan" bermaksud report_generator, BUKAN data_analysis
- "semak surat" atau "review dokumen" bermaksud document_reviewer, BUKAN letter_generator
- Jika ragu, pilih fallback

Balas HANYA dengan satu perkataan kategori dari senarai di atas. Tiada penjelasan.

{f"Konteks perbualan terkini:{chr(10)}{history_context}" if history_context else ""}"""

    try:
        result = chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
            temperature=0.0,
            max_tokens=20,
        )
        intent = result.strip().lower().replace(" ", "_")
        if intent not in INTENT_LABELS:
            intent = "fallback"
    except RuntimeError:
        intent = "fallback"

    return {"intent": intent, "active_agent": intent}


def _agent_stub(agent_name: str):
    def node(state: OrchestratorState) -> dict:
        from agents import (
            data_analysis,
            letter_generator,
            kpm_support,
            report_generator,
            document_reviewer,
        )
        agent_map = {
            "data_analysis": data_analysis,
            "letter_generator": letter_generator,
            "kpm_support": kpm_support,
            "report_generator": report_generator,
            "document_reviewer": document_reviewer,
        }
        module = agent_map.get(agent_name)
        if module and hasattr(module, "handle"):
            import inspect
            sig = inspect.signature(module.handle)
            kwargs = {
                "query": state["user_query"],
                "history": state.get("conversation_history", []),
            }
            if "session_id" in sig.parameters:
                kwargs["session_id"] = state.get("session_id", "default")
            output = module.handle(**kwargs)
        else:
            output = f"[{agent_name}] Agen ini belum diaktifkan."
        return {"agent_output": output, "active_agent": agent_name}
    node.__name__ = agent_name
    return node


def fallback_node(state: OrchestratorState) -> dict:
    query = state["user_query"]
    history = state.get("conversation_history", [])

    messages = [
        {
            "role": "system",
            "content": (
                "Anda ialah pembantu AI umum untuk SMARTAssist Hub, sistem sokongan PPD/KPM. "
                "Jawab soalan pengguna dengan ringkas dan membantu dalam Bahasa Malaysia. "
                "Jika soalan berkaitan data/surat/laporan/semakan/sistem KPM, "
                "cadangkan pengguna menggunakan agen khusus yang tersedia."
            ),
        },
    ]
    for msg in history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": query})

    try:
        output = chat_completion(messages=messages, temperature=0.5)
    except RuntimeError as e:
        output = str(e)

    return {"agent_output": output, "active_agent": "fallback"}


# ── Routing ──

def route_intent(state: OrchestratorState) -> str:
    intent = state.get("intent", "fallback")
    if intent in INTENT_LABELS:
        return intent
    return "fallback"


# ── Graph assembly ──

def build_graph() -> StateGraph:
    graph = StateGraph(OrchestratorState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("data_analysis", _agent_stub("data_analysis"))
    graph.add_node("letter_generator", _agent_stub("letter_generator"))
    graph.add_node("report_generator", _agent_stub("report_generator"))
    graph.add_node("document_reviewer", _agent_stub("document_reviewer"))
    graph.add_node("kpm_support", _agent_stub("kpm_support"))
    graph.add_node("fallback", fallback_node)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_intent,
        {
            "data_analysis": "data_analysis",
            "letter_generator": "letter_generator",
            "report_generator": "report_generator",
            "document_reviewer": "document_reviewer",
            "kpm_support": "kpm_support",
            "fallback": "fallback",
        },
    )

    for agent_name in INTENT_LABELS:
        graph.add_edge(agent_name, END)

    return graph


_compiled = None

def get_workflow():
    global _compiled
    if _compiled is None:
        _compiled = build_graph().compile()
    return _compiled


def run_query(query: str, conversation_history: list[dict] | None = None, session_id: str = "default") -> dict:
    workflow = get_workflow()
    state: OrchestratorState = {
        "user_query": query,
        "intent": "",
        "conversation_history": conversation_history or [],
        "active_agent": "",
        "agent_output": "",
        "session_id": session_id,
    }
    result = workflow.invoke(state)
    return result
