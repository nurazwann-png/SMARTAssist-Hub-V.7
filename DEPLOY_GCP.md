# Panduan Deploy SMARTAssist Hub ke GCP

## Gambaran Keseluruhan Fasa

```
Fasa 1 → Setup & Prasyarat        (~30 minit)
Fasa 2 → Database: Cloud SQL       (~20 minit)
Fasa 3 → Rahsia: Secret Manager    (~15 minit)
Fasa 4 → Storan: Cloud Storage     (~20 minit)
Fasa 5 → Build & Deploy Cloud Run  (~20 minit)
Fasa 6 → Pasca-Deploy              (~15 minit)
```

---

## Fasa 1 — Setup & Prasyarat

### 1.1 Install Google Cloud CLI

Muat turun dari: https://cloud.google.com/sdk/docs/install

Selepas install, log masuk:

```bash
gcloud auth login
gcloud auth application-default login
```

### 1.2 Buat Projek GCP Baru

```bash
gcloud projects create smartassist-hub --name="SMARTAssist Hub"
gcloud config set project smartassist-hub
```

> **Nota:** Nama projek mestilah unik secara global. Tukar `smartassist-hub` kepada nama lain jika sudah diambil.

### 1.3 Aktifkan Billing

Pergi ke: https://console.cloud.google.com/billing  
Sambungkan akaun billing ke projek `smartassist-hub`.

### 1.4 Aktifkan API Yang Diperlukan

```bash
gcloud services enable \
  run.googleapis.com \
  sql-component.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

### 1.5 Tetapkan Rantau (Region)

```bash
gcloud config set run/region asia-southeast1
```

> `asia-southeast1` = Singapura — paling hampir dengan Malaysia.

---

## Fasa 2 — Database: Cloud SQL (PostgreSQL)

### 2.1 Buat Instance Cloud SQL

```bash
gcloud sql instances create smartassist-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=asia-southeast1 \
  --storage-size=10GB \
  --storage-auto-increase \
  --backup-start-time=02:00 \
  --availability-type=zonal
```

> `db-f1-micro` = ~USD 7/bulan. Naik ke `db-g1-small` (~USD 25/bulan) untuk production sebenar.

### 2.2 Tetapkan Password PostgreSQL

```bash
gcloud sql users set-password postgres \
  --instance=smartassist-db \
  --password=GANTI_DENGAN_PASSWORD_KUAT
```

### 2.3 Buat Database

```bash
gcloud sql databases create smartassist \
  --instance=smartassist-db
```

### 2.4 Jalankan Schema

Sambung ke database melalui Cloud SQL Proxy:

```bash
# Terminal 1 — jalankan proxy
gcloud sql auth-proxy smartassist-hub:asia-southeast1:smartassist-db --port=5433

# Terminal 2 — jalankan schema
DATABASE_URL=postgresql://postgres:PASSWORD@127.0.0.1:5433/smartassist \
  python database/run_migration.py
```

> Ganti `PASSWORD` dengan password yang anda tetapkan di langkah 2.2.

### 2.5 Ambil Connection Name

```bash
gcloud sql instances describe smartassist-db --format="value(connectionName)"
# Output contoh: smartassist-hub:asia-southeast1:smartassist-db
```

Simpan output ini — diperlukan di Fasa 3 dan 5.

---

## Fasa 3 — Rahsia: Secret Manager

Jangan simpan rahsia dalam image Docker atau environment variables yang boleh dilihat. Guna Secret Manager.

### 3.1 Simpan Semua Rahsia

```bash
# DeepSeek API Key
echo -n "sk-XXXX" | \
  gcloud secrets create DEEPSEEK_API_KEY --data-file=-

# Google OAuth
echo -n "617886577219-XXX.apps.googleusercontent.com" | \
  gcloud secrets create GOOGLE_CLIENT_ID --data-file=-

echo -n "GOCSPX-XXXX" | \
  gcloud secrets create GOOGLE_CLIENT_SECRET --data-file=-

# Session secret (ambil dari .env anda)
echo -n "fb88ebe4b4ccc..." | \
  gcloud secrets create SESSION_SECRET_KEY --data-file=-

# DATABASE_URL untuk Cloud SQL
# Format: postgresql://postgres:PASSWORD@/smartassist?host=/cloudsql/CONNECTION_NAME
echo -n "postgresql://postgres:PASSWORD@/smartassist?host=/cloudsql/smartassist-hub:asia-southeast1:smartassist-db" | \
  gcloud secrets create DATABASE_URL --data-file=-
```

### 3.2 Beri Akses ke Service Account Cloud Run

```bash
# Ambil nombor projek
PROJECT_NUMBER=$(gcloud projects describe smartassist-hub --format="value(projectNumber)")

# Beri akses baca rahsia
gcloud projects add-iam-policy-binding smartassist-hub \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Fasa 4 — Storan: Cloud Storage

Fail yang diupload pengguna (letterhead, imej laporan) perlu disimpan di luar container kerana Cloud Run adalah stateless.

### 4.1 Buat Bucket

```bash
gcloud storage buckets create gs://smartassist-hub-uploads \
  --location=asia-southeast1 \
  --uniform-bucket-level-access
```

### 4.2 Pindah Letterhead Sedia Ada

```bash
gcloud storage cp static/letterheads/* \
  gs://smartassist-hub-uploads/letterheads/
```

### 4.3 Kod — Kemaskini Path Storan (Selepas Deploy)

> **Nota:** Untuk fasa pertama deploy, letterheads yang diupload baru tidak akan kekal selepas container restart. Ini boleh diterima untuk fasa awal. Kemaskini ke Cloud Storage selepas sistem stabil.

---

## Fasa 5 — Build & Deploy ke Cloud Run

### 5.1 Buat Artifact Registry Repository

```bash
gcloud artifacts repositories create smartassist-repo \
  --repository-format=docker \
  --location=asia-southeast1
```

### 5.2 Build & Push Docker Image

```bash
# Dari folder projek anda
gcloud builds submit \
  --tag asia-southeast1-docker.pkg.dev/smartassist-hub/smartassist-repo/app:latest
```

> Ini menggunakan Cloud Build — tidak perlu Docker install di komputer anda.

### 5.3 Deploy ke Cloud Run

```bash
gcloud run deploy smartassist-hub \
  --image asia-southeast1-docker.pkg.dev/smartassist-hub/smartassist-repo/app:latest \
  --region asia-southeast1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --concurrency 80 \
  --timeout 300 \
  --add-cloudsql-instances smartassist-hub:asia-southeast1:smartassist-db \
  --set-secrets "DEEPSEEK_API_KEY=DEEPSEEK_API_KEY:latest" \
  --set-secrets "GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest" \
  --set-secrets "GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest" \
  --set-secrets "SESSION_SECRET_KEY=SESSION_SECRET_KEY:latest" \
  --set-secrets "DATABASE_URL=DATABASE_URL:latest" \
  --set-env-vars "ENV=production,ALLOWED_EMAIL_DOMAINS=moe.gov.my,moe-dl.edu.my"
```

### 5.4 Ambil URL Aplikasi

```bash
gcloud run services describe smartassist-hub \
  --region asia-southeast1 \
  --format="value(status.url)"
# Contoh output: https://smartassist-hub-xxxx-as.a.run.app
```

---

## Fasa 6 — Pasca-Deploy

### 6.1 Kemaskini Google OAuth Redirect URI

1. Pergi ke: https://console.cloud.google.com/apis/credentials
2. Klik OAuth 2.0 Client ID anda
3. Tambah di **Authorized redirect URIs**:
   ```
   https://smartassist-hub-xxxx-as.a.run.app/auth/callback
   ```
4. Simpan

### 6.2 Uji Login

```bash
# Buka dalam browser
open https://smartassist-hub-xxxx-as.a.run.app
```

Cuba log masuk dengan akaun `@moe.gov.my` atau `@moe-dl.edu.my`.

### 6.3 Domain Custom (Pilihan)

Jika anda ada domain sendiri (contoh: `smartassist.moe.gov.my`):

```bash
gcloud run domain-mappings create \
  --service smartassist-hub \
  --domain smartassist.moe.gov.my \
  --region asia-southeast1
```

Kemudian tambah rekod DNS yang diberikan ke domain registrar anda.

### 6.4 Semak Log

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=smartassist-hub" \
  --limit 50 \
  --format "table(timestamp, textPayload)"
```

---

## Kos Anggaran (Bulanan)

| Perkhidmatan | Spesifikasi | Anggaran Kos |
|---|---|---|
| Cloud Run | 1 CPU, 1GB RAM, ~1000 req/hari | USD 0–5 |
| Cloud SQL | db-f1-micro, 10GB | USD 7–10 |
| Cloud Storage | 5GB uploads | USD 0.10 |
| Secret Manager | 6 secrets | USD 0.06 |
| Artifact Registry | 1GB image | USD 0.10 |
| **Jumlah** | | **~USD 8–15/bulan** |

---

## Perintah Berguna Selepas Deploy

```bash
# Deploy semula selepas perubahan kod
gcloud builds submit --tag asia-southeast1-docker.pkg.dev/smartassist-hub/smartassist-repo/app:latest
gcloud run deploy smartassist-hub --image asia-southeast1-docker.pkg.dev/smartassist-hub/smartassist-repo/app:latest --region asia-southeast1

# Lihat semua environment variables
gcloud run services describe smartassist-hub --region asia-southeast1 --format=yaml

# Kemaskini satu secret
echo -n "nilai_baru" | gcloud secrets versions add DEEPSEEK_API_KEY --data-file=-

# Scale down (jimat kos semasa tidak digunakan)
gcloud run services update smartassist-hub --region asia-southeast1 --min-instances 0
```

---

## Masalah Lazim

| Masalah | Sebab | Penyelesaian |
|---|---|---|
| `Cloud SQL connection failed` | DATABASE_URL salah format | Pastikan guna `?host=/cloudsql/...` bukan `@localhost` |
| `OAuth redirect_uri mismatch` | URI belum ditambah di Google Console | Tambah URL Cloud Run di OAuth credentials |
| `Container failed to start` | Error dalam kod | Semak log: `gcloud logging read ...` |
| `Memory limit exceeded` | App guna terlalu banyak RAM | Naik ke `--memory 2Gi` |
| `File upload hilang selepas restart` | Static files tidak kekal | Integrate Cloud Storage (Fasa 4 lanjutan) |
