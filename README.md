# SafeCart — Scraping Data Pipeline

Repositori ini memuat seluruh *pipeline* (pengumpulan data, pembersihan, dan standarisasi) untuk mengumpulkan dataset pendukung proyek **SafeCart**. Kami mengumpulkan data referensi produk, kemasan, hingga daftar produk BPOM dari berbagai sumber.

## 🏗️ Arsitektur Proyek

Repositori ini dibagi menjadi 3 modul utama, masing-masing menangani sumber data yang berbeda secara terisolasi. Silakan masuk ke masing-masing folder untuk melihat dokumentasi teknisnya:

1. **[Dokumentasi Tokopedia](Scraping%20Data%20Tokopedia/README.md)**
   Pipeline lengkap untuk mencari produk di Tokopedia, mengunduh gambar kemasannya, serta membersihkan noise/iklan menggunakan AI (MobileNetV2).

2. **[Dokumentasi BPOM](Scraping%20Data%20BPOM/README.md)**
   Pipeline untuk mengambil dataset resmi izin edar kosmetik dan makanan dari situs BPOM. Data ini menjadi *ground truth* pendaftaran produk.

3. **[Dokumentasi Sociolla](Scraping%20Data%20Sociolla/README.md)**
   Pipeline untuk mengumpulkan gambar referensi dari Sociolla dan Serper API, membedakan packaging *fake vs real*, dan melakukan deduksi visual produk kecantikan.

---

## 🚀 Persiapan Lingkungan (Setup)

Seluruh dependensi untuk ketiga modul di atas telah disentralisasi. Anda cukup melakukan setup satu kali di folder utama (*root*) ini.

### 1. Install Library
Pastikan Anda menggunakan Python 3.9+ dan jalankan:
```bash
pip install -r requirements.txt
playwright install
```

### 2. Setup Environment Variables (.env)
Beberapa pipeline (seperti BPOM dan Serper) membutuhkan akses API Token. 
1. Copy file `.env.example` menjadi `.env`:
   ```bash
   cp .env.example .env
   ```
2. Buka file `.env` dan isikan token yang diperlukan (Jangan pernah commit file ini!):
   ```env
   BPOM_ACCESS_TOKEN=token_anda_disini
   SERPER_API_KEY=token_anda_disini
   ```

---

## 🤝 Berkontribusi & Catatan Khusus
- **Resume otomatis:** Semua script di repository ini mendukung *resume*. Jika scraping terputus (crash, internet mati, dll.), cukup jalankan ulang dan script akan melanjutkan dari titik terakhir.
- **Isolasi Folder:** Saat menambahkan fitur baru, usahakan menambahkannya ke dalam modul folder yang sesuai (Tokopedia/BPOM/Sociolla) agar *root* repository tetap bersih.
- **Anti-bot Deteksi:** Sebagian besar scraper menggunakan `playwright-stealth` dan menyimpan profil sesi untuk menghindari pemblokiran Cloudflare/Captcha.
