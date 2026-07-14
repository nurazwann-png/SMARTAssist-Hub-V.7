# SMARTAssist Hub — PostgreSQL Database

## Cara Sediakan

### 1. Buat database
```sql
CREATE DATABASE smartassist;
```

### 2. Jalankan schema
```bash
psql -U postgres -d smartassist -f database/schema.sql
```

### 3. Tetapkan DATABASE_URL dalam .env
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/smartassist
```

### 4. Pasang driver Python
```bash
pip install psycopg2-binary
```

### 5. (Pilihan) Pindah data dari SQLite
```bash
python database/migrate_sqlite_to_pg.py
```

---

## Jadual & Tujuan

| Jadual | Tujuan |
|---|---|
| `user_profiles` | Profil pengguna (dari Google OAuth) |
| `sessions` | Metadata sesi perbualan |
| `messages` | Sejarah mesej chat |
| `kv_store` | Keadaan ejen per-sesi (JSON serba-guna) |
| `feedback` | Maklum balas 👍/👎 pengguna |
| `letterheads` | Fail kop surat & logo |
| `generated_letters` | Surat rasmi & memo yang dijana |
| `generated_reports` | Laporan satu muka surat yang dijana |
| `report_images` | Imej yang dimuat naik untuk laporan |
| `document_reviews` | Keputusan semakan dokumen (skor, isu) |
| `uploaded_datasets` | Set data CSV/Excel untuk analisis |
