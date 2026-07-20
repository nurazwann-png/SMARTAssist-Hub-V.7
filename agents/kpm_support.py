"""KPM Support Agent — Section 3: Problem Solver for KPM Systems & Policies."""

import json
from backend.deepseek_client import chat_completion
from backend.mcp_server import search_documents, search_documents_tfidf

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


def handle(query: str, history: list[dict] | None = None, session_id: str = "default", lang: str = "bm", user_name: str = "") -> str:
    sapaan = f", {user_name.split()[0]}" if user_name else ""
    if query == '__INTRO__':
        if lang == "en":
            return (f"Assalamualaikum and greetings{sapaan}! 😊 I am the SMARTAssist Hub KPM Support Agent. I am here to help you with any issues related to KPM systems such as EMIS, DELIMa, DTPCare, SK@S and others. How may I assist you today?\n\n"
                    "⚠️ Reminder: Answers provided are AI-generated based on available reference documents. Please verify with the official helpdesk or relevant officer before taking any formal action.")
        return (f"Assalamualaikum dan salam sejahtera{sapaan}! 😊 Saya SMARTAssist Hub KPM Support Agent. Saya di sini untuk membantu anda dengan sebarang isu berkaitan sistem KPM seperti EMIS, DELIMa, DTPCare, SK@S dan lain-lain. Apa yang boleh saya bantu hari ini?\n\n"
                "⚠️ Peringatan: Jawapan yang diberikan adalah hasil AI berdasarkan dokumen rujukan yang ada. Sila sahkan dengan helpdesk rasmi atau pegawai berkaitan sebelum mengambil sebarang tindakan formal.")

    session = _get_session(session_id)
    session["history_queries"].append(query)
    _save_session(session_id, session)

    docs = _retrieve_docs(query, history)
    doc_context = _format_doc_context(docs)

    session_context = "\n\nSesi sedang berjalan. JANGAN ulang sapaan perkenalan. Terus jawab soalan pengguna secara langsung dan profesional."
    lang_note = "\n\nIMPORTANT: The user has selected English. You MUST respond entirely in English. Do not use Malay." if lang == "en" else ""

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT + session_context + lang_note + doc_context},
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
    from backend.session_store import get_store
    get_store().delete_ns(session_id, _NS)
