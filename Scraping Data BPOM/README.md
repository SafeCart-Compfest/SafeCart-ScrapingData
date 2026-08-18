# Dokumentasi Scraping Data BPOM

Folder ini berisi script untuk mengambil data produk resmi dari API Satu Data BPOM. Data ditarik secara bertahap (per halaman) dan disimpan ke dalam beberapa file CSV.

## Persiapan (Setup)

Script ini membutuhkan token akses (Access Token) resmi dari BPOM untuk bisa berfungsi.

1. Duplikat file `.env.example` dan ubah namanya menjadi `.env`
2. Buka file `.env` dan masukkan token milikmu:
   ```env
   BPOM_ACCESS_TOKEN=masukkan_token_kamu_di_sini
   ```
*(Catatan: File `.env` sudah masuk ke dalam `.gitignore` sehingga aman dan tidak akan ter-push ke GitHub).*

## Konfigurasi Script

Buka file `main_bpom.py` dan perhatikan bagian atas (baris ~20):

```python
# Run modes
RUN_FULL_DOWNLOAD = True  # Set False jika hanya ingin mencoba (maksimal 3 halaman)
FORCE_RESTART = False     # Set True jika ingin mengulang scraping dari awal
```

- **Fitur Resume (Checkpoint):** Script secara otomatis menyimpan kemajuan di file `.checkpoint.json`. Jika sewaktu-waktu terputus (internet mati atau menekan Ctrl+C), jalankan ulang script dan ia akan otomatis **melanjutkan** dari halaman terakhir.

## Cara Menjalankan

Buka terminal, pastikan kamu berada di dalam folder ini, lalu jalankan:

```bash
python main_bpom.py
```

## Hasil (Output)

- File CSV (`bpom_products_001.csv`, `002`, dst.) berisi maksimal 150.000 baris per file.
- `ingestion.log`: Catatan riwayat scraping.
- `ingestion_report.json`: Laporan validasi akhir yang mengecek apakah ada duplikat atau data kosong (NIE/Kode QR/Nama Produk).

## Validasi Lanjutan

Terdapat file `validate_bpom.ipynb` (Jupyter Notebook) yang dapat digunakan oleh *Data Scientist* atau analis untuk mengeksplorasi data hasil scraping lebih dalam (melihat distribusi data, memplot grafik, dll).
