"""Letter Generator Agent — Section 2: Personal Assistant for Official Correspondence."""

import json
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from backend.deepseek_client import chat_completion

# ── Document field schemas ──

SURAT_FIELDS = {
    "doc_type": "surat",
    "fields": [
        {"key": "rujukan", "label": "Nombor Rujukan", "example": "PPD.XXX/XXX/XX/XX ( )"},
        {"key": "tarikh", "label": "Tarikh", "example": "10 Julai 2026"},
        {"key": "penerima_nama", "label": "Nama Penerima", "example": "YBhg. Dato'/Tuan/Puan"},
        {"key": "penerima_jawatan", "label": "Jawatan Penerima", "example": "Pengarah Pendidikan Negeri"},
        {"key": "penerima_organisasi", "label": "Nama Organisasi Penerima", "example": "Jabatan Pendidikan Negeri Selangor"},
        {"key": "penerima_alamat", "label": "Alamat Penerima", "example": "Aras 5, Blok E, 40000 Shah Alam, Selangor"},
        {"key": "tajuk", "label": "Perkara / Tajuk Surat", "example": "Permohonan Peruntukan Khas"},
        {"key": "isi", "label": "Isi Kandungan Utama", "example": "Penerangan tujuan surat"},
        {"key": "penandatangan_nama", "label": "Nama Penandatangan", "example": "Ahmad bin Ali"},
        {"key": "penandatangan_jawatan", "label": "Jawatan Penandatangan", "example": "Pegawai Pendidikan Daerah"},
        {"key": "salinan_kepada", "label": "Salinan Kepada (s.k.)", "example": "Pengarah JPN, Ketua Unit ICT", "optional": True},
    ],
}

MEMO_FIELDS = {
    "doc_type": "memo",
    "fields": [
        {"key": "rujukan", "label": "Nombor Rujukan", "example": "PPD.BIL(M)200-1/1"},
        {"key": "tarikh", "label": "Tarikh", "example": "10 Julai 2026"},
        {"key": "kepada", "label": "Kepada (Penerima)", "example": "Semua Guru Besar"},
        {"key": "daripada", "label": "Daripada (Pengirim)", "example": "Pegawai Pendidikan Daerah"},
        {"key": "tajuk", "label": "Perkara", "example": "Mesyuarat Pengurusan Bil. 3/2026"},
        {"key": "isi", "label": "Isi Kandungan", "example": "Butiran memo"},
    ],
}

SHARED_KEYS = {"rujukan", "tarikh", "tajuk", "isi"}

_SYSTEM_PROMPT_TEMPLATE = """Anda ialah pembantu peribadi profesional dalam SMARTAssist Hub.
Tugas anda: membantu pengguna menulis surat rasmi dan memo dalaman mengikut format KPM/Pekeliling Am.

CARA KERJA:
1. Kenal pasti jenis dokumen (surat rasmi atau memo dalaman)
2. Tanya maklumat yang diperlukan SATU DEMI SATU — HANYA SATU SOALAN setiap giliran
3. JANGAN terima semua maklumat sekaligus walaupun pengguna memberikan banyak maklumat dalam satu mesej — proses maklumat yang diberi, simpan dalam fields_collected, kemudian tanya field seterusnya yang belum diisi
4. Gunakan maklumat yang diberi untuk menjana dokumen lengkap apabila semua field dipenuhi
5. Pastikan tiada [PLACEHOLDER] yang belum diisi sebelum dokumen siap

URUTAN SOALAN (ikut susunan ini):
- Surat: rujukan → tarikh → penerima_nama → penerima_jawatan → penerima_organisasi → penerima_alamat → tajuk → (jana isi secara automatik) → penandatangan_nama → penandatangan_jawatan → salinan_kepada (pilihan)
- Memo: rujukan → tarikh → kepada → daripada → tajuk → (jana isi secara automatik)

GAYA:
- Bertanya seperti pembantu peribadi yang cekap — sopan, ringkas, dan spesifik
- HANYA tanya SATU field pada satu masa. Contoh: "Apakah nombor rujukan surat ini?"
- Jika pengguna beri beberapa maklumat sekaligus, terima semua yang diberi, kemudian tanya field seterusnya yang masih kosong
- Gunakan Bahasa Malaysia rasmi
- Format dokumen mengikut konvensyen rasmi KPM

TARIKH SEMASA: {current_date}
- Gunakan tarikh semasa sebagai rujukan. Tahun semasa ialah {current_year}.
- Jangan persoalkan tarikh yang pengguna berikan selagi formatnya betul.

FORMAT OUTPUT — balas HANYA dalam JSON:
{
  "phase": 0-4,
  "doc_type": "surat|memo|null",
  "message": "Mesej kepada pengguna",
  "field_asking": "nama field yang sedang ditanya (atau null)",
  "fields_collected": {"key": "value", ...},
  "document_preview": "Teks dokumen lengkap (hanya pada phase 3-4)",
  "validation_errors": ["Senarai ralat jika ada"],
  "ready_to_save": true/false
}

PHASES:
- Phase 0: Kenal pasti jenis dokumen (surat/memo). Jika pengguna minta tukar jenis, pindahkan field yang sama.
- Phase 1: Kumpul maklumat secara berperingkat (satu field setiap giliran). JANGAN tanya "isi" — isi akan dijana automatik.
- Phase 2: JANA ISI KANDUNGAN SECARA AUTOMATIK berdasarkan tajuk dan semua maklumat yang dikumpul. Tulis isi surat/memo dalam gaya rasmi KPM — bernombor perenggan (2., 3., 4. dst), bahasa formal, lengkap dan profesional. Simpan hasil dalam fields_collected dengan key "isi". Jika maklumat tidak mencukupi untuk menjana isi yang bermakna (cth: tajuk terlalu umum), tanya pengguna soalan spesifik untuk mendapat konteks tambahan (cth: "Boleh nyatakan tujuan utama dan jumlah yang dipohon?"). JANGAN minta pengguna tulis isi sendiri.
- Phase 3: Tunjukkan pratonton dokumen lengkap — SEMAK tiada [PLACEHOLDER] kekal
- Phase 4: Dokumen disahkan dan sedia untuk dimuat turun / dihantar emel

FIELD KEYS YANG WAJIB DIGUNAKAN (guna key tepat ini dalam fields_collected):
Untuk surat: rujukan, tarikh, penerima_nama, penerima_jawatan, penerima_organisasi, penerima_alamat, tajuk, isi, penandatangan_nama, penandatangan_jawatan, salinan_kepada
Untuk memo: rujukan, tarikh, kepada, daripada, tajuk, isi

PENTING:
- Jangan reka maklumat PERIBADI (nama, jawatan, alamat) — tanya pengguna
- ISI KANDUNGAN surat/memo WAJIB dijana secara automatik oleh anda berdasarkan tajuk dan konteks. JANGAN tanya pengguna untuk menulis isi.
- Jika tajuk terlalu umum dan anda perlukan konteks tambahan, tanya soalan spesifik (contoh: "Apakah jumlah peruntukan yang dipohon?" atau "Berapa buah sekolah yang terlibat?")
- Gunakan KEY TEPAT seperti senarai di atas dalam fields_collected (contoh: "penerima_nama", BUKAN "nama_penerima")
- Jika pengguna minta tukar dari surat ke memo (atau sebaliknya), pindahkan field yang sama (rujukan, tarikh, tajuk, isi)
- Pastikan JSON sah"""

_sessions: dict[str, dict] = {}


def _get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "phase": 0,
            "doc_type": None,
            "fields": {},
            "document": None,
        }
    return _sessions[session_id]


def _get_field_schema(doc_type: str) -> list[dict]:
    if doc_type == "memo":
        return MEMO_FIELDS["fields"]
    return SURAT_FIELDS["fields"]


def _find_missing_fields(doc_type: str, collected: dict) -> list[dict]:
    schema = _get_field_schema(doc_type)
    return [f for f in schema if not f.get("optional") and (f["key"] not in collected or not collected[f["key"]])]


def _has_placeholders(text: str) -> list[str]:
    patterns = [
        r'\[PLACEHOLDER\]',
        r'\{\{CREATIVE:[^}]+\}\}',
        r'\{\{DYNAMIC_LIST:[^}]+\}\}',
    ]
    found = []
    for p in patterns:
        found.extend(re.findall(p, text))
    return found


def _build_document(doc_type: str, fields: dict) -> str:
    if doc_type == "memo":
        return _build_memo(fields)
    return _build_surat(fields)


def _build_surat(f: dict) -> str:
    sk = f.get("salinan_kepada", "")
    sk_lines = ""
    if sk:
        items = [s.strip() for s in sk.split(",") if s.strip()]
        if items:
            sk_lines = "\n\ns.k.:\n" + "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))

    return f"""Ruj. Kami : {f.get('rujukan', '[PLACEHOLDER]')}
Tarikh : {f.get('tarikh', '[PLACEHOLDER]')}

{f.get('penerima_nama', '[PLACEHOLDER]')}
{f.get('penerima_jawatan', '[PLACEHOLDER]')}
{f.get('penerima_organisasi', '[PLACEHOLDER]')}
{f.get('penerima_alamat', '[PLACEHOLDER]')}

Tuan/Puan,

{f.get('tajuk', '[PLACEHOLDER]').upper()}

Dengan hormatnya perkara di atas adalah dirujuk.

{f.get('isi', '[PLACEHOLDER]')}

Sekian, terima kasih.

"MALAYSIA MADANI"
"BERKHIDMAT UNTUK NEGARA"

Saya yang menjalankan amanah,


({f.get('penandatangan_nama', '[PLACEHOLDER]').upper()})
{f.get('penandatangan_jawatan', '[PLACEHOLDER]')}""" + sk_lines


def _build_memo(f: dict) -> str:
    return f"""MEMO DALAMAN

Rujukan: {f.get('rujukan', '[PLACEHOLDER]')}
Tarikh: {f.get('tarikh', '[PLACEHOLDER]')}

Kepada: {f.get('kepada', '[PLACEHOLDER]')}
Daripada: {f.get('daripada', '[PLACEHOLDER]')}

PERKARA: {f.get('tajuk', '[PLACEHOLDER]')}

{f.get('isi', '[PLACEHOLDER]')}

Sekian, harap maklum.

"BERKHIDMAT UNTUK NEGARA"
"MALAYSIA MADANI" """


def handle(query: str, history: list[dict] | None = None, session_id: str = "default") -> str:
    if query == '__INTRO__':
        return "Assalamualaikum dan selamat datang! ✉️ Saya Penjana Surat Rasmi. Saya akan membantu tuan/puan menyediakan surat rasmi, memo dan surat siaran mengikut format KPM yang betul. Boleh beritahu saya apakah jenis surat yang perlu disediakan dan maklumat asasnya?"

    session = _get_session(session_id)

    _PATCH_KEYWORDS = {"kemaskini", "ubah", "ganti", "tukar", "edit", "update", "betulkan", "perbetulkan", "tukar kepada", "ubah suai"}
    query_lower = query.lower()
    if session.get("document") and any(kw in query_lower for kw in _PATCH_KEYWORDS):
        patch_prompt = f"""Dokumen semasa:
---
{session['document']}
---

Pengguna meminta perubahan berikut: {query}

Kembalikan HANYA dokumen yang telah dikemaskini dalam format JSON:
{{
  "phase": {session['phase']},
  "doc_type": "{session.get('doc_type', 'surat')}",
  "message": "Dokumen telah dikemaskini.",
  "document_preview": "<dokumen lengkap selepas perubahan>",
  "ready_to_save": true
}}"""
        now = datetime.now()
        date_str = now.strftime("%#d %B %Y") if os.name == "nt" else now.strftime("%-d %B %Y")
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.replace("{current_date}", date_str).replace("{current_year}", str(now.year))
        patch_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": patch_prompt}]
        try:
            raw = chat_completion(messages=patch_messages, temperature=0.2, max_tokens=3000)
            parsed = _try_parse_json(raw)
            if parsed and parsed.get("document_preview"):
                doc_text = parsed["document_preview"]
                session["document"] = doc_text
                parsed["ready_to_save"] = not _has_placeholders(doc_text)
                parsed["fields_status"] = {"collected": session["fields"], "missing": []}
                return json.dumps(parsed, ensure_ascii=False)
        except Exception:
            pass

    context_info = f"""
Status sesi semasa:
- Phase: {session['phase']}
- Jenis dokumen: {session['doc_type'] or 'belum ditentukan'}
- Field terkumpul: {json.dumps(session['fields'], ensure_ascii=False) if session['fields'] else 'tiada lagi'}
- Field belum diisi: {json.dumps([f['label'] for f in _find_missing_fields(session['doc_type'], session['fields'])], ensure_ascii=False) if session['doc_type'] else 'tentukan jenis dokumen dahulu'}
"""

    now = datetime.now()
    date_str = now.strftime("%#d %B %Y") if os.name == "nt" else now.strftime("%-d %B %Y")
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.replace("{current_date}", date_str).replace("{current_year}", str(now.year))

    messages = [
        {"role": "system", "content": system_prompt + context_info},
    ]
    if history:
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": query})

    try:
        raw = chat_completion(messages=messages, temperature=0.3, max_tokens=3000)
    except RuntimeError as e:
        return json.dumps({
            "phase": session["phase"],
            "message": f"Ralat menghubungi API. Sila cuba lagi.\n{e}",
            "ready_to_save": False,
        }, ensure_ascii=False)

    parsed = _try_parse_json(raw)
    if not parsed:
        return json.dumps({
            "phase": session["phase"],
            "message": raw,
            "ready_to_save": False,
        }, ensure_ascii=False)

    if parsed.get("doc_type") and parsed["doc_type"] in ("surat", "memo"):
        old_type = session["doc_type"]
        new_type = parsed["doc_type"]
        if old_type and old_type != new_type and session["fields"]:
            carried = {k: v for k, v in session["fields"].items() if k in SHARED_KEYS}
            session["fields"] = carried
        session["doc_type"] = new_type

    if parsed.get("fields_collected"):
        session["fields"].update(parsed["fields_collected"])

    if parsed.get("phase") is not None:
        session["phase"] = parsed["phase"]

    all_filled = session["doc_type"] and not _find_missing_fields(session["doc_type"], session["fields"])
    if session["doc_type"] and (session["phase"] >= 3 or all_filled):
        if all_filled:
            session["phase"] = max(session["phase"], 3)
            parsed["phase"] = session["phase"]
        doc_text = _build_document(session["doc_type"], session["fields"])
        placeholders = _has_placeholders(doc_text)
        parsed["document_preview"] = doc_text
        if placeholders:
            parsed["validation_errors"] = [f"Masih ada placeholder yang belum diisi: {', '.join(placeholders)}"]
            parsed["ready_to_save"] = False
        else:
            parsed["ready_to_save"] = True
            session["document"] = doc_text

    parsed["fields_status"] = {
        "collected": session["fields"],
        "missing": [f["label"] for f in _find_missing_fields(session["doc_type"], session["fields"])] if session["doc_type"] else [],
    }

    return json.dumps(parsed, ensure_ascii=False)


def get_document(session_id: str) -> str | None:
    session = _sessions.get(session_id)
    if session and session.get("document"):
        return session["document"]
    return None


def build_docx(session_id: str) -> bytes | None:
    doc_text = get_document(session_id)
    if not doc_text:
        return None

    from docx import Document as DocxDocument
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import io

    doc = DocxDocument()
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Arial"
    font.size = Pt(11)
    pf = style.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = 1.0
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for section in doc.sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.17)
        section.right_margin = Cm(2.54)

    # Insert active letterhead at top
    try:
        from backend.letterhead_store import get_active_path_by_type
        lh_path = get_active_path_by_type("letterhead")
        if lh_path:
            lh_para = doc.add_paragraph()
            lh_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            lh_para.paragraph_format.space_after = Pt(6)
            run = lh_para.add_run()
            run.add_picture(str(lh_path), width=Cm(16))
            doc.add_paragraph("").paragraph_format.space_after = Pt(0)
    except Exception:
        pass

    lines = doc_text.split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            doc.add_paragraph("")
            continue

        para = doc.add_paragraph()
        para.paragraph_format.space_after = Pt(0)
        para.paragraph_format.space_before = Pt(0)

        is_bold = False
        if stripped.startswith(("Ruj. Kami", "Tarikh")):
            para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        elif stripped.startswith('"') and stripped.endswith('"'):
            is_bold = True
        elif stripped.startswith("s.k.:"):
            is_bold = True
        elif stripped == stripped.upper() and len(stripped) > 5 and stripped[0].isalpha():
            is_bold = True

        run = para.add_run(stripped)
        run.font.size = Pt(11)
        run.font.name = "Arial"
        if is_bold:
            run.bold = True

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def get_session_info(session_id: str) -> dict | None:
    return _sessions.get(session_id)


def send_email(session_id: str, to_email: str, subject: str) -> dict:
    document = get_document(session_id)
    if not document:
        return {"ok": False, "error": "Tiada dokumen yang sedia untuk dihantar. Sila lengkapkan dokumen dahulu."}

    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_APP_PASSWORD")

    if not sender_email or not sender_password:
        return {"ok": False, "error": "Konfigurasi emel belum ditetapkan. Sila tetapkan SENDER_EMAIL dan SENDER_APP_PASSWORD dalam .env."}

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(document, "plain", "utf-8"))

        session = _sessions.get(session_id, {})
        doc_type = session.get("doc_type", "dokumen")
        filename = f"{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        attachment = MIMEBase("application", "octet-stream")
        attachment.set_payload(document.encode("utf-8"))
        encoders.encode_base64(attachment)
        attachment.add_header("Content-Disposition", f"attachment; filename={filename}")
        msg.attach(attachment)

        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)

        return {"ok": True, "message": f"Emel berjaya dihantar ke {to_email}."}
    except Exception as e:
        return {"ok": False, "error": f"Gagal menghantar emel: {e}"}


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
