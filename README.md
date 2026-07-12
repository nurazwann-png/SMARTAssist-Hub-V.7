# SMARTAssist Hub V.7

> **Multi-Agent AI Assistant Platform for PPD / KPM**
> Selamat Datang ke SMARTAssist Hub — sistem AI pelbagai ejen untuk membantu pegawai pendidikan daerah menjalankan kerja pentadbiran dengan lebih cepat dan tepat.

---

## Gambaran Keseluruhan

SMARTAssist Hub menyediakan **5 ejen AI khusus** dalam satu aplikasi web. Setiap ejen dilatih untuk tugas tertentu dan menghasilkan output dalam format rasmi KPM — lengkap dengan kepala surat, logo, dan frasa wajib seperti *"MALAYSIA MADANI"* dan *"BERKHIDMAT UNTUK NEGARA"*.

| Ejen | Fungsi |
|------|--------|
| 📊 **Analisis Data** | Baca fail CSV/Excel, jana carta interaktif, statistik dan ringkasan |
| ✉️ **Penjana Surat Rasmi** | Jana surat rasmi & memo dalaman format KPM, muat turun `.docx` |
| 📋 **Penjana Laporan** | Jana One Page Report format PPD/KPM secara automatik |
| 📝 **Semakan Dokumen** | Semak tatabahasa, format, dan pematuhan dokumen (PDF/Word) |
| 🛟 **Sokongan KPM** | Jawab soalan sistem EMIS, APDM, DTPCare, SK@S berdasarkan dokumen rujukan rasmi |

---

## Ciri-ciri Utama

- 🤖 **5 ejen AI khusus** — setiap ejen ada personaliti, peraturan, dan format output tersendiri
- 📄 **Jana dokumen Word** — surat rasmi dan laporan dengan kepala surat dan logo automatik
- 📊 **Carta interaktif** — bar, line, pie dengan eksport ke PowerPoint dan PDF
- ✏️ **Kemaskini separa** — tukar bahagian dokumen tanpa jana semula keseluruhan
- 👍 **Sistem maklum balas** — butang thumbs up/down pada setiap respons AI
- 📈 **Papan pemuka admin** — statistik penggunaan, maklum balas, dan sesi terkini
- 🌐 **Dwibahasa** — antara muka Bahasa Malaysia / English
- 💾 **Penyimpanan data** — fail CSV yang dimuat naik disimpan ke cakera (tahan restart)
- 📧 **Hantar emel** — dokumen siap boleh dihantar terus melalui emel

---

## Teknologi

| Lapisan | Teknologi |
|---------|-----------|
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **AI Engine** | DeepSeek LLM (via REST API) |
| **Frontend** | Vanilla HTML / CSS / JavaScript, Chart.js |
| **Data** | pandas, openpyxl |
| **Dokumen Word** | python-docx |
| **Eksport** | reportlab (PDF), python-pptx (PowerPoint) |
| **Baca PDF** | pdfplumber |
| **Carian Dokumen** | TF-IDF (scikit-learn) |
| **Emel** | SMTP (smtplib) |

---

## Struktur Projek

```
SMARTAssist Hub V.7/
├── app.py                        # FastAPI server — semua endpoint API
├── requirements.txt
├── templates/
│   └── index.html                # Antara muka SPA (Single Page Application)
├── static/
│   ├── app.js                    # Logik frontend (SPA controller)
│   ├── style.css                 # Reka bentuk & tema
│   └── chart.min.js              # Chart.js (bundled)
├── agents/
│   ├── data_analysis.py          # Ejen Analisis Data
│   ├── letter_generator.py       # Ejen Penjana Surat Rasmi
│   ├── report_generator.py       # Ejen Penjana Laporan
│   ├── document_reviewer.py      # Ejen Semakan Dokumen
│   ├── kpm_support.py            # Ejen Sokongan KPM
│   └── data_analysis_export.py   # Eksport PPTX / PDF
├── backend/
│   ├── deepseek_client.py        # Wrapper panggilan LLM
│   ├── orchestrator.py           # Pengklasifikasi niat (intent classifier)
│   ├── mcp_server.py             # Carian dokumen KPM (TF-IDF)
│   └── letterhead_store.py       # Pengurusan kepala surat & logo
└── scripts/
    └── ingest_kpm_docs.py        # Skrip indeks dokumen KPM
```

---

## Persediaan & Pemasangan

### 1. Klon repository

```bash
git clone https://github.com/nurazwann-png/SMARTAssist-Hub-V.7.git
cd "SMARTAssist-Hub-V.7"
```

### 2. Pasang keperluan Python

```bash
pip install -r requirements.txt
```

### 3. Tetapkan pemboleh ubah persekitaran

Cipta fail `.env` di akar projek:

```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

# E-mel (pilihan — untuk fungsi hantar emel)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your@email.com
```

### 4. Indeks dokumen KPM (pilihan)

Letakkan fail PDF dokumen rujukan KPM ke dalam folder `Dokumen KPM_Support/`, kemudian jalankan:

```bash
python scripts/ingest_kpm_docs.py
```

### 5. Jalankan aplikasi

```bash
python app.py
```

Buka pelayar dan pergi ke: **http://localhost:8112**

---

## Keperluan Sistem

- Python 3.10 atau lebih baru
- Sambungan internet (untuk panggilan DeepSeek API)
- Kunci API DeepSeek (daftar di [platform.deepseek.com](https://platform.deepseek.com))

---

## Nota Keselamatan

> ⚠️ **Sistem ini belum mempunyai pengesahan pengguna (login).** Sesiapa yang mempunyai URL boleh mengakses sistem. Adalah disyorkan untuk menyekat akses melalui VPN atau firewall sebelum digunakan secara meluas.

Fail sensitif yang **tidak** disimpan di GitHub:
- `.env` — kunci API
- `Dokumen KPM_Support/` — dokumen dalaman KPM
- `static/letterheads/` — imej kepala surat yang dimuat naik
- `static/session_data/` — data CSV sesi pengguna

---

## Dokumentasi

Rujuk [SMARTAssist_Hub_Documentation.pdf](./SMARTAssist_Hub_Documentation.pdf) untuk penerangan lengkap sistem dalam Bahasa Inggeris, termasuk cara kerja ejen, teknologi yang digunakan, dan pelan penambahbaikan.

---

## Lesen

Projek ini dibangunkan untuk kegunaan dalaman Pejabat Pendidikan Daerah (PPD) dan Kementerian Pendidikan Malaysia (KPM).
