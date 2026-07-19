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
_session_df: dict[str, "pd.DataFrame"] = {}


def _df_path(session_id: str) -> pathlib.Path:
    return _DATA_DIR / f"{session_id}.data.csv"


def _get_df(session_id: str) -> "pd.DataFrame | None":
    """Return the FULL dataframe for a session (memory cache → disk → truncated fallback)."""
    if session_id in _session_df:
        return _session_df[session_id]
    p = _df_path(session_id)
    if p.exists():
        try:
            df = pd.read_csv(p)
            _session_df[session_id] = df
            return df
        except Exception:
            pass
    data = get_session_data(session_id)
    if data and data.get("full_data"):
        try:
            df = pd.read_csv(io.StringIO(data["full_data"]))
            _session_df[session_id] = df
            return df
        except Exception:
            pass
    return None


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


def upload_file(file_bytes: bytes, filename: str, session_id: str = "default", lang: str = "bm") -> dict:
    """Parse uploaded CSV/Excel file, store the FULL data for pandas computation,
    and return an auto-EDA profile the frontend can render immediately."""
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
        _session_df[session_id] = df
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            (_DATA_DIR / f"{session_id}.json").write_text(
                json.dumps(entry, ensure_ascii=False), encoding="utf-8"
            )
            # Persist the FULL dataset so pandas computations use every row
            df.to_csv(_df_path(session_id), index=False)
        except Exception:
            pass

        try:
            eda = _compute_eda(df, filename, lang=lang)
            # Surface one-click education templates when school data is detected
            edu = _detect_education_columns(df)
            edu_chips = []
            if _has_education_data(edu):
                edu_chips.append("Analisis keputusan peperiksaan" if lang != "en" else "Analyse exam results")
            if edu.get("attendance_col"):
                edu_chips.append("Analisis kehadiran" if lang != "en" else "Analyse attendance")
            if edu_chips and isinstance(eda, dict):
                eda["susulan"] = edu_chips + eda.get("susulan", [])
        except Exception:
            eda = None

        return {
            "ok": True,
            "filename": filename,
            "rows": df.shape[0],
            "columns": df.shape[1],
            "column_names": list(df.columns),
            "eda": eda,
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


_PALETTE = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6",
            "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#14b8a6"]


def _compute_eda(df: pd.DataFrame, filename: str, lang: str = "bm") -> dict:
    """Deterministic auto-EDA profile computed with pandas (no LLM) —
    returned as a structured payload the frontend can render directly."""
    EN = lang == "en"
    n_rows, n_cols = df.shape
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    # ── Data quality metrics ──
    missing_cells = int(df.isnull().sum().sum())
    total_cells = max(1, n_rows * n_cols)
    missing_pct = round(missing_cells / total_cells * 100, 1)
    dup_rows = int(df.duplicated().sum())
    dup_pct = round(dup_rows / max(1, n_rows) * 100, 1)

    outlier_info: list[tuple[str, int]] = []
    for col in numeric_cols:
        s = df[col].dropna()
        if len(s) < 8:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        n_out = int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
        if n_out > 0:
            outlier_info.append((col, n_out))
    outlier_info.sort(key=lambda x: -x[1])

    score = max(0, min(100, round(100 - missing_pct * 1.5 - dup_pct)))
    if score >= 90:
        grade = "Cemerlang" if not EN else "Excellent"
    elif score >= 75:
        grade = "Baik" if not EN else "Good"
    elif score >= 50:
        grade = "Sederhana" if not EN else "Fair"
    else:
        grade = "Lemah" if not EN else "Poor"

    # ── Auto-insights ──
    insights: list[str] = []
    insights.append(
        f"Dataset contains {n_rows} rows x {n_cols} columns ({len(numeric_cols)} numeric, {len(cat_cols)} categorical)."
        if EN else
        f"Dataset mengandungi {n_rows} baris x {n_cols} lajur ({len(numeric_cols)} numerik, {len(cat_cols)} kategori)."
    )
    if missing_cells:
        worst = df.isnull().sum().sort_values(ascending=False)
        worst = worst[worst > 0].head(3)
        cols_txt = ", ".join(f"{c} ({int(v)})" for c, v in worst.items())
        insights.append(
            f"{missing_cells} missing values ({missing_pct}%) — most affected: {cols_txt}."
            if EN else
            f"{missing_cells} nilai kosong ({missing_pct}%) — paling terjejas: {cols_txt}."
        )
    if dup_rows:
        insights.append(
            f"{dup_rows} duplicate rows detected ({dup_pct}%)." if EN
            else f"{dup_rows} baris pendua dikesan ({dup_pct}%)."
        )
    if outlier_info:
        top_out = ", ".join(f"{c} ({n})" for c, n in outlier_info[:3])
        insights.append(
            f"Outliers (IQR method) found in: {top_out}." if EN
            else f"Outlier (kaedah IQR) dikesan dalam: {top_out}."
        )
    const_cols = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]
    if const_cols:
        insights.append(
            f"Constant columns (single value): {', '.join(const_cols[:5])}." if EN
            else f"Lajur malar (satu nilai sahaja): {', '.join(const_cols[:5])}."
        )
    if len(numeric_cols) >= 2:
        try:
            corr = df[numeric_cols].corr()
            best_pair, best_r = None, 0.0
            for i, a in enumerate(numeric_cols):
                for b in numeric_cols[i + 1:]:
                    r = corr.loc[a, b]
                    if pd.notna(r) and abs(r) > abs(best_r):
                        best_pair, best_r = (a, b), float(r)
            if best_pair and abs(best_r) >= 0.6:
                insights.append(
                    f"Strong correlation between '{best_pair[0]}' and '{best_pair[1]}' (r={best_r:.2f})." if EN
                    else f"Korelasi kuat antara '{best_pair[0]}' dan '{best_pair[1]}' (r={best_r:.2f})."
                )
        except Exception:
            pass

    # ── Column profile table ──
    headers = (["Column", "Type", "Missing", "Unique", "Min", "Mean", "Max"] if EN
               else ["Lajur", "Jenis", "Kosong", "Unik", "Min", "Purata", "Maks"])
    rows = []
    for col in df.columns[:25]:
        s = df[col]
        is_num = col in numeric_cols
        rows.append([
            str(col), str(s.dtype), int(s.isnull().sum()), int(s.nunique(dropna=True)),
            round(float(s.min()), 2) if is_num and s.notna().any() else "-",
            round(float(s.mean()), 2) if is_num and s.notna().any() else "-",
            round(float(s.max()), 2) if is_num and s.notna().any() else "-",
        ])

    # ── Default chart ──
    chart = None
    try:
        if missing_cells:
            miss = df.isnull().sum()
            miss = miss[miss > 0].sort_values(ascending=False).head(10)
            chart = {
                "type": "bar",
                "title": "Missing values by column" if EN else "Nilai Kosong Mengikut Lajur",
                "labels": [str(c) for c in miss.index],
                "datasets": [{"label": "Missing" if EN else "Kosong",
                              "data": [int(v) for v in miss.values],
                              "backgroundColor": _PALETTE[:len(miss)]}],
            }
        elif numeric_cols:
            col = max(numeric_cols, key=lambda c: df[c].nunique(dropna=True))
            s = df[col].dropna()
            if s.nunique() > 1:
                bins = min(8, s.nunique())
                cut = pd.cut(s, bins=bins)
                counts = cut.value_counts().sort_index()
                chart = {
                    "type": "bar",
                    "title": (f"Distribution of {col}" if EN else f"Taburan {col}"),
                    "labels": [f"{iv.left:.4g}–{iv.right:.4g}" for iv in counts.index],
                    "datasets": [{"label": col, "data": [int(v) for v in counts.values],
                                  "backgroundColor": _PALETTE[0]}],
                }
        elif cat_cols:
            col = cat_cols[0]
            vc = df[col].value_counts().head(8)
            chart = {
                "type": "bar",
                "title": (f"Top categories: {col}" if EN else f"Kategori Teratas: {col}"),
                "labels": [str(i) for i in vc.index],
                "datasets": [{"label": col, "data": [int(v) for v in vc.values],
                              "backgroundColor": _PALETTE[:len(vc)]}],
            }
    except Exception:
        chart = None

    msg = (
        f"File '{filename}' uploaded and profiled automatically. Data quality score: {score}/100 ({grade})."
        if EN else
        f"Fail '{filename}' berjaya dimuat naik dan diprofilkan secara automatik. Skor kualiti data: {score}/100 ({grade})."
    )
    amaran = []
    if missing_pct > 5 or dup_rows:
        amaran.append(
            "Data quality issues detected — review missing/duplicate values before drawing conclusions." if EN
            else "Isu kualiti data dikesan — semak nilai kosong/pendua sebelum membuat kesimpulan."
        )

    susulan = (
        ["Give me a full analysis of this dataset", "Check data quality in detail",
         "Detect anomalies and outliers", "Show correlations between numeric columns"]
        if EN else
        ["Buat analisis penuh dataset ini", "Semak kualiti data dengan terperinci",
         "Kesan anomali dan outlier", "Tunjukkan korelasi antara lajur numerik"]
    )

    payload = {
        "response_type": "papar",
        "message": msg,
        "penemuan": insights,
        "amaran": amaran,
        "table": {"headers": headers, "rows": rows},
        "susulan": susulan,
    }
    if chart:
        payload["chart"] = chart
    return payload


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
    _session_df.pop(session_id, None)
    for p in (_DATA_DIR / f"{session_id}.json", _df_path(session_id)):
        try:
            p.unlink(missing_ok=True)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════
#  Plan → Execute → Narrate
#  The LLM PLANS which pandas operations to run; the server EXECUTES
#  them on the FULL dataset; the LLM then NARRATES the real results.
#  This guarantees every number in the answer is computed, not guessed.
# ═══════════════════════════════════════════════════════════════════

_PLAN_PROMPT = """Anda ialah perancang analisis data. Berdasarkan soalan pengguna dan struktur dataset,
pilih operasi pandas (1 hingga 4) yang perlu dijalankan untuk menjawab soalan dengan TEPAT.

Operasi yang dibenarkan:
- {"op":"describe","cols":["A","B"]} — statistik deskriptif (cols pilihan; lalai semua numerik)
- {"op":"value_counts","col":"A","top":10} — kiraan nilai unik satu lajur
- {"op":"groupby","by":["A"],"col":"B","agg":"mean","top":15,"sort":"desc"} — agregat mengikut kumpulan; agg: mean|sum|count|median|min|max|nunique; "col" pilihan (tanpa col = kiraan baris)
- {"op":"filter","where":[{"col":"A","cmp":">","val":50}],"then":"rows","cols":["A","B"],"top":20} — tapis baris; cmp: ==|!=|>|>=|<|<=|contains|isnull|notnull; "then": "count" | "rows" | {"agg":"mean","col":"B"}
- {"op":"correlation"} — korelasi antara semua lajur numerik
- {"op":"top_rows","sort_col":"A","ascending":false,"n":10,"cols":["A","B"]} — baris teratas selepas isih
- {"op":"crosstab","row":"A","col":"B"} — jadual silang dua lajur kategori

Peraturan:
- Gunakan HANYA nama lajur yang wujud dalam senarai lajur diberikan (padankan ejaan tepat).
- Untuk soalan umum ("analisis penuh", "ringkasan"), gunakan describe + value_counts lajur kategori utama + correlation.
- Balas HANYA JSON sah: {"ops":[...]}"""

_ALLOWED_AGGS = {"mean", "sum", "count", "median", "min", "max", "nunique"}


def _fmt_result(obj, max_rows: int = 25) -> str:
    if isinstance(obj, pd.Series):
        obj = obj.to_frame()
    if isinstance(obj, pd.DataFrame):
        total = len(obj)
        txt = obj.head(max_rows).to_string()
        if total > max_rows:
            txt += f"\n... ({total} baris kesemuanya; {max_rows} pertama dipaparkan)"
        return txt
    return str(obj)


def _apply_filter(df: pd.DataFrame, where: list[dict]) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for cond in where or []:
        col, cmp, val = cond.get("col"), cond.get("cmp"), cond.get("val")
        if col not in df.columns:
            raise ValueError(f"Lajur '{col}' tiada dalam dataset")
        s = df[col]
        if cmp in (">", ">=", "<", "<=") or (cmp in ("==", "!=") and pd.api.types.is_numeric_dtype(s)):
            try:
                val = float(val)
            except (TypeError, ValueError):
                pass
        if cmp == "==":
            mask &= (s == val)
        elif cmp == "!=":
            mask &= (s != val)
        elif cmp == ">":
            mask &= (s > val)
        elif cmp == ">=":
            mask &= (s >= val)
        elif cmp == "<":
            mask &= (s < val)
        elif cmp == "<=":
            mask &= (s <= val)
        elif cmp == "contains":
            mask &= s.astype(str).str.contains(str(val), case=False, na=False)
        elif cmp == "isnull":
            mask &= s.isnull()
        elif cmp == "notnull":
            mask &= s.notnull()
        else:
            raise ValueError(f"Operator '{cmp}' tidak disokong")
    return mask


def _execute_ops(df: pd.DataFrame, ops: list[dict]) -> list[str]:
    """Run a validated list of pandas operations; return formatted result blocks."""
    blocks: list[str] = []
    for op_spec in (ops or [])[:4]:
        try:
            op = op_spec.get("op")
            if op == "describe":
                cols = [c for c in (op_spec.get("cols") or []) if c in df.columns]
                target = df[cols] if cols else df.select_dtypes(include=["number"])
                if target.shape[1] == 0:
                    continue
                blocks.append("### Statistik deskriptif\n" + _fmt_result(target.describe().round(3)))
            elif op == "value_counts":
                col = op_spec.get("col")
                if col not in df.columns:
                    continue
                top = int(op_spec.get("top", 10))
                vc = df[col].value_counts().head(max(1, min(top, 30)))
                blocks.append(f"### Kiraan nilai: {col}\n" + _fmt_result(vc))
            elif op == "groupby":
                by = [c for c in (op_spec.get("by") or []) if c in df.columns]
                if not by:
                    continue
                col = op_spec.get("col")
                agg = op_spec.get("agg", "count")
                if agg not in _ALLOWED_AGGS:
                    agg = "count"
                if col and col in df.columns:
                    res = df.groupby(by)[col].agg(agg)
                    title = f"{agg}({col}) mengikut {', '.join(by)}"
                else:
                    res = df.groupby(by).size()
                    title = f"kiraan baris mengikut {', '.join(by)}"
                asc = str(op_spec.get("sort", "desc")).lower() == "asc"
                res = res.sort_values(ascending=asc)
                top = max(1, min(int(op_spec.get("top", 15)), 40))
                if pd.api.types.is_float_dtype(res):
                    res = res.round(3)
                blocks.append(f"### Groupby: {title}\n" + _fmt_result(res.head(top)))
            elif op == "filter":
                mask = _apply_filter(df, op_spec.get("where") or [])
                sub = df[mask]
                then = op_spec.get("then", "count")
                desc = json.dumps(op_spec.get("where", []), ensure_ascii=False)
                if then == "count":
                    blocks.append(f"### Tapisan {desc}\nBilangan baris sepadan: {len(sub)} daripada {len(df)}")
                elif then == "rows":
                    cols = [c for c in (op_spec.get("cols") or []) if c in df.columns] or list(df.columns)
                    top = max(1, min(int(op_spec.get("top", 20)), 40))
                    blocks.append(f"### Baris sepadan {desc} ({len(sub)} baris)\n" + _fmt_result(sub[cols], top))
                elif isinstance(then, dict):
                    agg = then.get("agg", "mean")
                    col = then.get("col")
                    if agg in _ALLOWED_AGGS and col in df.columns:
                        val = getattr(sub[col], agg)()
                        blocks.append(f"### {agg}({col}) untuk tapisan {desc}\n{round(float(val), 4) if pd.notna(val) else 'tiada data'} ({len(sub)} baris sepadan)")
            elif op == "correlation":
                num = df.select_dtypes(include=["number"])
                if num.shape[1] < 2:
                    continue
                corr = num.corr()
                pairs = []
                cols = list(num.columns)
                for i, a in enumerate(cols):
                    for b in cols[i + 1:]:
                        r = corr.loc[a, b]
                        if pd.notna(r):
                            pairs.append((abs(float(r)), f"{a} ↔ {b}: r={float(r):.3f}"))
                pairs.sort(reverse=True)
                blocks.append("### Korelasi (pasangan terkuat)\n" + "\n".join(p[1] for p in pairs[:10]))
            elif op == "top_rows":
                sc = op_spec.get("sort_col")
                if sc not in df.columns:
                    continue
                n = max(1, min(int(op_spec.get("n", 10)), 40))
                cols = [c for c in (op_spec.get("cols") or []) if c in df.columns] or list(df.columns)
                res = df.sort_values(sc, ascending=bool(op_spec.get("ascending", False))).head(n)[cols]
                blocks.append(f"### Top {n} mengikut {sc}\n" + _fmt_result(res, n))
            elif op == "crosstab":
                r, c = op_spec.get("row"), op_spec.get("col")
                if r not in df.columns or c not in df.columns:
                    continue
                ct = pd.crosstab(df[r], df[c])
                blocks.append(f"### Jadual silang: {r} x {c}\n" + _fmt_result(ct.iloc[:15, :10]))
        except Exception as e:
            blocks.append(f"### Operasi {op_spec.get('op')} gagal: {e}")
    return blocks


def _plan_and_compute(query: str, df: pd.DataFrame) -> str | None:
    """Ask the LLM to plan pandas operations, execute them on the full dataset,
    and return a computed-results context block. None on failure."""
    col_lines = []
    for col in df.columns[:40]:
        s = df[col]
        samples = ", ".join(str(v)[:30] for v in s.dropna().unique()[:3])
        col_lines.append(f"- {col} ({s.dtype}): cth. {samples}")
    plan_user = (
        f"Dataset: {df.shape[0]} baris x {df.shape[1]} lajur\n"
        f"Lajur:\n" + "\n".join(col_lines) +
        f"\n\nSoalan pengguna: {query}"
    )
    try:
        raw = chat_completion(
            messages=[{"role": "system", "content": _PLAN_PROMPT},
                      {"role": "user", "content": plan_user}],
            temperature=0.0, max_tokens=600,
        )
        plan = _try_parse_json(raw)
        ops = plan.get("ops") if isinstance(plan, dict) else None
        if not ops:
            return None
        blocks = _execute_ops(df, ops)
        if not blocks:
            return None
        return (
            f"\n\nHASIL PENGIRAAN SEBENAR (dikira oleh pandas ke atas KESEMUA {df.shape[0]} baris):\n\n"
            + "\n\n".join(blocks)
            + "\n\nPENTING: Setiap nombor dalam respons anda MESTI diambil terus daripada "
              "HASIL PENGIRAAN di atas atau RINGKASAN DATA. JANGAN kira sendiri, "
              "JANGAN anggar, dan JANGAN reka sebarang nilai."
        )
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════
#  Education templates — one-click analysis for KPM/PPD school data.
#  All figures are computed deterministically with pandas (no LLM),
#  so every number is exact. The KPM grade scale below is stated in
#  each result so the user can verify the assumption.
# ═══════════════════════════════════════════════════════════════════

# Markah → Gred → Mata (skala standard SPM; GPMP/GPS rendah = lebih baik)
_GRADE_BANDS = [
    (90, "A+", 0), (80, "A", 1), (70, "A-", 2), (65, "B+", 3),
    (60, "B", 4), (55, "C+", 5), (50, "C", 6), (45, "D", 7),
    (40, "E", 8), (0, "G", 9),
]
_GRADE_ORDER = ["A+", "A", "A-", "B+", "B", "C+", "C", "D", "E", "G"]
_GRADE_POINT = {g: p for _, g, p in _GRADE_BANDS}
_EXTRA_GRADE_POINT = {"B-": 4, "C-": 6, "F": 9, "TH": 9, "TP": 9}
_PASS_GRADES = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "E"}
_EXCELLENT_GRADES = {"A+", "A", "A-"}

_SUBJECT_HINTS = {
    "bm", "bi", "bahasa melayu", "bahasa inggeris", "english", "matematik", "mate", "mt",
    "mat", "sains", "sn", "sejarah", "sej", "geografi", "geo", "pendidikan islam", "pi",
    "pai", "pjk", "pjpk", "rbt", "prinsip perakaunan", "ekonomi", "fizik", "kimia",
    "biologi", "bio", "matematik tambahan", "add math", "addmath", "pendidikan moral",
    "moral", "tasawwur", "psv", "pendidikan seni", "reka bentuk", "asas sains komputer",
    "ask", "physics", "chemistry", "biology", "mathematics", "science", "history", "geography",
}


def _mark_to_grade(mark) -> str | None:
    if pd.isna(mark):
        return None
    for lo, g, _ in _GRADE_BANDS:
        if mark >= lo:
            return g
    return "G"


def _detect_education_columns(df: pd.DataFrame) -> dict:
    """Best-effort detection of KPM school-data columns."""
    lower = {c: str(c).strip().lower() for c in df.columns}
    numeric = df.select_dtypes(include=["number"]).columns.tolist()

    def find(patterns):
        for c in df.columns:
            if any(p in lower[c] for p in patterns):
                return c
        return None

    school_col = find(["sekolah", "school"])
    class_col = find(["kelas", "class", "tingkatan", "darjah"])
    name_col = find(["nama", "name", "murid", "pelajar", "student"])
    attendance_col = find(["kehadiran", "attendance", "hadir"])

    id_like = {school_col, class_col, name_col, attendance_col}

    def looks_id(c):
        toks = lower[c].replace("_", " ").split()
        return ("id" in toks or "no" in toks or "bil" in toks or
                "tahun" in lower[c] or "year" in lower[c] or "umur" in lower[c] or "age" in lower[c])

    def name_match(c):
        l = lower[c]
        toks = set(l.replace("_", " ").split())
        return any(h == l or h in toks for h in _SUBJECT_HINTS)

    named = [c for c in numeric if c not in id_like and name_match(c) and not looks_id(c)]
    if named:
        subjects = named
    else:
        subjects = []
        for c in numeric:
            if c in id_like or looks_id(c):
                continue
            s = df[c].dropna()
            if not s.empty and s.between(0, 100).mean() >= 0.95 and s.max() <= 100:
                subjects.append(c)

    grade_cols = []
    known = set(_GRADE_ORDER) | set(_EXTRA_GRADE_POINT)
    for c in df.select_dtypes(include=["object", "category"]).columns:
        vals = df[c].dropna().astype(str).str.strip().str.upper()
        if not vals.empty and vals.isin(known).mean() >= 0.8:
            grade_cols.append(c)

    return {
        "subjects": subjects, "grade_cols": grade_cols, "attendance_col": attendance_col,
        "school_col": school_col, "class_col": class_col, "name_col": name_col,
    }


def _has_education_data(edu: dict) -> bool:
    return bool(edu.get("subjects") or edu.get("grade_cols"))


def _grade_series_for(df: pd.DataFrame, col: str, is_numeric: bool) -> pd.Series:
    if is_numeric:
        return df[col].map(_mark_to_grade)
    return df[col].dropna().astype(str).str.strip().str.upper()


def _grade_stats(grades: pd.Series) -> dict:
    g = grades.dropna()
    n = len(g)
    if n == 0:
        return {"n": 0}
    points = g.map(lambda x: _GRADE_POINT.get(x, _EXTRA_GRADE_POINT.get(x)))
    valid_points = points.dropna()
    lulus = g.isin(_PASS_GRADES).sum()
    cemerlang = g.isin(_EXCELLENT_GRADES).sum()
    dist = g.value_counts()
    top_grade = dist.index[0] if not dist.empty else "-"
    return {
        "n": n,
        "lulus_pct": round(lulus / n * 100, 1),
        "cemerlang_pct": round(cemerlang / n * 100, 1),
        "gpmp": round(float(valid_points.mean()), 2) if not valid_points.empty else None,
        "top_grade": top_grade,
    }


def _exam_analysis(df: pd.DataFrame, edu: dict, lang: str = "bm") -> dict:
    EN = lang == "en"
    subject_cols = [(c, True) for c in edu["subjects"]] + [(c, False) for c in edu["grade_cols"]]

    headers = (["Subject", "Sat", "Pass %", "Distinction (A) %", "GPMP", "Top Grade"] if EN
               else ["Subjek", "Bil", "Lulus %", "Cemerlang (A) %", "GPMP", "Gred Terbanyak"])
    rows = []
    gpmp_pairs = []
    pass_pairs = []
    all_points = []
    for col, is_num in subject_cols:
        grades = _grade_series_for(df, col, is_num)
        st = _grade_stats(grades)
        if st["n"] == 0:
            continue
        rows.append([str(col), st["n"], st["lulus_pct"], st["cemerlang_pct"],
                     st["gpmp"] if st["gpmp"] is not None else "-", st["top_grade"]])
        if st["gpmp"] is not None:
            gpmp_pairs.append((str(col), st["gpmp"]))
        pass_pairs.append((str(col), st["lulus_pct"]))
        pts = grades.dropna().map(lambda x: _GRADE_POINT.get(x, _EXTRA_GRADE_POINT.get(x))).dropna()
        all_points.extend(pts.tolist())

    if not rows:
        return {
            "response_type": "pandangan",
            "message": ("No exam subjects could be detected in this dataset." if EN
                        else "Tiada subjek peperiksaan dapat dikesan dalam dataset ini."),
            "susulan": (["Show summary statistics"] if EN else ["Tunjukkan ringkasan statistik"]),
        }

    gps = round(sum(all_points) / len(all_points), 2) if all_points else None

    penemuan = []
    penemuan.append(
        (f"Overall school GPS: {gps} (lower is better; best = 0)." if EN
         else f"GPS keseluruhan sekolah: {gps} (rendah lebih baik; terbaik = 0).")
        if gps is not None else
        ("GPS could not be computed." if EN else "GPS tidak dapat dikira.")
    )
    best = min(gpmp_pairs, key=lambda x: x[1]) if gpmp_pairs else None
    worst = max(gpmp_pairs, key=lambda x: x[1]) if gpmp_pairs else None
    if best:
        penemuan.append(
            f"Strongest subject: {best[0]} (GPMP {best[1]}). Needs most attention: {worst[0]} (GPMP {worst[1]})."
            if EN else
            f"Subjek terbaik: {best[0]} (GPMP {best[1]}). Paling perlu perhatian: {worst[0]} (GPMP {worst[1]})."
        )
    low_pass = [c for c, p in pass_pairs if p < 50]
    if low_pass:
        penemuan.append(
            f"Subjects with pass rate below 50%: {', '.join(low_pass)}." if EN
            else f"Subjek dengan peratus lulus di bawah 50%: {', '.join(low_pass)}."
        )

    tafsiran = (
        "GPMP measures average grade points per subject and GPS averages across all subjects. "
        "These figures help identify which subjects need targeted intervention." if EN else
        "GPMP mengukur purata mata gred bagi setiap subjek dan GPS purata merentas semua subjek. "
        "Angka ini membantu mengenal pasti subjek yang memerlukan intervensi bersasar."
    )
    cadangan = (
        ["Focus intervention programmes on subjects with the highest GPMP and lowest pass rates.",
         "Share best practices from the strongest subject's teachers with other panels.",
         "Track these figures each term to measure improvement."] if EN else
        ["Fokuskan program intervensi pada subjek dengan GPMP tertinggi dan peratus lulus terendah.",
         "Kongsi amalan terbaik guru subjek terbaik dengan panel lain.",
         "Pantau angka ini setiap penggal untuk mengukur penambahbaikan."]
    )
    amaran = [
        ("Grade scale used — A+:90-100, A:80-89, A-:70-79, B+:65-69, B:60-64, C+:55-59, "
         "C:50-54, D:45-49, E:40-44, G:0-39. Pass = grade E and above; Distinction = A-/A/A+."
         if EN else
         "Skala gred digunakan — A+:90-100, A:80-89, A-:70-79, B+:65-69, B:60-64, C+:55-59, "
         "C:50-54, D:45-49, E:40-44, G:0-39. Lulus = gred E ke atas; Cemerlang = A-/A/A+.")
    ]

    # Chart: pass rate per subject (easy to read)
    pass_pairs_sorted = sorted(pass_pairs, key=lambda x: -x[1])
    chart = {
        "type": "bar",
        "title": ("Pass rate by subject (%)" if EN else "Peratus Lulus Mengikut Subjek (%)"),
        "labels": [c for c, _ in pass_pairs_sorted],
        "datasets": [{
            "label": "% Lulus" if not EN else "% Pass",
            "data": [p for _, p in pass_pairs_sorted],
            "backgroundColor": [_PALETTE[i % len(_PALETTE)] for i in range(len(pass_pairs_sorted))],
        }],
    }

    payload = {
        "response_type": "rumusan",
        "message": (f"Exam results analysis complete. School GPS: {gps}." if EN
                    else f"Analisis keputusan peperiksaan selesai. GPS sekolah: {gps}."),
        "penemuan": penemuan,
        "tafsiran": tafsiran,
        "cadangan": cadangan,
        "amaran": amaran,
        "table": {"headers": headers, "rows": rows},
        "chart": chart,
    }

    # Optional: GPS comparison by school or class
    group_col = edu.get("school_col") or edu.get("class_col")
    if group_col and edu["subjects"]:
        try:
            long_points = []
            for c in edu["subjects"]:
                pts = df[c].map(_mark_to_grade).map(lambda x: _GRADE_POINT.get(x))
                tmp = pd.DataFrame({"grp": df[group_col], "pt": pts}).dropna()
                long_points.append(tmp)
            allp = pd.concat(long_points, ignore_index=True)
            gps_by = allp.groupby("grp")["pt"].mean().round(2).sort_values()
            grp_label = ("School" if EN else "Sekolah") if group_col == edu.get("school_col") else ("Class" if EN else "Kelas")
            payload["table2"] = {
                "headers": [grp_label, "GPS"],
                "rows": [[str(k), float(v)] for k, v in gps_by.items()],
            }
            payload["penemuan"].append(
                f"Best-performing {grp_label.lower()}: {gps_by.index[0]} (GPS {gps_by.iloc[0]})."
                if EN else
                f"{grp_label} berprestasi terbaik: {gps_by.index[0]} (GPS {gps_by.iloc[0]})."
            )
        except Exception:
            pass

    payload["susulan"] = (
        ["Analyse attendance", "Show grade distribution for each subject", "Compare classes"] if EN else
        ["Analisis kehadiran", "Tunjukkan taburan gred setiap subjek", "Bandingkan kelas"]
    )
    return payload


def _attendance_analysis(df: pd.DataFrame, edu: dict, lang: str = "bm") -> dict:
    EN = lang == "en"
    col = edu.get("attendance_col")
    if not col:
        return {
            "response_type": "pandangan",
            "message": ("No attendance column was detected in this dataset." if EN
                        else "Tiada lajur kehadiran dapat dikesan dalam dataset ini."),
            "susulan": (["Analyse exam results"] if EN else ["Analisis keputusan peperiksaan"]),
        }
    s = pd.to_numeric(df[col], errors="coerce")
    if s.dropna().empty:
        return {
            "response_type": "pandangan",
            "message": ("The attendance column has no numeric values to analyse." if EN
                        else "Lajur kehadiran tiada nilai numerik untuk dianalisis."),
            "susulan": (["Analyse exam results"] if EN else ["Analisis keputusan peperiksaan"]),
        }
    # Normalise fraction (0-1) to percentage
    if s.max() <= 1.5:
        s = s * 100
    avg = round(float(s.mean()), 1)
    at_risk_mask = s < 80
    n_risk = int(at_risk_mask.sum())
    n_total = int(s.notna().sum())
    risk_pct = round(n_risk / max(1, n_total) * 100, 1)

    penemuan = [
        (f"Average attendance: {avg}%." if EN else f"Purata kehadiran: {avg}%."),
        (f"{n_risk} of {n_total} students ({risk_pct}%) are at risk with attendance below 80%."
         if EN else
         f"{n_risk} daripada {n_total} murid ({risk_pct}%) berisiko dengan kehadiran di bawah 80%."),
    ]

    # At-risk list
    name_col = edu.get("name_col")
    class_col = edu.get("class_col")
    show_cols, headers = [], []
    if name_col:
        show_cols.append(name_col); headers.append("Name" if EN else "Nama")
    if class_col:
        show_cols.append(class_col); headers.append("Class" if EN else "Kelas")
    headers.append("Attendance %" if EN else "Kehadiran %")
    risk_df = df.loc[at_risk_mask, show_cols].copy() if show_cols else pd.DataFrame(index=df.index[at_risk_mask])
    risk_df["_att"] = s[at_risk_mask].round(1)
    risk_df = risk_df.sort_values("_att").head(25)
    rows = [[*(str(r[c]) for c in show_cols), float(r["_att"])] for _, r in risk_df.iterrows()]

    # Average by class or school
    chart = None
    group_col = edu.get("class_col") or edu.get("school_col")
    if group_col:
        try:
            by = pd.DataFrame({"grp": df[group_col], "att": s}).dropna().groupby("grp")["att"].mean().round(1).sort_values()
            chart = {
                "type": "bar",
                "title": (f"Average attendance by {group_col} (%)" if EN
                          else f"Purata Kehadiran Mengikut {group_col} (%)"),
                "labels": [str(k) for k in by.index],
                "datasets": [{"label": "% " + ("Attendance" if EN else "Kehadiran"),
                              "data": [float(v) for v in by.values],
                              "backgroundColor": [_PALETTE[i % len(_PALETTE)] for i in range(len(by))]}],
            }
        except Exception:
            chart = None

    payload = {
        "response_type": "rumusan",
        "message": (f"Attendance analysis complete. Average attendance is {avg}%, with {n_risk} at-risk students."
                    if EN else
                    f"Analisis kehadiran selesai. Purata kehadiran ialah {avg}%, dengan {n_risk} murid berisiko."),
        "penemuan": penemuan,
        "tafsiran": (
            "Students below 80% attendance are flagged as at-risk, in line with common KPM practice. "
            "Low attendance often correlates with weaker academic performance." if EN else
            "Murid dengan kehadiran di bawah 80% ditanda sebagai berisiko, selaras dengan amalan lazim KPM. "
            "Kehadiran rendah sering berkait dengan pencapaian akademik yang lebih lemah."),
        "cadangan": (
            ["Contact the guardians of at-risk students to understand the causes.",
             "Run a targeted attendance-improvement programme for the flagged classes.",
             "Review attendance again next month to measure progress."] if EN else
            ["Hubungi penjaga murid berisiko untuk memahami puncanya.",
             "Jalankan program peningkatan kehadiran bersasar untuk kelas yang ditanda.",
             "Semak semula kehadiran bulan hadapan untuk mengukur kemajuan."]),
        "amaran": [
            ("At-risk threshold set at 80%. Adjust if your school uses a different benchmark." if EN
             else "Ambang berisiko ditetapkan pada 80%. Laraskan jika sekolah anda menggunakan penanda aras berbeza.")
        ],
        "susulan": (["Analyse exam results", "List students below 60% attendance"] if EN
                    else ["Analisis keputusan peperiksaan", "Senaraikan murid berkehadiran bawah 60%"]),
    }
    if rows:
        payload["table"] = {"headers": headers, "rows": rows}
    if chart:
        payload["chart"] = chart
    return payload


# Keyword → template routing (checked before the LLM plan-execute stage)
_EXAM_KEYWORDS = (
    "analisis keputusan peperiksaan", "keputusan peperiksaan", "analisis peperiksaan",
    "analisa peperiksaan", "taburan gred", "gpmp", "gps sekolah", "peratus lulus",
    "analyse exam", "analyze exam", "exam result", "exam analysis", "grade distribution",
)
_ATTENDANCE_KEYWORDS = (
    "analisis kehadiran", "analisa kehadiran", "murid berisiko", "kehadiran rendah",
    "attendance analysis", "analyse attendance", "analyze attendance", "at-risk", "at risk student",
)


def _maybe_run_education_template(query: str, df: pd.DataFrame, lang: str) -> dict | None:
    q = query.lower()
    edu = _detect_education_columns(df)
    if any(k in q for k in _EXAM_KEYWORDS) and _has_education_data(edu):
        return _exam_analysis(df, edu, lang)
    if any(k in q for k in _ATTENDANCE_KEYWORDS) and edu.get("attendance_col"):
        return _attendance_analysis(df, edu, lang)
    return None


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

    df = _get_df(session_id)

    # Education templates (exam/attendance) — deterministic, computed with pandas.
    if df is not None and data_context:
        template = _maybe_run_education_template(query, df, lang)
        if template is not None:
            topic_hint = query[:60]
            _add_explored(session_id, topic_hint)
            return json.dumps(template, ensure_ascii=False)

    # Plan→Execute→Narrate: LLM plans pandas ops, server computes them on the
    # FULL dataset, and the narration below may only use those real numbers.
    if df is not None and data_context:
        computed = _plan_and_compute(query, df)
        if computed:
            data = get_session_data(session_id) or {}
            raw_block = ""
            full_csv = data.get("full_data", "")
            if len(full_csv) <= 12000:
                raw_block = f"\n\nDATA PENUH (CSV):\n{full_csv}"
            data_context = f"\n\nRINGKASAN DATA:\n{data.get('summary', '')}" + raw_block + computed

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
