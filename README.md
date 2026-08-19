# SafeCart — Scraping Data Pipeline

Repo ini berisi seluruh pipeline untuk mengumpulkan, menggabungkan, dan membersihkan dataset gambar produk dari Tokopedia. Pipeline ini digunakan oleh tim SafeCart (Compfest 2026) untuk menyiapkan data training.

## Persiapan

```bash
pip install -r requirements.txt
playwright install
```

## Struktur Folder

```
SafeCart-ScrapingData/
├── Scraping Data Tokopedia/   # Pipeline Tokopedia lengkap (Scraping & Cleaning)
│   ├── scrape_tokopedia.py    # Tahap 1: Scraping produk dari Tokopedia
│   ├── merge_tokopedia.py     # Tahap 2: Gabungkan hasil scraping paralel
│   └── Clean Dataset Tokopedia/ # Tahap 3-5: Training model & cleaning
│       ├── sample_tokopedia.py  # Tahap 3: Ambil sampel untuk labeling
│       ├── train_tokopedia.py   # Tahap 4: Training model AI
│       ├── clean_tokopedia.py   # Tahap 5: Bersihkan dataset pakai model
│       ├── model/               # Folder berisi file model (.pth)
│       └── samples/             # Folder sampel (keep/discard)
├── requirements.txt           # Daftar library Python
└── README.md                  # File ini
```

## Pipeline Lengkap

### Tahap 1: Scraping (`scrape_tokopedia.py`)

Script ini membuka browser Chromium, mencari produk di Tokopedia, lalu mengunduh gambar dan metadata setiap produk.

**Cara menjalankan:**
```bash
cd "Scraping Data Tokopedia"
python scrape_tokopedia.py
```

**Konfigurasi yang perlu diubah:**

1. **Daftar produk** — ubah list `PRODUCTS` di bagian atas file (baris 15):
```python
# 1. UBAH NAMA PRODUK DI SINI:
# Tambahkan atau hapus nama produk yang ingin di-scrape
PRODUCTS = [
    "Blackmores Multivitamins Minerals",
    "Blackmores Bio C",
    # ... tambah/hapus sesuai kebutuhan
]
```

2. **Jumlah produk per keyword** — ubah `LIMIT_PER_KEYWORD` (baris 120):
```python
LIMIT_PER_KEYWORD = 20  # Berapa banyak product card yang di-scrape per keyword
```

3. **Mode browser** — ubah `HEADLESS` (baris 125):
```python
HEADLESS = False  # False = browser terlihat (untuk login manual pertama kali)
                  # True  = browser tersembunyi (untuk scraping otomatis)
```

4. **Folder output** — ubah `dataset_dir` di dalam fungsi `scrape_batch()` (baris 285):
```python
# 2. UBAH FOLDER OUTPUT DI SINI:
# "Data Obat Marketplace Tokopedia" adalah nama folder utamanya
dataset_dir = os.path.join(current_dir, "Data Obat Marketplace Tokopedia")
```

**Menjalankan paralel (scraping lebih cepat):**

Jika daftar produk sangat banyak, Anda bisa memecah pekerjaan ke beberapa folder:

1. Buat folder bernama `1/`, `2/`, `3/`, dst.
2. Copy `scrape_tokopedia.py` ke setiap folder.
3. Bagi list `PRODUCTS` di masing-masing copy (misalnya folder `1/` berisi produk 1-20, folder `2/` berisi produk 21-40, dst.)
4. Jalankan setiap script di terminal terpisah secara bersamaan.
5. Setelah selesai, gabungkan hasilnya menggunakan **Tahap 2** di bawah.

> **Catatan:** Pertama kali menjalankan, set `HEADLESS = False` agar browser terlihat. Anda mungkin perlu login ke Tokopedia secara manual. Setelah login, state-nya tersimpan di folder `chrome_profile/` dan tidak perlu login ulang.

---

### Tahap 2: Merge Dataset (`merge_tokopedia.py`)

Script ini menggabungkan hasil scraping yang dijalankan secara paralel di folder terpisah (misal folder `1/` sampai `6/`) menjadi satu folder utama.

**Kapan digunakan:** Hanya jika Anda menjalankan scraping paralel di beberapa folder. Jika scraping dilakukan di satu tempat saja, tahap ini bisa dilewati.

**Cara menjalankan:**
```bash
cd "Scraping Data Tokopedia"
python merge_tokopedia.py
```

**Konfigurasi yang perlu diubah:**

```python
# Pilih kategori dataset ("Obat Marketplace", "Makanan Marketplace", atau "Skincare Marketplace")
KATEGORI = "Obat Marketplace"

# Nama folder target akhir (tempat semua data digabungkan)
TARGET_DIR_NAME = "Gambar Obat Marketplace"

# Range folder part yang ingin digabungkan (1 sampai 6)
FOLDERS_RANGE = range(1, 7)
```

**Apa yang terjadi:**
- Script memindahkan (move) folder produk dari setiap part ke folder target.
- File `progress_tokopedia.json` dari semua part digabungkan agar tidak ada duplikasi.

---

### Tahap 3: Sampling (`Scraping Data Tokopedia/Clean Dataset Tokopedia/sample_tokopedia.py`)

Mengambil sampel acak dari dataset raw untuk dilabeli secara manual. Sampel ini akan menjadi data training untuk model AI di tahap selanjutnya.

**Cara menjalankan:**
```bash
cd "Scraping Data Tokopedia/Clean Dataset Tokopedia"
python sample_tokopedia.py
```

**Konfigurasi:**
```python
SAMPLES_PER_CATEGORY = 100  # Jumlah sampel acak per kategori
```

**Setelah sampling:**
Script akan membuat folder `samples/unlabeled/` berisi gambar acak. Tugas Anda:
1. Buka folder `samples/unlabeled/`
2. Pindahkan gambar yang **berisi kemasan produk** ke `samples/keep/`
3. Pindahkan gambar yang **berisi banner/infografis/marketing** ke `samples/discard/`
4. Hapus folder `samples/unlabeled/` jika sudah kosong (hanya sisakan `keep` dan `discard`).

---

### Tahap 4: Training Model (`Scraping Data Tokopedia/Clean Dataset Tokopedia/train_tokopedia.py`)

Melatih model MobileNetV2 menggunakan data yang sudah dilabeli di tahap 3. Output berupa file `.pth` di folder `model/`.

**Prasyarat:** Folder `samples/keep/` dan `samples/discard/` sudah berisi gambar berlabel.

**Cara menjalankan:**
```bash
cd "Scraping Data Tokopedia/Clean Dataset Tokopedia"
python train_tokopedia.py
```

**Konfigurasi:**
```python
EPOCHS = 10           # Jumlah iterasi training
BATCH_SIZE = 16       # Ukuran batch per iterasi
LEARNING_RATE = 0.001 # Learning rate optimizer
```

> **Catatan:** Model yang sudah di-training (`packaging_classifier.pth`) sudah tersedia di folder `model/`. Anda **tidak perlu** menjalankan tahap 3 dan 4 lagi jika hanya ingin membersihkan dataset baru — langsung lanjut ke tahap 5.

---

### Tahap 5: Cleaning Dataset (`Scraping Data Tokopedia/Clean Dataset Tokopedia/clean_tokopedia.py`)

Mesin utama. Script ini menggunakan model dari tahap 4 untuk memindai seluruh gambar dan memisahkan gambar produk bersih dari gambar marketing/infografis.

**Cara menjalankan:**
```bash
cd "Scraping Data Tokopedia/Clean Dataset Tokopedia"
python clean_tokopedia.py
```

**Konfigurasi:**
```python
TARGET_CATEGORY = "Gambar Makanan Tokopedia"  # None = proses semua kategori
CONFIDENCE_THRESHOLD = 0.6  # Minimum probability untuk "keep" (0.0 - 1.0)
```

**Output:**
- Gambar bersih disalin ke folder `Marketplace/clean/`
- Gambar marketing, infografis, dan file korup otomatis dibuang

> **Arsitektur Model:** Pipeline menggunakan model **MobileNetV2** (pre-trained ImageNet) yang di-fine-tune untuk klasifikasi biner dengan custom head (Dropout 0.2 + Linear 1280->2). Kecepatan inferensi ~1-2ms per gambar, sangat ringan dan cepat memfilter noise (iklan/banner) dari dataset.

---

## 📌 Dokumentasi Scraping Lainnya

- **BPOM (Badan Pengawas Obat dan Makanan):** [Dokumentasi Scraping BPOM](Scraping%20Data%20BPOM/README.md)
- **Sociolla:** [TBA]

---

## 🤝 Berkontribusi

### Catatan Penting
- **Resume otomatis:** Semua script mendukung resume. Jika scraping/cleaning terhenti (crash, captcha, dll.), cukup jalankan ulang dan akan melanjutkan dari posisi terakhir.
- **Anti-deteksi:** Script scraping menggunakan `playwright-stealth` dan persistent browser profile untuk menghindari deteksi bot.
- **GPU opsional:** Training dan cleaning bisa jalan di CPU, tapi akan lebih cepat jika ada GPU (CUDA).
