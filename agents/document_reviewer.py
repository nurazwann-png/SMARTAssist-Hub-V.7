"""Document Reviewer Agent — Section 5: Editor / Proofreader."""

import json
import re
from backend.deepseek_client import chat_completion

_sessions: dict[str, dict] = {}

_SYSTEM_PROMPT = """Anda ialah editor dan penyemak bahasa berpengalaman dalam SMARTAssist Hub.
Anda menyemak surat rasmi, memo, dan laporan sebelum ia dimuktamadkan.

CARA KERJA:
1. Semak seperti editor teliti — periksa tatabahasa, ejaan, konsistensi nada, dan pematuhan format rasmi
2. Semak dalam kedua-dua Bahasa Malaysia dan Bahasa Inggeris
3. JANGAN tulis semula niat penulis — JANGAN tambah kandungan baru yang pengguna tidak minta
4. TANDAKAN isu sahaja — biar pengguna yang membuat keputusan untuk membetulkan
5. Hanya betulkan jika pengguna secara eksplisit minta anda membetulkan

SEMAKAN FORMAT RASMI KPM:
- Rujukan (Ruj. Kami) — pastikan ada dan format betul
- Tarikh — format Bahasa Malaysia rasmi (contoh: 10 Julai 2026)
- Perkara — huruf besar, jelas
- Gelaran kehormatan — Yang Berhormat, Tuan/Puan, Dato', Datuk, dll
- "MALAYSIA MADANI" dan "BERKHIDMAT UNTUK NEGARA" — wajib ada dalam surat rasmi KPM
- Penutup — "Saya yang menjalankan amanah," untuk surat rasmi
- Salinan kepada (s.k.) — jika berkaitan
- Font Arial, saiz 11, Justify — nyatakan sebagai peringatan format

SEMAKAN PLACEHOLDER:
- Pastikan TIADA [PLACEHOLDER], {{CREATIVE:slot}}, atau {{DYNAMIC_LIST:name}} yang belum diisi
- Ini adalah semakan kritikal — setiap placeholder yang ditemui adalah ISU WAJIB BETULKAN

FORMAT MAKLUM BALAS — balas HANYA dalam JSON:
{
  "summary": "Ringkasan keseluruhan semakan dalam 1-2 ayat",
  "score": "A/B/C/D (A=cemerlang, B=baik dengan isu kecil, C=perlu pembetulan, D=banyak isu kritikal)",
  "issues": [
    {
      "severity": "WAJIB_BETULKAN atau CADANGAN",
      "category": "Tatabahasa/Ejaan/Format/Nada/Placeholder/Kandungan",
      "location": "Bahagian/perenggan di mana isu ditemui",
      "issue": "Penerangan isu",
      "suggestion": "Cadangan pembetulan"
    }
  ],
  "corrected_document": null,
  "message": "Mesej kepada pengguna"
}

PENTING:
- "corrected_document" hanya diisi jika pengguna MINTA anda betulkan dokumen tersebut
- Jika tiada isu ditemui, kembalikan senarai issues kosong dengan mesej positif
- Sentiasa beri pujian untuk aspek yang baik dalam dokumen
- Jika pengguna hanya bertanya soalan umum tentang semakan (tanpa dokumen), jelaskan cara menggunakan agen ini"""

_REVIEW_TRIGGER_PROMPT = """Sila semak dokumen berikut dan berikan maklum balas mengikut format yang ditetapkan.

DOKUMEN UNTUK DISEMAK:
---
{document}
---

Jenis dokumen: {doc_type}
"""


def _get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "reviewed_docs": [],
            "last_review": None,
            "uploaded_doc": None,
            "uploaded_doc_type": None,
            "uploaded_filename": None,
        }
    return _sessions[session_id]


def set_uploaded_document(session_id: str, text: str, filename: str, doc_type: str = "Dokumen"):
    session = _get_session(session_id)
    session["uploaded_doc"] = text
    session["uploaded_doc_type"] = doc_type
    session["uploaded_filename"] = filename


def get_uploaded_document(session_id: str) -> tuple[str | None, str, str | None]:
    session = _sessions.get(session_id)
    if not session:
        return None, "Dokumen", None
    return session.get("uploaded_doc"), session.get("uploaded_doc_type", "Dokumen"), session.get("uploaded_filename")


def _detect_document_in_query(query: str) -> str | None:
    """Check if the query itself contains a document to review."""
    doc_markers = [
        "Ruj. Kami", "Tarikh :", "Tuan/Puan", "MALAYSIA MADANI",
        "ONE PAGE REPORT", "NAMA PROGRAM", "BUTIRAN PERLAKSANAAN",
        "Yang Berusaha", "Saya yang menjalankan amanah",
        "DISEDIAKAN OLEH", "CADANGAN / TINDAKAN",
    ]
    marker_count = sum(1 for m in doc_markers if m in query)
    if marker_count >= 2:
        return query
    return None


def _get_linked_document(session_id: str) -> tuple[str | None, str]:
    """Try to get document from letter_generator or report_generator sessions."""
    try:
        from agents.letter_generator import get_document as lg_get_doc
        doc = lg_get_doc(session_id)
        if doc:
            return doc, "Surat Rasmi"
    except (ImportError, Exception):
        pass

    try:
        from agents.report_generator import get_document as rg_get_doc
        doc = rg_get_doc(session_id)
        if doc:
            return doc, "Laporan Satu Muka Surat"
    except (ImportError, Exception):
        pass

    return None, ""


def _check_placeholders(text: str) -> list[dict]:
    """Pre-check for unfilled placeholders before sending to LLM."""
    issues = []
    patterns = [
        (r'\[PLACEHOLDER\]', '[PLACEHOLDER]'),
        (r'\{\{CREATIVE:[^}]+\}\}', '{{CREATIVE:...}}'),
        (r'\{\{DYNAMIC_LIST:[^}]+\}\}', '{{DYNAMIC_LIST:...}}'),
    ]
    for pattern, label in patterns:
        matches = re.findall(pattern, text)
        if matches:
            issues.append({
                "severity": "WAJIB_BETULKAN",
                "category": "Placeholder",
                "location": "Seluruh dokumen",
                "issue": f"Ditemui {len(matches)} placeholder '{label}' yang belum diisi",
                "suggestion": "Gantikan semua placeholder dengan maklumat sebenar",
            })
    return issues


def handle(query: str, history: list[dict] | None = None, session_id: str = "default") -> str:
    if query == '__INTRO__':
        return "Assalamualaikum dan selamat datang! 📝 Saya Semakan Dokumen Agent. Muat naik dokumen PDF atau Word tuan/puan menggunakan butang 📎, atau tampal teks dokumen terus ke sini. Saya akan menyemak tatabahasa, format, ejaan dan pematuhan format rasmi KPM. Dokumen apa yang ingin tuan/puan semak hari ini?"

    session = _get_session(session_id)

    # Prioritise: uploaded file > embedded in query > linked from other agent
    uploaded_doc, uploaded_type, uploaded_filename = get_uploaded_document(session_id)
    embedded_doc = _detect_document_in_query(query)
    linked_doc, doc_type = _get_linked_document(session_id)

    document = None
    if uploaded_doc:
        document = uploaded_doc
        doc_type = uploaded_type or "Dokumen"
    elif embedded_doc:
        document = embedded_doc
        doc_type = doc_type or "Dokumen"
    elif linked_doc:
        document = linked_doc
        review_keywords = ["semak", "review", "proofread", "periksa", "check"]
        if any(kw in query.lower() for kw in review_keywords):
            pass
        else:
            document = None

    if document and "betulkan" in query.lower() or document and "perbaiki" in query.lower():
        extra_instruction = "\n\nPengguna minta dokumen ini DIBETULKAN. Sila isi 'corrected_document' dengan versi yang telah diperbaiki."
    else:
        extra_instruction = ""

    if document:
        placeholder_issues = _check_placeholders(document)

        review_prompt = _REVIEW_TRIGGER_PROMPT.format(
            document=document,
            doc_type=doc_type or "Dokumen",
        ) + extra_instruction

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
        ]
        if history:
            for msg in history[-4:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": review_prompt})

        try:
            raw = chat_completion(messages=messages, temperature=0.3, max_tokens=3000)
        except RuntimeError as e:
            return json.dumps({
                "message": f"Ralat semasa menyemak dokumen. Sila cuba lagi.\n{e}",
                "review_failed": True,
            }, ensure_ascii=False)

        parsed = _try_parse_json(raw)
        if parsed:
            if placeholder_issues:
                existing = parsed.get("issues", [])
                parsed["issues"] = placeholder_issues + existing
            session["last_review"] = parsed
            session["reviewed_docs"].append(doc_type)
            return json.dumps(parsed, ensure_ascii=False)

        return raw
    else:
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
        ]
        if history:
            for msg in history[-6:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": query})

        try:
            return chat_completion(messages=messages, temperature=0.3, max_tokens=2000)
        except RuntimeError as e:
            return f"Ralat semakan dokumen: {e}"


def get_last_review(session_id: str) -> dict | None:
    session = _sessions.get(session_id)
    if session:
        return session.get("last_review")
    return None


def clear_session(session_id: str):
    _sessions.pop(session_id, None)


def _try_parse_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        end = next((i for i, l in enumerate(lines) if l.strip() == "```"), len(lines))
        text = "\n".join(lines[:end])
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except (json.JSONDecodeError, ValueError):
                pass
    return None
