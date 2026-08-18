# SafeCart — Product Reference Image Dataset

## 1. Tentang Dataset

Dataset ini dibuat untuk project SafeCart sebagai kumpulan gambar referensi produk skincare dan kosmetik. Gambar yang dikumpulkan berfokus pada packaging atau tampilan produk, sehingga bisa dipakai sebagai visual reference untuk product identification, visual matching, dan proses pendukung verifikasi produk.

Dataset ini berbeda dari dataset real-vs-fake. Gambar di sini tidak otomatis dianggap sebagai bukti bahwa sebuah produk asli, dan tidak boleh dipakai sendirian untuk menentukan produk fake atau real.

## 2. Sumber Data

Notebook menggunakan daftar produk dari CSV subset yang disiapkan dari `products_all_brands.csv`. Pada notebook, file input yang dibaca adalah:

```python
PRODUCTS_CSV = "products_sampe.csv"
```

Setiap baris produk minimal memakai informasi `brand_name`, `product_name`, `product_id`, dan `url`.

Sumber gambar yang digunakan:

- Sociolla direct extraction: pipeline membuka URL produk Sociolla dan mengambil kandidat gambar dari `og:image` serta tag `<img>` yang mengarah ke media produk.
- Serper Image Search: digunakan sebagai fallback jika gambar dari Sociolla belum mencapai jumlah minimum.

Alurnya adalah Sociolla dicoba terlebih dahulu untuk setiap produk. Jika jumlah gambar yang berhasil disimpan masih kurang dari `MIN_IMAGES_PER_PRODUCT`, pipeline membuat satu request Serper Image Search untuk produk tersebut.

## 3. Cara Kerja Pipeline

```text
products_sampe.csv
        |
        v
pilih produk yang akan diproses
        |
        v
ambil gambar langsung dari halaman Sociolla
        |
        v
validasi + dedup gambar
        |
        v
apakah gambar sudah mencapai MIN_IMAGES_PER_PRODUCT?
        |                         |
       ya                       tidak
        |                         |
        v                         v
   simpan hasil          cek quota Serper
                                  |
                                  v
                         Serper Image Search
                                  |
                                  v
                         validasi + dedup gambar
                                  |
                                  v
                             simpan hasil
        |
        v
tulis metadata ke SafeCart_Dataset/metadata
```

Gambar disimpan per produk ke folder:

```text
SafeCart_Dataset/images/{brand_name}_{product_id}/
```

Contoh nama file yang dibuat notebook:

- `sociolla_0.jpg`
- `serper_0.jpg`

## 4. Batasan Serper

Serper dibatasi maksimal `2_500` request melalui parameter:

```python
SERPER_MAX_REQUESTS = 2500
```

Counter request dibuat thread-safe dengan `Lock`, lalu disimpan ke:

```text
SafeCart_Dataset/metadata/serper_usage.json
```

File ini menyimpan `limit`, `used`, `remaining`, `enabled`, dan `last_updated`, sehingga pipeline bisa dilanjutkan/resume tanpa melewati batas request. Counter disimpan saat notebook dimulai, setelah request Serper, secara berkala setiap `SERPER_SAVE_EVERY_N_PRODUCTS`, dan di akhir proses.

Ketika quota habis, fallback Serper otomatis dinonaktifkan. Proses lain yang tidak membutuhkan Serper tetap berjalan, termasuk Sociolla direct extraction, download gambar, validasi, dedup, dan penulisan metadata.

## 5. Struktur Folder

Struktur folder yang dibuat atau digunakan notebook:

```text
SafeCart_Dataset/
├── images/
│   └── {brand_name}_{product_id}/
│       ├── sociolla_0.jpg
│       └── serper_0.jpg
├── metadata/
│   ├── collection_results.csv
│   ├── test_results.csv
│   ├── missing_images.csv
│   └── serper_usage.json
└── logs/
```

Catatan: `logs/` dibuat pada setup notebook, tetapi notebook yang dianalisis tidak menulis file log khusus ke folder tersebut.

## 6. Metadata

File metadata yang dihasilkan atau digunakan notebook:

- `collection_results.csv`: hasil utama saat `TEST_MODE = False`.
- `test_results.csv`: hasil saat `TEST_MODE = True`.
- `missing_images.csv`: daftar produk yang tidak menghasilkan gambar usable, hanya ditulis jika ada produk dengan `total_images == 0`.
- `serper_usage.json`: checkpoint penggunaan request Serper untuk mendukung resume dan pembatasan quota.

## 7. Format Data

Metadata hasil scraping memiliki kolom berikut:

- `brand_name`: nama brand dari input CSV.
- `product_name`: nama produk.
- `product_id`: ID produk.
- `url`: URL halaman produk.
- `images_from_sociolla`: jumlah gambar yang berhasil disimpan dari Sociolla direct extraction.
- `images_from_serper`: jumlah gambar yang berhasil disimpan dari Serper fallback.
- `total_images`: total gambar usable yang berhasil disimpan.
- `serper_status`: status Serper untuk produk tersebut, misalnya `not_needed`, `ok`, `quota_limit_reached`, `rate_limited`, `authentication_error`, `timeout`, `error`, atau `processing_error: ...`.

## 8. Cara Menjalankan

1. Clone repository.
2. Install dependency Python:

```bash
pip install -r requirements.txt
```

3. Siapkan `products_all_brands.csv`.
4. Buat atau siapkan CSV subset sesuai file yang dibaca notebook, yaitu `products_sampe.csv`.
5. Masukkan Serper API key secara lokal di notebook:

```python
SERPER_API_KEY = "YOUR_SERPER_API_KEY"
```

6. Pastikan API key tidak di-commit ke repository.
7. Jalankan notebook `SafeCart_Image_Collection.ipynb`.
8. Cek hasil gambar di `SafeCart_Dataset/images/`.
9. Cek metadata di `SafeCart_Dataset/metadata/`.

## 9. Konfigurasi Penting

Parameter penting yang ada di notebook:

- `SERPER_MAX_REQUESTS`: batas maksimal request Serper, default `2500`.
- `SERPER_ENABLED`: status apakah fallback Serper masih aktif.
- `MIN_IMAGES_PER_PRODUCT`: jumlah minimum gambar per produk sebelum fallback Serper dipakai, default `3`.
- `SERPER_RETRY_LIMIT`: jumlah retry untuk error jaringan sementara, default `2`.
- `SERPER_REQUEST_TIMEOUT`: timeout request Serper dalam detik, default `15`.
- `SERPER_SAVE_EVERY_N_PRODUCTS`: interval penyimpanan checkpoint usage, default `25`.
- `TEST_SERPER_API`: test opsional API Serper, default `False`, dan jika diaktifkan akan memakai 1 request.
- `TEST_MODE`: mode uji coba menggunakan sebagian kecil produk, default `False`.
- `TEST_PRODUCTS`: jumlah produk saat `TEST_MODE = True`, default `20`.
- `MAX_WORKERS`: jumlah worker paralel untuk `ThreadPoolExecutor`, default `8`.

## 10. Catatan Dataset

Dataset ini merupakan subset dari `products_all_brands.csv`, bukan seluruh daftar produk. Jumlah produk yang diproses bergantung pada CSV subset yang digunakan.

Jumlah gambar per produk tidak harus sama. Tidak semua gambar berasal dari sumber yang sama, karena sebagian bisa berasal dari Sociolla direct extraction dan sebagian dari Serper Image Search.

Gambar dalam dataset ini digunakan sebagai reference images. Dataset ini bukan ground truth authenticity dataset, dan dataset real-vs-fake adalah dataset terpisah.

## 11. Limitasi

Beberapa limitasi yang perlu diperhatikan:

- Beberapa produk mungkin tidak memiliki gambar yang cukup.
- Beberapa URL produk dapat gagal diakses.
- Serper memiliki quota maksimal 2.500 request.
- Kualitas dan jumlah gambar bergantung pada sumber yang tersedia.
- Dedup dilakukan berdasarkan hash konten gambar.
- Gambar reference tidak otomatis menjamin keaslian produk.

## 12. Hubungan dengan SafeCart

Dataset ini dapat digunakan sebagai data pendukung untuk SafeCart, terutama untuk:

- product recognition;
- visual matching;
- membandingkan packaging produk yang di-scan dengan reference image;
- membantu proses authenticity verification.

Namun, dataset ini tidak menentukan keaslian produk secara mandiri. Hasil dari dataset ini sebaiknya dipakai sebagai salah satu referensi dalam pipeline SafeCart, bukan sebagai keputusan final fake atau real.

## 13. Disclaimer

Gambar dikumpulkan dari sumber publik atau retail yang diakses melalui URL produk dan pencarian gambar. Dataset ini digunakan untuk kebutuhan penelitian dan pengembangan SafeCart.

Informasi produk dan sumber tetap dicatat pada metadata jika tersedia. Dataset reference ini tidak boleh dianggap sebagai bukti final keaslian produk.
