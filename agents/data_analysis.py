"""Data Analysis Agent — Section 1: Professional Data Analyst."""

import json
import io
import os
import pathlib
import pandas as pd
from backend.deepseek_client import chat_completion

_DATA_DIR = pathlib.Path("static/session_data")

SYSTEM_PROMPT = """Anda ialah penganalisis data profesional dalam SMARTAssist Hub.
Anda menganalisis data yang dimuat naik oleh pengguna (CSV/Excel) dan memberi taklimat
ringkas seperti seorang penganalisis yang membentangkan kepada pengurus.

GAYA RESPONS:
- Tepat, berasaskan bukti, berhati-hati terhadap overclaiming
- Gunakan Bahasa Malaysia rasmi
- Analisis berdasarkan DATA SEBENAR yang diberikan sahaja — jangan reka data

JENIS RESPONS (response_type):
- "tanya" : soalan penjelasan sebelum analisis
- "papar" : paparan data/carta/jadual
- "kemaskini" : kemas kini data sedia ada
- "pandangan" : pandangan/insight berdasarkan data
- "rumusan" : rumusan keseluruhan analisis

STRUKTUR WAJIB untuk setiap respons substantif (papar/pandangan/rumusan):
1. penemuan — fakta utama daripada data
2. tafsiran — apa makna penemuan ini
3. cadangan — tindakan yang dicadangkan
4. amaran — kaveat, had data, risiko overclaiming (WAJIB jika saiz sampel kecil atau kualiti data meragukan)

FORMAT OUTPUT:
Balas HANYA dalam JSON yang sah dengan struktur berikut:
{
  "response_type": "tanya|papar|pandangan|rumusan|kemaskini",
  "message": "Teks respons utama dalam Bahasa Malaysia",
  "penemuan": ["Fakta 1", "Fakta 2"],
  "tafsiran": "Interpretasi penemuan",
  "cadangan": ["Cadangan 1", "Cadangan 2"],
  "amaran": ["Kaveat 1"],
  "chart": {
    "type": "bar|line|pie|doughnut",
    "title": "Tajuk Carta",
    "labels": ["Label1", "Label2"],
    "datasets": [
      {
        "label": "Nama Dataset",
        "data": [10, 20],
        "backgroundColor": ["#3b82f6", "#22c55e"]
      }
    ]
  },
  "table": {
    "headers": ["Lajur1", "Lajur2"],
    "rows": [["Nilai1", "Nilai2"]]
  },
  "susulan": ["Cadangan soalan seterusnya 1", "Cadangan soalan seterusnya 2"]
}

NOTA:
- "chart" adalah PILIHAN — sertakan hanya jika data sesuai untuk visualisasi
- "table" adalah PILIHAN — sertakan untuk memaparkan data dalam bentuk jadual
- "susulan" WAJIB — sentiasa cadangkan 2-4 soalan susulan yang mendalami topik
- Untuk "tanya", hanya perlukan "message" dan "susulan"
- Gunakan data SEBENAR dari dataset yang diberikan — JANGAN sesekali reka, tambah, atau ubah suai data
- Data penuh dalam format CSV disediakan — rujuk data tersebut untuk SEMUA analisis
- Pastikan SETIAP nombor, nama, dan nilai dalam respons anda wujud dalam dataset asal
- Jika data hanya mempunyai N baris, analisis HANYA N baris tersebut — jangan cipta baris tambahan
- Pastikan JSON sah tanpa trailing comma
- Untuk carta dan jadual, gunakan data sebenar dari dataset — semak setiap nilai sebelum masukkan"""

_explored_topics: dict[str, list[str]] = {}
_session_data: dict[str, dict] = {}


def _get_explored(session_id: str) -> list[str]:
    return _explored_topics.get(session_id, [])


def _add_explored(session_id: str, topic: str):
    if session_id not in _explored_topics:
        _explored_topics[session_id] = []
    if topic not in _explored_topics[session_id]:
        _explored_topics[session_id].append(topic)


def _build_context_note(session_id: str) -> str:
    explored = _get_explored(session_id)
    if not explored:
        return ""
    return (
        f"\n\nTopik yang telah diterokai dalam sesi ini: {', '.join(explored)}. "
        "Cadangkan soalan susulan yang BERBEZA dan lebih mendalam daripada topik ini "
        "(contoh: perincian -> anomali -> perbandingan -> eksport)."
    )


def _build_data_context(session_id: str) -> str:
    data = _session_data.get(session_id)
    if not data:
        return ""
    return (
        f"\n\nRINGKASAN DATA:\n{data['summary']}"
        f"\n\nDATA PENUH (CSV):\n{data['full_data']}"
        "\n\nPENTING: Gunakan HANYA data di atas untuk analisis. "
        "JANGAN reka atau tambah data yang tiada dalam dataset. "
        "Pastikan semua nombor, nama, dan nilai dalam respons anda sepadan tepat dengan data di atas."
    )


def upload_file(file_bytes: bytes, filename: str, session_id: str = "default") -> dict:
    """Parse uploaded CSV/Excel file and store summary for the session."""
    try:
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
        if ext == "csv":
            df = pd.read_csv(io.BytesIO(file_bytes))
        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            return {"ok": False, "error": f"Format fail '{ext}' tidak disokong. Sila muat naik CSV atau Excel (.xlsx)."}

        summary = _summarize_dataframe(df, filename)
        full_data = df.to_csv(index=False)
        if len(full_data) > 60000:
            full_data = df.head(500).to_csv(index=False)

        entry = {
            "filename": filename,
            "summary": summary,
            "full_data": full_data,
            "shape": list(df.shape),
            "columns": list(df.columns),
        }
        _session_data[session_id] = entry
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            (_DATA_DIR / f"{session_id}.json").write_text(
                json.dumps(entry, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

        return {
            "ok": True,
            "filename": filename,
            "rows": df.shape[0],
            "columns": df.shape[1],
            "column_names": list(df.columns),
        }
    except Exception as e:
        return {"ok": False, "error": f"Gagal membaca fail: {e}"}


def _summarize_dataframe(df: pd.DataFrame, filename: str) -> str:
    lines = [
        f"Nama fail: {filename}",
        f"Saiz: {df.shape[0]} baris x {df.shape[1]} lajur",
        f"Lajur: {', '.join(df.columns.tolist())}",
        "",
        "Jenis data setiap lajur:",
    ]
    for col in df.columns:
        dtype = str(df[col].dtype)
        nulls = int(df[col].isnull().sum())
        null_info = f" ({nulls} nilai kosong)" if nulls > 0 else ""
        lines.append(f"  - {col}: {dtype}{null_info}")

    lines.append("")
    lines.append("Statistik ringkas (lajur numerik):")
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if numeric_cols:
        desc = df[numeric_cols].describe().round(2)
        lines.append(desc.to_string())
    else:
        lines.append("  Tiada lajur numerik.")

    lines.append("")
    lines.append(f"5 baris pertama data:")
    preview = df.head(5).to_string(index=False)
    lines.append(preview)

    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if cat_cols:
        lines.append("")
        lines.append("Nilai unik lajur kategori:")
        for col in cat_cols[:10]:
            uniques = df[col].nunique()
            top_vals = df[col].value_counts().head(8)
            top_str = ", ".join(f"{v} ({c})" for v, c in top_vals.items())
            lines.append(f"  - {col}: {uniques} nilai unik. Teratas: {top_str}")

    return "\n".join(lines)


def get_session_data(session_id: str) -> dict | None:
    if session_id in _session_data:
        return _session_data[session_id]
    p = _DATA_DIR / f"{session_id}.json"
    if p.exists():
        try:
            entry = json.loads(p.read_text(encoding="utf-8"))
            _session_data[session_id] = entry
            return entry
        except Exception:
            pass
    return None


def clear_session_data(session_id: str):
    _session_data.pop(session_id, None)
    _explored_topics.pop(session_id, None)
    p = _DATA_DIR / f"{session_id}.json"
    try:
        p.unlink(missing_ok=True)
    except Exception:
        pass


def handle(query: str, history: list[dict] | None = None, session_id: str = "default", lang: str = "bm", user_name: str = "") -> str:
    sapaan = f", {user_name.split()[0]}" if user_name else ""
    if query == '__INTRO__':
        if lang == "en":
            return (f"Assalamualaikum and welcome{sapaan}! 👋 I am the Data Analysis Agent. Upload your CSV or Excel file using the 📎 button, then ask anything about the data. I can generate charts, summary statistics, detect missing values and much more. Which file would you like to analyse today?\n\n"
                    "⚠️ Reminder: All analysis, charts and interpretations are AI-generated. Please verify the findings against your original data before using them in any official report or decision.")
        return (f"Assalamualaikum dan selamat datang{sapaan}! 👋 Saya Analisis Data Agent. Muat naik fail CSV atau Excel anda menggunakan butang 📎, kemudian tanya apa sahaja tentang data tersebut. Saya boleh menjana carta, statistik ringkasan, mengesan data kosong dan banyak lagi. Fail apa yang ingin anda analisis hari ini?\n\n"
                "⚠️ Peringatan: Semua analisis, carta dan interpretasi adalah hasil AI. Sila sahkan dapatan dengan data asal anda sebelum digunakan dalam sebarang laporan rasmi atau membuat keputusan.")

    context_note = _build_context_note(session_id)
    data_context = _build_data_context(session_id)
    lang_note = "\n\nIMPORTANT: The user has selected English. You MUST respond entirely in English. All text fields in your JSON response must be in English." if lang == "en" else ""

    if not data_context and not history:
        if lang == "en":
            return json.dumps({
                "response_type": "tanya",
                "message": "Welcome to the Data Analysis Agent. Please upload your data file (CSV or Excel) using the 📎 button below, then ask questions about the data.",
                "susulan": ["Upload a CSV file to analyse", "Upload an Excel file to analyse"],
            }, ensure_ascii=False)
        return json.dumps({
            "response_type": "tanya",
            "message": (
                "Selamat datang ke Agen Analisis Data. "
                "Sila muat naik fail data anda (CSV atau Excel) menggunakan butang 📎 di bawah, "
                "kemudian tanya soalan tentang data tersebut."
            ),
            "susulan": [
                "Muat naik fail CSV untuk dianalisis",
                "Muat naik fail Excel untuk dianalisis",
            ],
        }, ensure_ascii=False)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + data_context + context_note + lang_note},
    ]
    if history:
        for msg in history[-8:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": query})

    try:
        raw = chat_completion(messages=messages, temperature=0.3, max_tokens=3000)
    except RuntimeError as e:
        return json.dumps({
            "response_type": "error",
            "message": f"Ralat menghubungi API analisis. Sila cuba lagi.\n{e}",
            "susulan": ["Cuba semula soalan tadi"],
        }, ensure_ascii=False)

    parsed = _try_parse_json(raw)

    if parsed and parsed.get("response_type") != "tanya":
        topic_hint = query[:60]
        _add_explored(session_id, topic_hint)

    if parsed:
        return json.dumps(parsed, ensure_ascii=False)
    return json.dumps({
        "response_type": "pandangan",
        "message": raw,
        "penemuan": [],
        "tafsiran": "",
        "cadangan": [],
        "amaran": ["Respons ini tidak dalam format berstruktur — paparan carta tidak tersedia."],
        "susulan": ["Boleh jelaskan dengan lebih terperinci?"],
    }, ensure_ascii=False)


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
