"""Export data analysis results to PowerPoint and PDF."""

import io
import base64
from datetime import datetime


def _decode_chart_image(chart_image_b64: str | None) -> bytes | None:
    if not chart_image_b64:
        return None
    try:
        if "," in chart_image_b64:
            chart_image_b64 = chart_image_b64.split(",", 1)[1]
        return base64.b64decode(chart_image_b64)
    except Exception:
        return None


def build_pptx(data: dict, chart_image_b64: str | None = None) -> bytes:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    BG = RGBColor(0x0F, 0x17, 0x2A)
    TEXT = RGBColor(0xF1, 0xF5, 0xF9)
    ACCENT = RGBColor(0x3B, 0x82, 0xF6)
    MUTED = RGBColor(0x94, 0xA3, 0xB8)
    DARK2 = RGBColor(0x1E, 0x29, 0x3B)

    def set_bg(slide):
        fill = slide.background.fill
        fill.solid()
        fill.fore_color.rgb = BG

    def add_text(slide, left, top, width, height, text, size=14, color=TEXT, bold=False, align=PP_ALIGN.LEFT):
        txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = text
        p.font.size = Pt(size)
        p.font.color.rgb = color
        p.font.bold = bold
        p.alignment = align
        return tf

    # --- Title slide ---
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide)
    add_text(slide, 1, 2.5, 11, 1.2, "Analisis Data", size=36, color=ACCENT, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, 1, 3.8, 11, 0.6, data.get("message", ""), size=16, color=TEXT, align=PP_ALIGN.CENTER)
    add_text(slide, 1, 5.5, 11, 0.4, f"SMARTAssist Hub — {datetime.now().strftime('%d %B %Y')}", size=12, color=MUTED, align=PP_ALIGN.CENTER)

    # --- Penemuan slide ---
    penemuan = data.get("penemuan", [])
    if penemuan:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        set_bg(slide)
        add_text(slide, 0.8, 0.4, 5, 0.6, "\U0001F4CC Penemuan", size=24, color=ACCENT, bold=True)
        y = 1.2
        for item in penemuan:
            add_text(slide, 1.0, y, 11, 0.5, f"•  {item}", size=14, color=TEXT)
            y += 0.55

    # --- Tafsiran slide ---
    tafsiran = data.get("tafsiran", "")
    if tafsiran:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        set_bg(slide)
        add_text(slide, 0.8, 0.4, 5, 0.6, "\U0001F50D Tafsiran", size=24, color=ACCENT, bold=True)
        add_text(slide, 1.0, 1.2, 11, 4, tafsiran, size=14, color=TEXT)

    # --- Chart slide ---
    chart_bytes = _decode_chart_image(chart_image_b64)
    if chart_bytes:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        set_bg(slide)
        add_text(slide, 0.8, 0.4, 5, 0.6, "\U0001F4CA Carta", size=24, color=ACCENT, bold=True)
        chart_title = ""
        if data.get("chart") and data["chart"].get("title"):
            chart_title = data["chart"]["title"]
            add_text(slide, 0.8, 0.9, 11, 0.4, chart_title, size=14, color=TEXT, align=PP_ALIGN.CENTER)
        img_stream = io.BytesIO(chart_bytes)
        slide.shapes.add_picture(img_stream, Inches(1.5), Inches(1.4), Inches(10), Inches(5.5))

    # --- Table slide ---
    table_data = data.get("table")
    if table_data and table_data.get("headers") and table_data.get("rows"):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        set_bg(slide)
        add_text(slide, 0.8, 0.4, 5, 0.6, "\U0001F4CA Data", size=24, color=ACCENT, bold=True)

        headers = table_data["headers"]
        rows = table_data["rows"]
        num_cols = len(headers)
        num_rows = min(len(rows), 15) + 1
        col_width = min(11.5 / num_cols, 3.0)
        tbl_width = col_width * num_cols

        tbl = slide.shapes.add_table(num_rows, num_cols, Inches(0.8), Inches(1.2), Inches(tbl_width), Inches(0.4 * num_rows)).table

        for i, h in enumerate(headers):
            cell = tbl.cell(0, i)
            cell.text = str(h)
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(11)
                p.font.color.rgb = TEXT
                p.font.bold = True
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(0x33, 0x41, 0x55)

        for r_idx, row in enumerate(rows[:15]):
            for c_idx, val in enumerate(row):
                cell = tbl.cell(r_idx + 1, c_idx)
                cell.text = str(val)
                for p in cell.text_frame.paragraphs:
                    p.font.size = Pt(10)
                    p.font.color.rgb = TEXT
                cell.fill.solid()
                cell.fill.fore_color.rgb = DARK2 if r_idx % 2 == 0 else BG

    # --- Cadangan slide ---
    cadangan = data.get("cadangan", [])
    if cadangan:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        set_bg(slide)
        add_text(slide, 0.8, 0.4, 5, 0.6, "\U0001F4A1 Cadangan", size=24, color=ACCENT, bold=True)
        y = 1.2
        for item in cadangan:
            add_text(slide, 1.0, y, 11, 0.5, f"•  {item}", size=14, color=TEXT)
            y += 0.55

    # --- Amaran slide ---
    amaran = data.get("amaran", [])
    if amaran:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        set_bg(slide)
        add_text(slide, 0.8, 0.4, 5, 0.6, "⚠️ Amaran", size=24, color=RGBColor(0xEA, 0xB3, 0x08), bold=True)
        y = 1.2
        for item in amaran:
            add_text(slide, 1.0, y, 11, 0.5, f"•  {item}", size=14, color=RGBColor(0xEA, 0xB3, 0x08))
            y += 0.55

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def build_pdf(data: dict, chart_image_b64: str | None = None) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    styles = {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=20, textColor=HexColor("#3b82f6"), spaceAfter=12, alignment=TA_CENTER),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=11, textColor=HexColor("#94a3b8"), spaceAfter=20, alignment=TA_CENTER),
        "heading": ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=14, textColor=HexColor("#3b82f6"), spaceBefore=16, spaceAfter=8),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=11, textColor=HexColor("#1e293b"), spaceAfter=6, leading=16),
        "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=11, textColor=HexColor("#1e293b"), spaceAfter=4, leftIndent=20, leading=16),
        "warning": ParagraphStyle("warning", fontName="Helvetica", fontSize=11, textColor=HexColor("#b45309"), spaceAfter=4, leftIndent=20, leading=16),
    }

    elements = []

    elements.append(Paragraph("Analisis Data", styles["title"]))
    elements.append(Paragraph(f"SMARTAssist Hub — {datetime.now().strftime('%d %B %Y')}", styles["subtitle"]))

    msg = data.get("message", "")
    if msg:
        elements.append(Paragraph(msg, styles["body"]))
        elements.append(Spacer(1, 8))

    penemuan = data.get("penemuan", [])
    if penemuan:
        elements.append(Paragraph("\U0001F4CC Penemuan", styles["heading"]))
        for p in penemuan:
            elements.append(Paragraph(f"•  {p}", styles["bullet"]))

    tafsiran = data.get("tafsiran", "")
    if tafsiran:
        elements.append(Paragraph("\U0001F50D Tafsiran", styles["heading"]))
        elements.append(Paragraph(tafsiran, styles["body"]))

    # --- Chart image ---
    chart_bytes = _decode_chart_image(chart_image_b64)
    if chart_bytes:
        elements.append(Spacer(1, 8))
        chart_title = ""
        if data.get("chart") and data["chart"].get("title"):
            chart_title = data["chart"]["title"]
            elements.append(Paragraph(f"\U0001F4CA {chart_title}", styles["heading"]))
        else:
            elements.append(Paragraph("\U0001F4CA Carta", styles["heading"]))
        img_stream = io.BytesIO(chart_bytes)
        page_width = A4[0] - 4 * cm
        img = Image(img_stream, width=page_width, height=page_width * 0.5)
        elements.append(img)
        elements.append(Spacer(1, 8))

    table_data = data.get("table")
    if table_data and table_data.get("headers") and table_data.get("rows"):
        elements.append(Paragraph("\U0001F4CA Data", styles["heading"]))
        headers = table_data["headers"]
        rows = table_data["rows"][:20]
        tbl_data = [headers] + rows
        col_widths = [min(450 / len(headers), 120)] * len(headers)
        tbl = Table(tbl_data, colWidths=col_widths)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#f1f5f9")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 1), (-1, -1), HexColor("#1e293b")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#f8fafc"), HexColor("#e2e8f0")]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(tbl)

    cadangan = data.get("cadangan", [])
    if cadangan:
        elements.append(Paragraph("\U0001F4A1 Cadangan", styles["heading"]))
        for c in cadangan:
            elements.append(Paragraph(f"•  {c}", styles["bullet"]))

    amaran = data.get("amaran", [])
    if amaran:
        elements.append(Paragraph("⚠️ Amaran", styles["heading"]))
        for a in amaran:
            elements.append(Paragraph(f"•  {a}", styles["warning"]))

    doc.build(elements)
    return buf.getvalue()


def build_xlsx(data: dict, df=None) -> bytes:
    """Export the analysis to an .xlsx workbook: summary, analysis table(s),
    an auto-computed pivot, and the full dataset."""
    import pandas as pd

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # ── Summary sheet ──
        rows = []
        if data.get("message"):
            rows.append(["Ringkasan", data["message"]])
        for label, key in [("Penemuan", "penemuan"), ("Cadangan", "cadangan"), ("Amaran", "amaran")]:
            for item in (data.get(key) or []):
                rows.append([label, item])
        if data.get("tafsiran"):
            rows.append(["Tafsiran", data["tafsiran"]])
        summary_df = pd.DataFrame(rows or [["Ringkasan", "Analisis Data"]], columns=["Bahagian", "Butiran"])
        summary_df.to_excel(writer, sheet_name="Ringkasan", index=False)

        # ── Analysis table(s) ──
        for i, key in enumerate(["table", "table2"]):
            tbl = data.get(key)
            if tbl and tbl.get("headers") and tbl.get("rows"):
                tdf = pd.DataFrame(tbl["rows"], columns=tbl["headers"])
                tdf.to_excel(writer, sheet_name=("Jadual Analisis" if i == 0 else "Jadual Perbandingan"), index=False)

        # ── Auto pivot from the full dataset (first category × mean of numerics) ──
        if df is not None and not df.empty:
            cats = df.select_dtypes(include=["object", "category"]).columns.tolist()
            nums = df.select_dtypes(include=["number"]).columns.tolist()
            cats = [c for c in cats if 1 < df[c].nunique(dropna=True) <= 50]
            if cats and nums:
                try:
                    pivot = df.groupby(cats[0])[nums].mean().round(2)
                    pivot.to_excel(writer, sheet_name="Pivot")
                except Exception:
                    pass
            # ── Full dataset ──
            safe = df.copy()
            if safe.shape[0] > 100000:
                safe = safe.head(100000)
            safe.to_excel(writer, sheet_name="Data Penuh", index=False)

    return buf.getvalue()
