# SafeCart 91-Product Authenticity Evidence Dataset

Notebook ini dipakai untuk membuat dataset SafeCart dari **91 produk** skincare/kosmetik di `product.xlsx`.

Tujuannya adalah mengumpulkan gambar referensi produk, mencari listing marketplace, lalu mengumpulkan gambar yang punya kaitan dengan bukti publik tentang dugaan produk palsu. Dataset ini untuk riset/prototipe SafeCart.

> Penting: pipeline ini **tidak membuktikan** sebuah produk itu palsu. Label `reported_counterfeit_candidate` artinya hanya kandidat yang terhubung ke bukti publik, bukan counterfeit yang sudah pasti/terverifikasi.

## Isi data produk

File utama: `product.xlsx`

Kolom yang dipakai antara lain:

- `brand`
- `product_name`
- `bpom_id`
- `product_type`
- `size`
- `product_url`
- `ingredients_list`
- `description_product`

Notebook juga membuat `product_id` dari gabungan brand, nama produk, dan BPOM ID. Nilai tersebut diubah ke huruf besar, karakter selain huruf/angka diganti underscore (`_`).

## Alur pipeline

```text
product.xlsx
→ normalisasi data produk
→ cari gambar referensi
→ cari listing Shopee/Tokopedia
→ cari bukti publik terkait produk palsu
→ cek apakah teks bukti relevan
→ ambil gambar yang benar-benar terhubung ke sumber bukti
→ download dan cek kualitas gambar
→ OCR dan cek BPOM
→ hapus gambar duplikat
→ simpan CSV metadata
```

## Label gambar

| Label | Artinya |
| --- | --- |
| `genuine_reference` | Gambar referensi dari pencarian yang mengarah ke sumber official/authorized. Bukan bukti autentik secara laboratorium. |
| `reported_counterfeit_candidate` | Gambar yang terhubung ke bukti publik dengan teks terkait dugaan palsu. Ini kandidat, bukan confirmed counterfeit. |
| `unknown` | Gambar yang perlu dicek manual. Saat ini dipakai jika BPOM dari OCR tidak cocok dengan master data. |
| `rejected` | Gambar gagal didownload, gagal quality check, atau duplikat. |

Tidak ada label otomatis `counterfeit_confirmed` di pipeline ini.

## Mengumpulkan gambar referensi

Untuk tiap produk, notebook memakai query berikut:

- `{brand} {product_name} official`
- `{brand} {product_name} official website`
- `{brand} {product_name} Sociolla authorized retailer`

Gambar disimpan di:

```text
SafeCart_Dataset/images/genuine_reference/<product_id>/
```

Targetnya maksimal 8 gambar referensi per produk.

## Marketplace dan bukti dugaan palsu

Notebook mencari listing dari **Shopee** dan **Tokopedia** lewat fungsi `discover_marketplace_listings()`.

Listing marketplace biasa tidak otomatis dianggap palsu. Harga murah, rating rendah, seller tidak dikenal, atau sekadar muncul di marketplace juga bukan bukti palsu.

Pipeline mencari hasil publik dengan kata/frasa seperti:

- `palsu`, `fake`, `counterfeit`
- `tidak asli`, `tidak original`
- `barang palsu`, `produk palsu`
- `kemasan berbeda`
- `review palsu`, `fake product review`

Fungsi `classify_review_evidence()` mengecek apakah judul/snippet punya teks yang benar-benar berkaitan dengan dugaan palsu. Rating hanya pendukung, bukan syarat utama.

## Gambar kandidat harus punya hubungan dengan sumber bukti

Pipeline tidak boleh mengambil gambar marketplace secara acak lalu melabelinya kandidat palsu.

Urutannya:

1. Ambil gambar yang dideklarasikan langsung oleh halaman sumber bukti, misalnya `og:image` atau `twitter:image`.
2. Kalau tidak ada, lakukan pencarian gambar memakai URL sumber dan hanya terima hasil dengan source URL yang sama.

Kalau BPOM yang terbaca OCR tidak cocok dengan master data, gambar masuk `unknown` dan dicatat untuk manual review.

## Cek gambar dan duplikat

Gambar didownload sebagai bytes asli, divalidasi dengan Pillow, lalu dikonversi ke JPG. Metadata yang dicatat termasuk ukuran, ukuran file, dan MD5.

Filter yang dipakai:

- `MIN_WIDTH = 300`
- `MIN_HEIGHT = 300`
- ukuran file output minimal 2.000 bytes
- `BLUR_VARIANCE_MIN = 15.0`
- pHash threshold = `6`

Duplikat persis dicek dengan MD5. Gambar yang mirip dicek dengan perceptual hash/pHash, dalam grup produk dan label yang sama.

## OCR dan BPOM

Notebook memakai Tesseract OCR dan RapidFuzz untuk mengambil/menilai:

- teks OCR
- skor kecocokan brand
- skor kecocokan nama produk
- kecocokan ukuran
- BPOM ID dari OCR

`bpom_match_status` punya tiga nilai: `match`, `mismatch`, dan `not_visible`.

BPOM yang cocok dari OCR bukan bukti bahwa produk asli. OCR bisa salah baca; ini hanya pengecekan konsistensi.

## Output CSV

Semua output ada di `SafeCart_Dataset/metadata/`.

| File | Isi singkat |
| --- | --- |
| `products.csv` | Master produk yang sudah dinormalisasi, termasuk `product_id`. |
| `images.csv` | Gambar yang lolos, label, sumber, OCR, BPOM, hash, dan status download. |
| `rejected_images.csv` | Gambar gagal dan gambar duplikat. |
| `failed_downloads.csv` | Detail download/quality check yang gagal. |
| `failed_searches.csv` | Search atau pencarian sumber gambar yang gagal. |
| `products_without_enough_images.csv` | Produk dengan gambar referensi genuine kurang dari lima. |
| `manual_review.csv` | Gambar yang perlu dicek manual karena BPOM mismatch. |
| `review_evidence.csv` | Bukti publik yang diterima dan URL gambar terkait bila ada. |
| `counterfeit_evidence.csv` | Versi ringkas data bukti dugaan palsu. |
| `evidence_search_results.csv` | Semua hasil pencarian bukti, termasuk yang ditolak. |
| `reported_counterfeit_candidate_images.csv` | Record gambar dari tahap evidence collection. |
| `marketplace_listings.csv` | Listing Shopee/Tokopedia yang ditemukan; bukan otomatis counterfeit. |
| `sources.csv` | URL sumber gambar yang lolos. |
| `dataset_summary.csv` | Jumlah gambar per produk dan label. |

## Struktur folder

```text
SafeCart_Dataset/
├── images/
│   ├── genuine_reference/
│   ├── reported_counterfeit_candidate/
│   └── unknown/
├── metadata/
└── cache/
```

Folder `cache/` menyimpan response Serper agar request yang sama tidak dipanggil berulang-ulang.

## Konfigurasi API

Pipeline memakai **Serper API** untuk Google web search dan image search.

Isi key di notebook secara lokal:

```python
SERPER_API_KEY = "PASTE_YOUR_SERPER_API_KEY_HERE"
```

Jangan commit API key ke GitHub. Folder cache juga sebaiknya tidak di-commit jika ukurannya besar atau berisi response API.

Parameter utama:

- `RESULTS_PER_QUERY = 10`
- `MAX_RETRIES = 3`
- `RETRY_BACKOFF_SEC = 1.5`
- `REQUEST_TIMEOUT_SEC = 30`
- `MAX_WORKERS = 3`

## Cara menjalankan

Install dependency Python:

```bash
pip install -r requirements.txt
```

Tesseract adalah system dependency, bukan package pip. Di Google Colab/Linux bisa pakai:

```bash
apt-get install tesseract-ocr
```

Di Windows/local Jupyter, install Tesseract secara terpisah dan pastikan binary-nya bisa ditemukan oleh `pytesseract`.

Jalankan notebook secara berurutan:

```bash
jupyter notebook SafeCart_Dataset_Pipeline.ipynb
```

Masukkan Serper API key sebelum menjalankan preflight dan pipeline.

## Pilot mode

Untuk test kecil:

```python
PILOT_MODE = True
PILOT_PRODUCTS = 5
```

Untuk seluruh produk:

```python
PILOT_MODE = False
```

Notebook saat ini sudah memakai `PILOT_MODE = False`.

## Batasan dan penggunaan yang bertanggung jawab

- Halaman marketplace/review bisa memblokir request otomatis.
- Snippet hasil search bukan pengganti isi halaman/review lengkap.
- Hasil OCR dan pencocokan BPOM bisa salah.
- Sumber gambar tidak selalu menjamin barang asli.
- Search result bisa berubah dan Serper punya limit/quota request.
- Filter duplikat tidak sempurna.
- Jangan menuduh seller atau produk palsu hanya dari label candidate.
- Verifikasi manual tetap diperlukan sebelum data dipakai sebagai ground truth.
- Jangan bocorkan API key dan tetap hormati terms website, robots policy, rate limit, serta hukum yang berlaku.

## Status dataset

Dataset ini masih untuk research/prototype SafeCart. Label `reported_counterfeit_candidate` harus dianggap sebagai kandidat berbasis bukti publik dan masih butuh validasi manual.
