"""KPM Support Agent — Section 3: Problem Solver for KPM Systems & Policies."""

import json
from backend.deepseek_client import chat_completion
from backend.mcp_server import search_documents, search_documents_tfidf

_sessions: dict[str, dict] = {}

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
- WAJIB mulakan dengan sapaan mesra: "Assalamualaikum dan salam sejahtera! Saya SMARTAssist Hub KPM Support Agent. Saya di sini untuk membantu anda dengan sebarang isu berkaitan sistem KPM seperti EMIS, APDM, DTPCare, SK@S dan lain-lain. Apa yang boleh saya bantu hari ini?"

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
    if session_id not in _sessions:
        _sessions[session_id] = {"history_queries": []}
    return _sessions[session_id]


def _build_retrieval_query(query: str, history: list[dict] | None = None) -> str:
    """Build context-aware retrieval query using recent conversation turns."""
    parts = [query]
    if history:
        recent_user = [m["content"] for m in history[-6:] if m["role"] == "user"]
        if recent_user:
            parts = recent_user[-3:] + [query]
    return " ".join(parts)


def _retrieve_docs(query: str, history: list[dict] | None = None) -> list[dict]:
    """Retrieve relevant documents using session-aware query."""
    retrieval_query = _build_retrieval_query(query, history)

    docs = search_documents(retrieval_query, top_k=5)
    if not docs:
        docs = search_documents_tfidf(retrieval_query, top_k=5)

    if not docs and query != retrieval_query:
        docs = search_documents(query, top_k=3)
        if not docs:
            docs = search_documents_tfidf(query, top_k=3)

    return docs


def _format_doc_context(docs: list[dict]) -> str:
    if not docs:
        return "\n\nTiada dokumen berkaitan ditemui dalam indeks."

    sections = []
    for i, d in enumerate(docs, 1):
        content = d["content"]
        if len(content) > 1500:
            content = content[:1500] + "..."
        source = d.get("source_file", "")
        cat = d.get("category", "")
        sections.append(
            f"[Dokumen {i}: {d['title']}]\n"
            f"Sumber: {source} | Kategori: {cat}\n"
            f"{content}"
        )
    return "\n\nDokumen rujukan:\n" + "\n\n".join(sections)


def handle(query: str, history: list[dict] | None = None, session_id: str = "default") -> str:
    if query == '__INTRO__':
        return "Assalamualaikum dan salam sejahtera! 😊 Saya SMARTAssist Hub KPM Support Agent. Saya di sini untuk membantu tuan/puan dengan sebarang isu berkaitan sistem KPM seperti EMIS, APDM, DTPCare, SK@S dan lain-lain. Apa yang boleh saya bantu hari ini?"

    session = _get_session(session_id)
    session["history_queries"].append(query)

    docs = _retrieve_docs(query, history)
    doc_context = _format_doc_context(docs)

    prior_user_msgs = [m for m in (history or []) if m.get("role") == "user"]
    is_first_message = len(prior_user_msgs) <= 1
    session_context = "\n\nINI ADALAH PERMULAAN SESI BAHARU. Wajib mulakan dengan sapaan perkenalan." if is_first_message else "\n\nSesi sedang berjalan. JANGAN ulang sapaan perkenalan. Teruskan perbualan secara semula jadi dan rujuk konteks sebelumnya."

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT + session_context + doc_context},
    ]
    if history:
        for msg in history[-8:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": query})

    try:
        return chat_completion(messages=messages, temperature=0.5, max_tokens=2000)
    except RuntimeError as e:
        if docs:
            refs = "\n".join(f"- {d['title']} ({d.get('source_file', '')})" for d in docs)
            return (
                f"Ralat menjana jawapan. Namun, dokumen berikut mungkin berkaitan:\n\n{refs}\n\n"
                "Sila rujuk dokumen ini secara manual atau cuba lagi."
            )
        return f"Ralat sokongan KPM: {e}"


def clear_session(session_id: str):
    _sessions.pop(session_id, None)
