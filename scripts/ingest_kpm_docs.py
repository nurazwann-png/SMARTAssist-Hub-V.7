"""Ingest KPM PDF documents into the kpm_documents SQLite table."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pdfplumber
from pathlib import Path
from backend.mcp_server import insert_document, _get_conn

DOCS_DIR = Path(__file__).resolve().parent.parent / "Dokumen KPM_Support"

CATEGORY_MAP = {
    "EMIS": ["EMIS", "emis"],
    "INFRASTRUKTUR": ["INFRA", "Infrastruktur"],
    "DTP": ["DTP"],
    "POLISI": ["SPI", "Garis_Panduan", "Pelantikan"],
    "SK@S": ["SK@S", "SKAS"],
    "ScPT": ["ScPT"],
}


def detect_category(filename: str) -> str:
    for cat, keywords in CATEGORY_MAP.items():
        if any(kw.lower() in filename.lower() for kw in keywords):
            return cat
    return "UMUM"


def extract_text(pdf_path: Path) -> str:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
    return "\n\n".join(pages)


def chunk_text(text: str, title: str, max_chars: int = 3000) -> list[dict]:
    """Split long documents into chunks for better retrieval."""
    if len(text) <= max_chars:
        return [{"title": title, "content": text}]

    paragraphs = text.split("\n\n")
    chunks = []
    current = ""
    chunk_idx = 1

    for para in paragraphs:
        if len(current) + len(para) > max_chars and current:
            chunks.append({
                "title": f"{title} (Bahagian {chunk_idx})",
                "content": current.strip(),
            })
            chunk_idx += 1
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para

    if current.strip():
        chunks.append({
            "title": f"{title} (Bahagian {chunk_idx})" if chunk_idx > 1 else title,
            "content": current.strip(),
        })

    return chunks


def main():
    conn = _get_conn()
    existing = conn.execute("SELECT COUNT(*) FROM kpm_documents").fetchone()[0]
    if existing > 0:
        print(f"Database sudah mengandungi {existing} dokumen. Kosongkan dahulu? (y/n)")
        if input().strip().lower() == "y":
            conn.execute("DELETE FROM kpm_documents")
            conn.execute("DELETE FROM kpm_documents_fts")
            conn.commit()
            print("Database dikosongkan.")
        else:
            print("Menambah dokumen baharu...")

    if not DOCS_DIR.exists():
        print(f"Direktori tidak ditemui: {DOCS_DIR}")
        return

    pdf_files = list(DOCS_DIR.glob("*.pdf"))
    print(f"Dijumpai {len(pdf_files)} fail PDF dalam {DOCS_DIR}")

    total_chunks = 0
    for pdf_path in sorted(pdf_files):
        print(f"\nMemproses: {pdf_path.name}")
        try:
            text = extract_text(pdf_path)
            if not text:
                print(f"  [SKIP] Tiada teks diekstrak (mungkin PDF imej)")
                continue

            category = detect_category(pdf_path.name)
            title = pdf_path.stem.replace("-", " ").replace("_", " ").strip()
            chunks = chunk_text(text, title)

            for chunk in chunks:
                insert_document(
                    title=chunk["title"],
                    content=chunk["content"],
                    category=category,
                    source_file=pdf_path.name,
                )

            total_chunks += len(chunks)
            print(f"  [OK]{len(chunks)} bahagian diindeks (kategori: {category}, {len(text)} aksara)")

        except Exception as e:
            print(f"  [ERR]Ralat: {e}")

    final_count = conn.execute("SELECT COUNT(*) FROM kpm_documents").fetchone()[0]
    print(f"\nSelesai. Jumlah dokumen dalam indeks: {final_count} ({total_chunks} bahagian baharu)")


if __name__ == "__main__":
    main()
