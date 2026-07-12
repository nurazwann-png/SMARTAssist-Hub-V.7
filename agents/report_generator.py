"""Report Generator Agent — Section 4: Bureaucratic Reporting Specialist."""

import json
import os
import re
import io
from datetime import datetime
from backend.deepseek_client import chat_completion

# ── Field schema ──

REPORT_FIELDS = [
    {"key": "nama_program", "label": "Nama Program", "example": "Bengkel ICT Guru Besar Siri 2/2026"},
    {"key": "tarikh_program", "label": "Tarikh Program", "example": "10 Julai 2026"},
    {"key": "hari", "label": "Hari", "example": "Khamis"},
    {"key": "masa", "label": "Masa Program", "example": "8.00 pagi - 5.00 petang"},
    {"key": "organisasi", "label": "Nama Organisasi", "example": "Pejabat Pendidikan Daerah Dalat"},
    {"key": "pegawai", "label": "Pegawai Yang Terlibat", "example": "Ahmad bin Ali, Siti binti Hassan, Razak bin Omar"},
    {"key": "objektif", "label": "Objektif Program", "example": "Meningkatkan kemahiran ICT guru besar"},
    {"key": "rumusan", "label": "Rumusan / Laporan Ringkas", "example": "Program berjalan lancar dengan 45 peserta"},
    {"key": "cadangan", "label": "Cadangan / Tindakan Susulan", "example": "Mengadakan bengkel susulan pada bulan hadapan"},
    {"key": "penyedia_nama", "label": "Nama Penyedia Laporan", "example": "Mohd Razali bin Ibrahim"},
    {"key": "penyedia_jawatan", "label": "Jawatan Penyedia", "example": "Pegawai Pendidikan Daerah"},
    {"key": "tarikh_disediakan", "label": "Tarikh Disediakan", "example": "11 Julai 2026"},
    {"key": "pengesah_nama", "label": "Nama Pengesah Laporan", "example": "Dato' Ahmad bin Yusof"},
    {"key": "pengesah_jawatan", "label": "Jawatan Pengesah", "example": "Pegawai Pendidikan Daerah Kanan"},
]

AUTO_GENERATE_KEYS = {"rumusan", "cadangan"}

_SYSTEM_PROMPT_TEMPLATE = """Anda ialah pakar laporan birokrasi dalam SMARTAssist Hub.
Tugas anda: membantu pengguna menyediakan laporan satu muka surat (One Page Report) dalam format rasmi PPD/KPM.

CARA KERJA:
1. Tanya maklumat yang diperlukan SATU DEMI SATU — HANYA SATU SOALAN setiap giliran
2. Jika pengguna beri beberapa maklumat sekaligus, terima semua yang diberi, kemudian tanya field seterusnya yang masih kosong
3. JANGAN tanya "rumusan" dan "cadangan" — anda WAJIB menjana kedua-duanya secara automatik berdasarkan maklumat program yang dikumpul
4. Jika maklumat tidak mencukupi untuk menjana rumusan/cadangan yang bermakna, tanya soalan spesifik (cth: "Berapa ramai peserta yang hadir?" atau "Apakah aktiviti utama yang dijalankan?")

URUTAN SOALAN:
nama_program → tarikh_program → hari → masa → organisasi → pegawai → objektif → (jana rumusan & cadangan automatik) → penyedia_nama → penyedia_jawatan → tarikh_disediakan → pengesah_nama → pengesah_jawatan

GAYA:
- Formal, tiada hiasan, seperti pegawai kerajaan yang berpengalaman
- Gunakan Bahasa Malaysia rasmi
- HANYA tanya SATU field pada satu masa
- Rumusan dan cadangan dijana dalam gaya laporan rasmi — perenggan bernombor, bahasa formal

TARIKH SEMASA: {current_date}
Tahun semasa ialah {current_year}. Jangan persoalkan tarikh yang pengguna berikan.

FORMAT OUTPUT — balas HANYA dalam JSON:
{{
  "phase": 0-3,
  "message": "Mesej kepada pengguna",
  "field_asking": "nama field yang sedang ditanya (atau null)",
  "fields_collected": {{"key": "value", ...}},
  "document_preview": "Teks laporan lengkap (hanya pada phase 2-3)",
  "validation_errors": ["Senarai ralat jika ada"],
  "ready_to_save": true/false
}}

PHASES:
- Phase 0: Pengenalan — sahkan pengguna mahu buat One Page Report
- Phase 1: Kumpul maklumat secara berperingkat. JANGAN tanya rumusan dan cadangan.
- Phase 2: Jana rumusan dan cadangan secara automatik, tunjukkan pratonton laporan lengkap. Selepas itu tanya penyedia_nama, penyedia_jawatan, tarikh_disediakan, pengesah_nama, pengesah_jawatan jika belum ada.
- Phase 3: Laporan disahkan dan sedia untuk dimuat turun

FIELD KEYS WAJIB (guna key tepat ini dalam fields_collected):
nama_program, tarikh_program, hari, masa, organisasi, pegawai, objektif, rumusan, cadangan, penyedia_nama, penyedia_jawatan, tarikh_disediakan, pengesah_nama, pengesah_jawatan

PENTING:
- Jangan reka maklumat peribadi — tanya pengguna
- RUMUSAN dan CADANGAN WAJIB dijana oleh anda secara automatik berdasarkan nama program, objektif, dan maklumat lain
- Gunakan KEY TEPAT seperti senarai di atas dalam fields_collected
- Pastikan JSON sah"""

_sessions: dict[str, dict] = {}


def _get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "phase": 0,
            "fields": {},
            "document": None,
        }
    return _sessions[session_id]


def _find_missing_fields(collected: dict) -> list[dict]:
    return [f for f in REPORT_FIELDS if f["key"] not in collected or not collected[f["key"]]]


def _has_placeholders(text: str) -> list[str]:
    patterns = [r'\[PLACEHOLDER\]', r'\{\{CREATIVE:[^}]+\}\}', r'\{\{DYNAMIC_LIST:[^}]+\}\}']
    found = []
    for p in patterns:
        found.extend(re.findall(p, text))
    return found


def _build_report(f: dict) -> str:
    pegawai = f.get("pegawai", "[PLACEHOLDER]")
    if isinstance(pegawai, list):
        pegawai_lines = "\n".join(f"{i+1}) {p.strip()}" for i, p in enumerate(pegawai))
    else:
        items = [p.strip() for p in pegawai.split(",") if p.strip()]
        pegawai_lines = "\n".join(f"{i+1}) {p}" for i, p in enumerate(items)) if items else "[PLACEHOLDER]"

    objektif = f.get("objektif", "[PLACEHOLDER]")
    if isinstance(objektif, list):
        objektif_lines = "\n".join(f"{i+1}) {o.strip()}" for i, o in enumerate(objektif))
    else:
        items = [o.strip() for o in objektif.split(",") if o.strip()]
        objektif_lines = "\n".join(f"{i+1}) {o}" for i, o in enumerate(items)) if items else objektif

    return f"""ONE PAGE REPORT

NAMA PROGRAM
{f.get('nama_program', '[PLACEHOLDER]')}

BUTIRAN PERLAKSANAAN
Tarikh      : {f.get('tarikh_program', '[PLACEHOLDER]')}
Hari        : {f.get('hari', '[PLACEHOLDER]')}
Masa        : {f.get('masa', '[PLACEHOLDER]')}
Organisasi  : {f.get('organisasi', '[PLACEHOLDER]')}

PEGAWAI YANG TERLIBAT
{pegawai_lines}

OBJEKTIF
{objektif_lines}

RUMUSAN / LAPORAN
{f.get('rumusan', '[PLACEHOLDER]')}

CADANGAN / TINDAKAN
{f.get('cadangan', '[PLACEHOLDER]')}

DISEDIAKAN OLEH                          DISAHKAN OLEH

............................................................    ............................................................
NAMA    : {f.get('penyedia_nama', '[PLACEHOLDER]')}              NAMA    : {f.get('pengesah_nama', '[PLACEHOLDER]')}
JAWATAN : {f.get('penyedia_jawatan', '[PLACEHOLDER]')}           JAWATAN : {f.get('pengesah_jawatan', '[PLACEHOLDER]')}
TARIKH  : {f.get('tarikh_disediakan', '[PLACEHOLDER]')}"""


def handle(query: str, history: list[dict] | None = None, session_id: str = "default") -> str:
    if query == '__INTRO__':
        return "Assalamualaikum dan selamat datang! 📋 Saya Penjana Laporan. Saya sedia membantu tuan/puan menjana laporan satu muka surat (One Page Report) dalam format rasmi PPD/KPM. Boleh beritahu saya nama program atau aktiviti yang ingin dilaporkan?"

    session = _get_session(session_id)

    _PATCH_KEYWORDS = {"kemaskini", "ubah", "ganti", "tukar", "edit", "update", "betulkan", "perbetulkan", "ubah suai"}
    query_lower = query.lower()
    if session.get("document") and any(kw in query_lower for kw in _PATCH_KEYWORDS):
        patch_prompt = f"""Laporan semasa:
---
{session['document']}
---

Pengguna meminta perubahan berikut: {query}

Kembalikan HANYA laporan yang telah dikemaskini dalam format JSON:
{{
  "phase": {session['phase']},
  "message": "Laporan telah dikemaskini.",
  "document_preview": "<laporan lengkap selepas perubahan>",
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
                parsed["ready_to_save"] = not bool(_has_placeholders(doc_text))
                return json.dumps(parsed, ensure_ascii=False)
        except Exception:
            pass

    missing = _find_missing_fields(session["fields"])
    context_info = f"""
Status sesi semasa:
- Phase: {session['phase']}
- Field terkumpul: {json.dumps(session['fields'], ensure_ascii=False) if session['fields'] else 'tiada lagi'}
- Field belum diisi: {json.dumps([f['label'] for f in missing], ensure_ascii=False)}
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

    if parsed.get("fields_collected"):
        session["fields"].update(parsed["fields_collected"])

    if parsed.get("phase") is not None:
        session["phase"] = parsed["phase"]

    all_filled = not _find_missing_fields(session["fields"])
    if session["phase"] >= 2 or all_filled:
        if all_filled:
            session["phase"] = max(session["phase"], 2)
            parsed["phase"] = session["phase"]
        doc_text = _build_report(session["fields"])
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
        "missing": [f["label"] for f in _find_missing_fields(session["fields"])],
    }

    return json.dumps(parsed, ensure_ascii=False)


def get_document(session_id: str) -> str | None:
    session = _sessions.get(session_id)
    if session and session.get("document"):
        return session["document"]
    return None


def get_session_info(session_id: str) -> dict | None:
    return _sessions.get(session_id)


def build_docx(session_id: str) -> bytes | None:
    session = _sessions.get(session_id)
    if not session or not session.get("document"):
        return None

    f = session["fields"]

    from docx import Document as DocxDocument
    from docx.shared import Pt, Cm, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn, nsdecls
    from docx.oxml import parse_xml

    doc = DocxDocument()
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(11)
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.line_spacing = 1.0

    for section in doc.sections:
        section.top_margin = Cm(1.5)
        section.bottom_margin = Cm(1.5)
        section.left_margin = Cm(2.54)
        section.right_margin = Cm(2.54)

    def _run(para, text, bold=False, size=11, center=False):
        if center:
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = para.add_run(text)
        r.font.name = "Arial"
        r.font.size = Pt(size)
        r.bold = bold
        return r

    def _set_cell_border(cell, **kwargs):
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}>'
            + ''.join(f'<w:{edge} w:val="{v["val"]}" w:sz="{v["sz"]}" w:space="0" w:color="{v["color"]}"/>'
                      for edge, v in kwargs.items())
            + '</w:tcBorders>')
        tcPr.append(tcBorders)

    def _border_kwargs():
        b = {"val": "single", "sz": "4", "color": "000000"}
        return {"top": b, "bottom": b, "start": b, "end": b}

    def _shade_cell(cell, color="FFC000"):
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}"/>')
        cell._tc.get_or_add_tcPr().append(shading)

    # ── Header: letterhead image or fallback KPM text ──
    _lh_inserted = False
    try:
        from backend.letterhead_store import get_active_path_by_type
        _lh_path = get_active_path_by_type("logo")
        if _lh_path:
            lh_para = doc.add_paragraph()
            lh_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            lh_para.paragraph_format.space_after = Pt(6)
            lh_para.add_run().add_picture(str(_lh_path), width=Cm(16))
            _lh_inserted = True
    except Exception:
        pass

    if not _lh_inserted:
        h1 = doc.add_paragraph()
        h1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(h1, "KEMENTERIAN PENDIDIKAN MALAYSIA", bold=True, size=12, center=True)
        h2 = doc.add_paragraph()
        h2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(h2, f"{f.get('organisasi', 'Pejabat Pendidikan Daerah')}", bold=False, size=10, center=True)

    # Horizontal line
    line_para = doc.add_paragraph()
    line_para.paragraph_format.space_before = Pt(4)
    line_para.paragraph_format.space_after = Pt(8)
    pPr = line_para._p.get_or_add_pPr()
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="12" w:space="1" w:color="000000"/></w:pBdr>')
    pPr.append(pBdr)

    total_width = Cm(15.92)  # A4 - margins

    # ── Main table ──
    table = doc.add_table(rows=0, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    col_widths = [Cm(3.0), Cm(4.96), Cm(3.0), Cm(4.96)]

    def _add_full_row(text, bold=True, shading=None, center=True, min_height=None):
        row = table.add_row()
        cell = row.cells[0]
        cell.merge(row.cells[3])
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        if center:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(p, text, bold=bold)
        _set_cell_border(cell, **_border_kwargs())
        if shading:
            _shade_cell(cell, shading)
        if min_height:
            tr = row._tr
            trPr = tr.get_or_add_trPr()
            trHeight = parse_xml(f'<w:trHeight {nsdecls("w")} w:val="{min_height}" w:hRule="atLeast"/>')
            trPr.append(trHeight)
        return cell

    def _add_two_col_row(left_text, right_text, left_bold=True, right_bold=False, right_center=False, min_height=None):
        row = table.add_row()
        left_cell = row.cells[0]
        left_cell.merge(row.cells[1])
        right_cell = row.cells[2]
        right_cell.merge(row.cells[3])

        lp = left_cell.paragraphs[0]
        lp.paragraph_format.space_before = Pt(4)
        lp.paragraph_format.space_after = Pt(4)
        _run(lp, left_text, bold=left_bold)
        _set_cell_border(left_cell, **_border_kwargs())

        rp = right_cell.paragraphs[0]
        rp.paragraph_format.space_before = Pt(4)
        rp.paragraph_format.space_after = Pt(4)
        if right_center:
            rp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _run(rp, right_text, bold=right_bold)
        _set_cell_border(right_cell, **_border_kwargs())

        if min_height:
            tr = row._tr
            trPr = tr.get_or_add_trPr()
            trHeight = parse_xml(f'<w:trHeight {nsdecls("w")} w:val="{min_height}" w:hRule="atLeast"/>')
            trPr.append(trHeight)
        return left_cell, right_cell

    # Row 1: ONE PAGE REPORT
    _add_full_row("ONE PAGE REPORT", bold=True)

    # Row 2: NAMA PROGRAM + value
    _add_full_row("NAMA PROGRAM", bold=True)
    _add_full_row(f.get("nama_program", ""), bold=False)

    # Row 3: BUTIRAN PERLAKSANAAN header
    _add_full_row("BUTIRAN PERLAKSANAAN", bold=True)

    # Row 4: Tarikh | value | Hari | value
    row4 = table.add_row()
    cells4 = row4.cells
    for i, (label, val) in enumerate([
        ("Tarikh", f.get("tarikh_program", "")),
        ("Hari", f.get("hari", "")),
    ]):
        label_cell = cells4[i * 2]
        val_cell = cells4[i * 2 + 1]
        lp = label_cell.paragraphs[0]
        lp.paragraph_format.space_before = Pt(4)
        lp.paragraph_format.space_after = Pt(4)
        _run(lp, label, bold=False)
        _set_cell_border(label_cell, **_border_kwargs())

        vp = val_cell.paragraphs[0]
        vp.paragraph_format.space_before = Pt(4)
        vp.paragraph_format.space_after = Pt(4)
        _run(vp, val, bold=False)
        _set_cell_border(val_cell, **_border_kwargs())

    # Row 5: Masa | value | Nama Sekolah | value
    row5 = table.add_row()
    cells5 = row5.cells
    for i, (label, val) in enumerate([
        ("Masa", f.get("masa", "")),
        ("Nama Sekolah", f.get("organisasi", "")),
    ]):
        label_cell = cells5[i * 2]
        val_cell = cells5[i * 2 + 1]
        lp = label_cell.paragraphs[0]
        lp.paragraph_format.space_before = Pt(4)
        lp.paragraph_format.space_after = Pt(4)
        _run(lp, label, bold=False)
        _set_cell_border(label_cell, **_border_kwargs())

        vp = val_cell.paragraphs[0]
        vp.paragraph_format.space_before = Pt(4)
        vp.paragraph_format.space_after = Pt(4)
        _run(vp, val, bold=False)
        _set_cell_border(val_cell, **_border_kwargs())

    # Row 6: PEGAWAI YANG TERLIBAT header + numbered list
    _add_full_row("PEGAWAI YANG TERLIBAT", bold=True)
    pegawai = f.get("pegawai", "")
    if isinstance(pegawai, list):
        items = pegawai
    else:
        items = [p.strip() for p in pegawai.split(",") if p.strip()]
    pegawai_text = "\n".join(f"{i+1}) {p}" for i, p in enumerate(items)) if items else ""
    _add_full_row(pegawai_text, bold=False, center=False, min_height="800")

    # Row 7: OBJEKTIF header + numbered list
    _add_full_row("OBJEKTIF", bold=True)
    objektif = f.get("objektif", "")
    if isinstance(objektif, list):
        obj_items = objektif
    else:
        obj_items = [o.strip() for o in objektif.split(",") if o.strip()]
    objektif_text = "\n".join(f"{i+1}) {o}" for i, o in enumerate(obj_items)) if obj_items else objektif
    _add_full_row(objektif_text, bold=False, center=False, min_height="800")

    # Row 8: RUMUSAN/LAPORAN (left label, right content)
    _add_two_col_row(
        "RUMUSAN/LAPORAN",
        f.get("rumusan", ""),
        left_bold=True, right_bold=False,
        min_height="2000",
    )

    # Row 9: CADANGAN/TINDAKAN (left label, right content)
    _add_two_col_row(
        "CADANGAN/TINDAKAN",
        f.get("cadangan", ""),
        left_bold=True, right_bold=False,
        min_height="2000",
    )

    # Row 10: DISEDIAKAN OLEH | DISAHKAN OLEH header
    _add_two_col_row("DISEDIAKAN OLEH", "DISAHKAN OLEH", left_bold=True, right_bold=True, right_center=True, min_height=None)

    # Row 11: Signature blocks side by side
    sig_left = (
        f"............................................................\n"
        f"NAMA    : {f.get('penyedia_nama', '')}\n"
        f"JAWATAN : {f.get('penyedia_jawatan', '')}\n"
        f"TARIKH  : {f.get('tarikh_disediakan', '')}"
    )
    sig_right = (
        f"............................................................\n"
        f"NAMA    : {f.get('pengesah_nama', '')}\n"
        f"JAWATAN : {f.get('pengesah_jawatan', '')}"
    )
    _add_two_col_row(sig_left, sig_right, left_bold=False, min_height="1600")

    # Set column widths
    for row in table.rows:
        for idx, width in enumerate(col_widths):
            if idx < len(row.cells):
                row.cells[idx].width = width

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def send_email(session_id: str, to_email: str, subject: str) -> dict:
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    document = get_document(session_id)
    if not document:
        return {"ok": False, "error": "Tiada laporan yang sedia untuk dihantar."}

    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_APP_PASSWORD")
    if not sender_email or not sender_password:
        return {"ok": False, "error": "Konfigurasi emel belum ditetapkan."}

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(document, "plain", "utf-8"))

        filename = f"laporan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
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
