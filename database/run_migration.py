"""
Jalankan semua migration SQL ke database smartassist.
Penggunaan: python database/run_migration.py
"""
import os, sys, psycopg2
from pathlib import Path

# Baca DATABASE_URL dari .env
db_url = None
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            db_url = line.split("=", 1)[1].strip()
            break

if not db_url:
    db_url = "postgresql://postgres:postgres@127.0.0.1:5432/smartassist"

# Ganti localhost dengan 127.0.0.1 untuk elak isu IPv6
db_url = db_url.replace("@localhost:", "@127.0.0.1:")

schema_file = Path(__file__).parent / "schema.sql"
migrations = [schema_file] + sorted(Path(__file__).parent.glob("migration_*.sql"))

try:
    conn = psycopg2.connect(db_url, options="-c search_path=public")
    conn.autocommit = True
    cur = conn.cursor()

    # Ensure public schema exists and user has create rights (PostgreSQL 15+)
    cur.execute("CREATE SCHEMA IF NOT EXISTS public")
    cur.execute("GRANT ALL ON SCHEMA public TO postgres")
    cur.execute("SET search_path TO public")
    cur.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    for mig in migrations:
        print(f"Menjalankan {mig.name}...")
        sql = mig.read_text(encoding="utf-8")
        cur.execute(sql)
        print(f"  ✓ {mig.name} selesai")

    print("\nSemua migration berjaya dijalankan.")

    # Tunjukkan semua table sekarang
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
    tables = [r[0] for r in cur.fetchall()]
    print(f"\nJumlah table dalam DB: {len(tables)}")
    for t in tables:
        print(f"  - {t}")

    conn.close()

except Exception as e:
    print(f"RALAT: {e}")
    if 'conn' in locals():
        conn.rollback()
        conn.close()
    sys.exit(1)
