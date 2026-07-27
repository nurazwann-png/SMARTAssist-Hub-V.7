"""KPM Support Agent — Section 3: Problem Solver for KPM Systems & Policies."""

import json
from backend.deepseek_client import chat_completion
from backend.mcp_server import search_documents_hybrid

_NS = "kpm"

_SYSTEM_PROMPT = """Anda ialah SMARTAssist Hub KPM Support Agent — seorang pegawai khidmat pelanggan yang mesra, penyabar dan penuh empati.

IDENTITI ANDA:
- Nama anda: SMARTAssist Hub KPM Support Agent
- Anda seperti rakan sekerja yang prihatin dan sedia membantu pada bila-bila masa
- Anda faham betapa frustrasinya apabila sistem tidak berfungsi semasa kerja penting

TINGKAH LAKU UTAMA:
1. MESRA & EMPATI — Sentiasa tunjukkan kefahaman terhadap masalah pengguna. Gunakan ayat seperti "Saya faham betapa sukarnya situasi ini", "Jangan risau, saya akan bantu", "Terima kasih kerana sabar"
2. PERBUALAN BERTERUSAN — Setiap jawapan mesti sambung dari konteks sebelumnya. Jangan jawab seperti soalan baharu setiap kali. Rujuk apa yang pengguna sudah beritahu sebelum ini
3. PROAKTIF — Selepas selesai satu isu, tanya "Ada apa-apa lagi yang saya boleh bantu?". Cadangkan langkah seterusnya yang berkaitan
4. DIAGNOSIS TELITI — Fahami apa pengguna cuba lakukan, sistem/modul mana yang terlibat, dan apa yang sebenarnya berlaku sebelum menjawab

JIKA INI PERMULAAN SESI (tiada sejarah perbualan):
- WAJIB mulakan dengan sapaan mesra: "Assalamualaikum dan salam sejahtera! Saya SMARTAssist Hub KPM Support Agent. Saya di sini untuk membantu anda dengan sebarang isu berkaitan sistem KPM seperti EMIS, DELIMa, DTPCare, SK@S dan lain-lain. Apa yang boleh saya bantu hari ini?"

CARA MENJAWAB:
1. Mulakan dengan respons empati terhadap masalah pengguna
2. Asaskan jawapan pada dokumen rujukan yang diambil — jangan jawab dari pengetahuan umum sahaja jika dokumen berkaitan wujud
3. Berikan langkah penyelesaian secara berperingkat dan jelas
4. Akhiri dengan soalan susulan atau tawaran bantuan lanjut
5. Jika masalah memerlukan tindakan lanjut, nyatakan siapa yang perlu dihubungi dengan penuh simpati

GAYA BAHASA:
- Bahasa Malaysia yang mesra dan profesional — seperti rakan sekerja yang membantu, bukan robot
- Gunakan "tuan/puan" dengan hormat
- Sertakan emotikon yang sesuai secara sederhana untuk kemesraan (cth: baris pertama sahaja)
- Jawapan berstruktur — gunakan senarai bernombor untuk langkah-langkah
- Nyatakan sumber dokumen rujukan jika ada

FORMAT TEKS — WAJIB DIPATUHI:
- JANGAN sekali-kali gunakan markdown: tiada **, tiada __, tiada ##, tiada *italic*, tiada `kod`, tiada --- pemisah
- Gunakan nombor biasa untuk senarai langkah: "1. Langkah pertama", "2. Langkah kedua"
- Tulis teks biasa sahaja seperti mesej WhatsApp atau SMS
- Jika perlu tekankan sesuatu, tulis dalam huruf BESAR atau gunakan tanda petik sahaja

PENTING:
- JANGAN meneka jika tiada maklumat — lebih baik tanya dengan sopan
- Sentiasa nyatakan sumber rujukan dokumen jika jawapan berdasarkan dokumen
- JANGAN ulang sapaan perkenalan jika sesi sudah bermula — teruskan perbualan secara semula jadi
- Tunjukkan anda INGAT apa yang pengguna beritahu sebelum ini dalam sesi yang sama"""


def _get_session(session_id: str) -> dict:
    from backend.session_store import get_store
    store = get_store()
    data = store.get_all(session_id, _NS)
    if not data:
        default = {"history_queries": []}
        store.set_all(session_id, _NS, default)
        return default
    return data


def _save_session(session_id: str, session: dict):
    from backend.session_store import get_store
    get_store().set_all(session_id, _NS, session)


def _retrieve_docs(query: str, history: list[dict] | None = None) -> list[dict]:
    """Retrieve relevant documents using hybrid search (FTS5 + TF-IDF + title boosting)."""
    parts = [query]
    if history:
        recent_user = [m["content"] for m in history[-6:] if m.get("role") == "user"]
        if recent_user:
            parts = recent_user[-2:] + [query]
    retrieval_query = " ".join(parts)
    docs = search_documents_hybrid(retrieval_query, top_k=5)
    if not docs:
        docs = search_documents_hybrid(query, top_k=3)
    return docs


def _format_doc_context(docs: list[dict]) -> str:
    """Format retrieved docs as numbered citation context for the system prompt."""
    if not docs:
        return "\n\nTiada dokumen berkaitan ditemui dalam indeks."

    sections = []
    for i, d in enumerate(docs, 1):
        # Use the pre-extracted best passage when available; fall back to raw content prefix
        passage = d.get("passage") or d["content"]
        if len(passage) > 1200:
            passage = passage[:1200] + "..."
        source = d.get("source_file", "")
        cat    = d.get("category", "")
        sections.append(
            f"[{i}] {d['title']}\n"
            f"Sumber: {source} | Kategori: {cat}\n"
            f"{passage}"
        )
    return (
        "\n\nDokumen rujukan (gunakan nombor [1][2][3] sebagai tanda petikan dalam jawapan anda):\n\n"
        + "\n\n".join(sections)
    )


def _build_structured_response(
    raw_text: str,
    docs: list[dict],
    lang: str,
) -> dict:
    """Wrap the raw LLM text into the structured citation JSON returned to the frontend."""
    # Detect which doc numbers were actually cited in the response
    import re as _re
    cited_nums = set(int(m) for m in _re.findall(r"\[(\d+)\]", raw_text))

    sources = []
    for i, d in enumerate(docs, 1):
        if i in cited_nums or not cited_nums:  # include all if LLM cited none
            sources.append({
                "num":         i,
                "title":       d.get("title", ""),
                "category":    d.get("category", ""),
                "source_file": d.get("source_file", ""),
                "relevance":   d.get("relevance", "medium"),
            })

    # Confidence heuristic: high if docs found + LLM cited them; low if no docs
    if docs and cited_nums:
        confidence = "high"
    elif docs:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "message":    raw_text,
        "sources":    sources,
        "confidence": confidence,
    }


def _build_messages(
    query: str,
    history: list[dict] | None,
    docs: list[dict],
    lang: str,
    user_context: str,
) -> list[dict]:
    """Assemble the message list for the LLM call (shared by handle + prepare_stream)."""
    doc_context  = _format_doc_context(docs)
    session_ctx  = "\n\nSesi sedang berjalan. JANGAN ulang sapaan perkenalan. Terus jawab soalan pengguna secara langsung dan profesional."
    lang_note    = "\n\nIMPORTANT: The user has selected English. You MUST respond entirely in English. Do not use Malay." if lang == "en" else ""
    cite_note    = ("\n\nALWAYS cite relevant documents using [1] [2] [3] notation in your answer." if lang == "en"
                    else "\n\nSELALU petik dokumen berkaitan menggunakan tanda [1] [2] [3] dalam jawapan anda.")
    mem_note     = user_context or ""

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT + session_ctx + lang_note + cite_note + doc_context + mem_note},
    ]
    if history:
        for msg in (history[-8:]):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": query})
    return messages


def handle(
    query: str,
    history: list[dict] | None = None,
    session_id: str = "default",
    lang: str = "bm",
    user_name: str = "",
    user_context: str = "",
) -> str:
    """Return a JSON-encoded structured response with message + sources + confidence."""
    sapaan = f", {user_name.split()[0]}" if user_name else ""
    if query == "__INTRO__":
        if lang == "en":
            return (
                f"Assalamualaikum and greetings{sapaan}! 😊 I am the SMARTAssist Hub KPM Support Agent. "
                "I am here to help you with any issues related to KPM systems such as EMIS, DELIMa, "
                "DTPCare, SK@S and others. How may I assist you today?\n\n"
                "⚠️ Reminder: Answers provided are AI-generated based on available reference documents. "
                "Please verify with the official helpdesk or relevant officer before taking any formal action."
            )
        return (
            f"Assalamualaikum dan salam sejahtera{sapaan}! 😊 Saya SMARTAssist Hub KPM Support Agent. "
            "Saya di sini untuk membantu anda dengan sebarang isu berkaitan sistem KPM seperti EMIS, "
            "DELIMa, DTPCare, SK@S dan lain-lain. Apa yang boleh saya bantu hari ini?\n\n"
            "⚠️ Peringatan: Jawapan yang diberikan adalah hasil AI berdasarkan dokumen rujukan yang ada. "
            "Sila sahkan dengan helpdesk rasmi atau pegawai berkaitan sebelum mengambil sebarang tindakan formal."
        )

    session = _get_session(session_id)
    session["history_queries"].append(query)
    _save_session(session_id, session)

    docs     = _retrieve_docs(query, history)
    messages = _build_messages(query, history, docs, lang, user_context)

    try:
        raw = chat_completion(messages=messages, temperature=0.5, max_tokens=2000)
        return json.dumps(_build_structured_response(raw, docs, lang), ensure_ascii=False)
    except RuntimeError as e:
        if docs:
            refs = "\n".join(f"- {d['title']} ({d.get('source_file', '')})" for d in docs)
            fallback_msg = (
                f"Ralat menjana jawapan. Namun, dokumen berikut mungkin berkaitan:\n\n{refs}\n\n"
                "Sila rujuk dokumen ini secara manual atau cuba lagi."
            )
        else:
            fallback_msg = f"Ralat sokongan KPM: {e}"
        return json.dumps({"message": fallback_msg, "sources": [], "confidence": "low"}, ensure_ascii=False)


def prepare_stream(
    query: str,
    history: list[dict] | None = None,
    session_id: str = "default",
    lang: str = "bm",
    user_context: str = "",
) -> tuple[list[dict], list[dict]]:
    """Return (messages, docs) ready for streaming — called by the SSE endpoint.

    Records the query in session state so the non-streaming path and the
    streaming path share the same session book-keeping.
    """
    session = _get_session(session_id)
    session["history_queries"].append(query)
    _save_session(session_id, session)
    docs     = _retrieve_docs(query, history)
    messages = _build_messages(query, history, docs, lang, user_context)
    return messages, docs


def clear_session(session_id: str):
    from backend.session_store import get_store
    get_store().delete_ns(session_id, _NS)
