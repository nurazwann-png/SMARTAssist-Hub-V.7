"""Document Reviewer Agent — Section 5: Editor / Proofreader."""

import json
import re
from backend.deepseek_client import chat_completion

_NS = "reviewer"

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
- "corrected_document" WAJIB diisi dengan dokumen penuh yang telah diperbetulkan apabila pengguna meminta betulkan sebarang isu (contoh: "Betulkan isu ini...", "perbaiki", "betulkan", "fix")
- Jika "corrected_document" diisi, ia mestilah dokumen PENUH dan LENGKAP dengan semua pembetulan yang diminta
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
    from backend.session_store import get_store
    data = get_store().get_all(session_id, _NS)
    if not data:
        default = {
            "reviewed_docs": [],
            "last_review": None,
            "uploaded_doc": None,
            "uploaded_doc_type": None,
            "uploaded_filename": None,
        }
        get_store().set_all(session_id, _NS, default)
        return default
    return data


def _save_session(session_id: str, session: dict):
    from backend.session_store import get_store
    get_store().set_all(session_id, _NS, session)


def set_uploaded_document(session_id: str, text: str, filename: str, doc_type: str = "Dokumen", html: str | None = None):
    session = _get_session(session_id)
    session["uploaded_doc"] = text
    session["uploaded_doc_type"] = doc_type
    session["uploaded_filename"] = filename
    session["uploaded_doc_html"] = html
    _save_session(session_id, session)


def get_uploaded_html(session_id: str) -> str | None:
    session = _get_session(session_id)
    return session.get("uploaded_doc_html")


def get_uploaded_document(session_id: str) -> tuple[str | None, str, str | None]:
    session = _get_session(session_id)
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


def handle(query: str, history: list[dict] | None = None, session_id: str = "default", lang: str = "bm", user_name: str = "") -> str:
    sapaan = f", {user_name.split()[0]}" if user_name else ""
    if query == '__INTRO__':
        if lang == "en":
            return (f"Assalamualaikum and welcome{sapaan}! 📝 I am the Document Review Agent. Upload your PDF or Word document using the 📎 button, or paste the document text directly here. I will check grammar, format, spelling and compliance with official KPM format. Which document would you like to review today?\n\n"
                    "⚠️ Reminder: This review is AI-generated and may not catch every error. Please treat it as a guide only and perform a final check yourself before the document is used officially.")
        return (f"Assalamualaikum dan selamat datang{sapaan}! 📝 Saya Semakan Dokumen Agent. Muat naik dokumen PDF atau Word anda menggunakan butang 📎, atau tampal teks dokumen terus ke sini. Saya akan menyemak tatabahasa, format, ejaan dan pematuhan format rasmi KPM. Dokumen apa yang ingin anda semak hari ini?\n\n"
                "⚠️ Peringatan: Semakan ini dihasilkan oleh AI dan mungkin tidak mengesan semua kesilapan. Anggap ia sebagai panduan sahaja dan lakukan semakan akhir sendiri sebelum dokumen digunakan secara rasmi.")

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

    fix_keywords = ["betulkan", "perbaiki", "fix", "baiki", "correct"]
    if document and any(kw in query.lower() for kw in fix_keywords):
        extra_instruction = (
            f"\n\nARahan PEMBETULAN daripada pengguna: {query}\n\n"
            "WAJIB: Buat pembetulan yang diminta di atas pada dokumen. "
            "Isi 'corrected_document' dengan DOKUMEN PENUH yang telah diperbetulkan mengikut arahan tersebut. "
            "Jangan ubah bahagian lain dokumen yang tidak berkaitan dengan isu yang diminta."
        )
    else:
        extra_instruction = ""

    lang_note = "\n\nIMPORTANT: The user has selected English. You MUST respond entirely in English. All 'message', 'summary', 'issues', and other text fields in your JSON response must be in English." if lang == "en" else ""
    system_content = _SYSTEM_PROMPT + lang_note

    if document:
        placeholder_issues = _check_placeholders(document)

        review_prompt = _REVIEW_TRIGGER_PROMPT.format(
            document=document,
            doc_type=doc_type or "Dokumen",
        ) + extra_instruction

        messages = [
            {"role": "system", "content": system_content},
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
            _save_session(session_id, session)
            return json.dumps(parsed, ensure_ascii=False)

        return raw
    else:
        messages = [
            {"role": "system", "content": system_content},
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
    session = _get_session(session_id)
    return session.get("last_review")


def auto_review(document: str, doc_type: str, session_id: str = "default", lang: str = "bm") -> dict | None:
    """Called by other agents to automatically review a generated document."""
    placeholder_issues = _check_placeholders(document)

    lang_note = "\n\nIMPORTANT: The user has selected English. Respond in English." if lang == "en" else ""
    system_content = _SYSTEM_PROMPT + lang_note

    auto_note = "\n\nSemakan automatik selepas dokumen dijana. Berikan maklum balas ringkas dan fokus. Jika dokumen sudah baik, nyatakan dengan jelas."
    review_prompt = _REVIEW_TRIGGER_PROMPT.format(document=document, doc_type=doc_type) + auto_note

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": review_prompt},
    ]

    try:
        raw = chat_completion(messages=messages, temperature=0.2, max_tokens=1500)
    except RuntimeError:
        return None

    parsed = _try_parse_json(raw)
    if parsed:
        if placeholder_issues:
            existing = parsed.get("issues", [])
            parsed["issues"] = placeholder_issues + existing
        session = _get_session(session_id)
        session["last_review"] = parsed
        _save_session(session_id, session)
    return parsed


_AUTO_IMPROVE_SYSTEM = """Anda ialah editor kandungan dokumen rasmi kerajaan Malaysia yang pakar.
Tugas: perbaiki TEKS ISI KANDUNGAN yang dijana automatik oleh sistem, berdasarkan cadangan semakan.

PERATURAN WAJIB:
1. KEMBALIKAN HANYA teks field yang diperbaiki — JANGAN hasilkan dokumen penuh atau ubah template
2. JANGAN ubah maklumat yang diisi pengguna: nama, tarikh, rujukan, alamat, tajuk, nama penandatangan, jawatan
3. HANYA perbaiki field yang disenaraikan dalam "KANDUNGAN DIJANA SISTEM"
4. Jika cadangan memerlukan maklumat tambahan yang tiada, tandakan dalam "needs_info"
5. Pastikan bahasa kekal formal, profesional, dan mengikut piawaian KPM
6. Untuk field "isi" surat: tulis HANYA perenggan bernombor bermula dari "2.  ..." — JANGAN masukkan "Dengan hormatnya perkara di atas adalah dirujuk." kerana ia sudah ada dalam template
7. Untuk "rumusan" laporan: ringkasan pelaksanaan yang padat dan jelas
8. Untuk "cadangan" laporan: cadangan tindakan susulan yang konkrit

FORMAT BALAS HANYA dalam JSON:
{
  "improved_fields": {"isi": "teks isi yang diperbaiki", "rumusan": "...", "cadangan": "..."},
  "changes_applied": ["Perubahan 1 yang dilakukan pada field X", "Perubahan 2"],
  "changes_skipped": ["Cadangan X diskip — berkaitan template/maklumat pengguna/tiada maklumat cukup"],
  "needs_info": "Soalan kepada pengguna jika perlu maklumat tambahan, atau null"
}

PENTING: Hanya sertakan keys dalam "improved_fields" yang BENAR-BENAR diperbaiki."""

_AUTO_IMPROVE_PROMPT = """JENIS DOKUMEN: {doc_type}

KANDUNGAN DIJANA SISTEM (BOLEH DIPERBAIKI — kembalikan versi yang lebih baik):
{generated_fields}

KONTEKS DOKUMEN (maklumat pengguna untuk rujukan sahaja — JANGAN UBAH):
{user_fields}

CADANGAN SEMAKAN UNTUK DILAKSANAKAN:
{issues}

Perbaiki HANYA kandungan dalam "KANDUNGAN DIJANA SISTEM" berdasarkan cadangan di atas. Jangan hasilkan dokumen penuh."""


def auto_improve(
    doc_type: str,
    user_fields: dict,
    generated_field_keys: list[str],
    review: dict,
    lang: str = "bm",
) -> dict | None:
    """Improve only LLM-generated fields; document template is rebuilt separately."""
    issues = review.get("issues", [])
    if not issues:
        return None

    generated_fields = {k: v for k, v in user_fields.items() if k in generated_field_keys}
    if not generated_fields:
        return None

    preserved_fields = {k: v for k, v in user_fields.items() if k not in generated_field_keys}

    issues_text = "\n".join(
        f"- [{i['severity']}] {i.get('location','')}: {i['issue']} → Cadangan: {i.get('suggestion','')}"
        for i in issues
    )

    lang_note = "\n\nIMPORTANT: The user has selected English. Respond in English." if lang == "en" else ""
    system_content = _AUTO_IMPROVE_SYSTEM + lang_note

    prompt = _AUTO_IMPROVE_PROMPT.format(
        doc_type=doc_type,
        user_fields=json.dumps(preserved_fields, ensure_ascii=False, indent=2),
        generated_fields=json.dumps(generated_fields, ensure_ascii=False, indent=2),
        issues=issues_text,
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": prompt},
    ]

    try:
        raw = chat_completion(messages=messages, temperature=0.3, max_tokens=2000)
    except RuntimeError:
        return None

    return _try_parse_json(raw)


def clear_session(session_id: str):
    from backend.session_store import get_store
    get_store().delete_ns(session_id, _NS)


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
