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


def get_indexed_files(conn) -> set:
    """Return set of source_file names already in the database."""
    rows = conn.execute("SELECT DISTINCT source_file FROM kpm_documents").fetchall()
    return {row[0] for row in rows}


def remove_document(conn, source_file: str):
    """Remove all chunks for a given source file."""
    conn.execute("DELETE FROM kpm_documents WHERE source_file = ?", (source_file,))
    conn.commit()


def ingest_pdf(pdf_path: Path, conn) -> int:
    """Ingest a single PDF. Returns number of chunks added."""
    text = extract_text(pdf_path)
    if not text:
        print(f"  [SKIP] Tiada teks diekstrak (mungkin PDF imej)")
        return 0

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

    print(f"  [OK] {len(chunks)} bahagian diindeks (kategori: {category}, {len(text)} aksara)")
    return len(chunks)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ingest KPM PDF documents into knowledge base")
    parser.add_argument("--reset", action="store_true", help="Kosongkan semua dokumen dan ingest semula")
    parser.add_argument("--file", type=str, help="Ingest fail PDF tertentu sahaja (nama fail dalam Dokumen KPM_Support/)")
    parser.add_argument("--remove", type=str, help="Padam dokumen tertentu dari knowledge base (nama fail)")
    args = parser.parse_args()

    conn = _get_conn()

    # Handle --remove
    if args.remove:
        indexed = get_indexed_files(conn)
        if args.remove in indexed:
            remove_document(conn, args.remove)
            count = conn.execute("SELECT COUNT(*) FROM kpm_documents").fetchone()[0]
            print(f"[OK] '{args.remove}' dipadam. Jumlah dokumen dalam indeks: {count}")
        else:
            print(f"[WARN] '{args.remove}' tidak dijumpai dalam database.")
            print(f"Fail sedia ada: {sorted(indexed)}")
        return

    if not DOCS_DIR.exists():
        print(f"Direktori tidak ditemui: {DOCS_DIR}")
        return

    # Handle --reset
    if args.reset:
        conn.execute("DELETE FROM kpm_documents")
        conn.execute("DELETE FROM kpm_documents_fts")
        conn.commit()
        print("Database dikosongkan. Memulakan ingest semula...")

    # Handle --file (single file)
    if args.file:
        pdf_path = DOCS_DIR / args.file
        if not pdf_path.exists():
            print(f"[ERR] Fail tidak dijumpai: {pdf_path}")
            return
        indexed = get_indexed_files(conn)
        if args.file in indexed and not args.reset:
            print(f"[INFO] '{args.file}' sudah ada dalam database. Mengemas kini...")
            remove_document(conn, args.file)
        print(f"\nMemproses: {args.file}")
        try:
            total_chunks = ingest_pdf(pdf_path, conn)
        except Exception as e:
            print(f"  [ERR] Ralat: {e}")
            return
        final_count = conn.execute("SELECT COUNT(*) FROM kpm_documents").fetchone()[0]
        print(f"\nSelesai. Jumlah dokumen dalam indeks: {final_count} ({total_chunks} bahagian baharu)")
        return

    # Default: ingest all PDFs, skip already-indexed ones (unless --reset)
    pdf_files = list(DOCS_DIR.glob("*.pdf"))
    print(f"Dijumpai {len(pdf_files)} fail PDF dalam {DOCS_DIR}")

    indexed = get_indexed_files(conn)
    if indexed and not args.reset:
        new_files = [p for p in pdf_files if p.name not in indexed]
        skipped = len(pdf_files) - len(new_files)
        print(f"  Sudah diindeks: {skipped} fail (dilangkau)")
        print(f"  Akan diindeks: {len(new_files)} fail baharu")
        pdf_files = new_files

    if not pdf_files:
        print("\nTiada dokumen baharu untuk diindeks.")
        final_count = conn.execute("SELECT COUNT(*) FROM kpm_documents").fetchone()[0]
        print(f"Jumlah dokumen dalam indeks: {final_count}")
        return

    total_chunks = 0
    for pdf_path in sorted(pdf_files):
        print(f"\nMemproses: {pdf_path.name}")
        try:
            total_chunks += ingest_pdf(pdf_path, conn)
        except Exception as e:
            print(f"  [ERR] Ralat: {e}")

    final_count = conn.execute("SELECT COUNT(*) FROM kpm_documents").fetchone()[0]
    print(f"\nSelesai. Jumlah dokumen dalam indeks: {final_count} ({total_chunks} bahagian baharu)")


if __name__ == "__main__":
    main()
