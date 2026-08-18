"""
=============================================================================
DATASET MERGE UTILITY
=============================================================================
Script ini digunakan untuk menggabungkan hasil web scraping (Tokopedia) 
yang terpotong menjadi beberapa part/folder (misal karena scraping terhenti).

Cara Penggunaan:
1. Pastikan Anda memiliki Python terinstal.
2. Atur konfigurasi di bawah (KATEGORI dan FOLDERS_RANGE).
3. Jalankan script ini via terminal:
   python merge_dataset.py

Proses:
- Script akan memindahkan (move) folder produk dari sumber ke folder target.
- Script juga akan menggabungkan list master di `progress_tokopedia.json`
  sehingga tidak ada progress yang hilang atau tumpang tindih (duplicate).
=============================================================================
"""

import os
import shutil
import json

# ==============================================================================
# KONFIGURASI PENGGUNA
# ==============================================================================

# 1. PILIH KATEGORI DATASET:
# Opsi: "Obat Marketplace", "Makanan Marketplace", atau "Skincare Marketplace"
KATEGORI = "Obat Marketplace"

# 2. NAMA FOLDER TARGET AKHIR:
# Semua data dari folder part akan digabungkan ke folder ini
TARGET_DIR_NAME = "Gambar Obat Marketplace"

# 3. RANGE FOLDER PART YANG DIGABUNGKAN:
# Jika Anda menjalankan scraping paralel di folder 1, 2, 3, 4, 5, 6 → range(1, 7)
FOLDERS_RANGE = range(1, 7)

# ==============================================================================

def merge_datasets():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(base_dir, TARGET_DIR_NAME)
    os.makedirs(target_dir, exist_ok=True)
    
    # Kumpulkan seluruh path sumber berdasarkan kategori dan range folder
    sources = [os.path.join(base_dir, KATEGORI, f"Data {KATEGORI} Tokopedia")]
    
    for i in FOLDERS_RANGE:
        # Menambahkan support untuk penamaan folder "Obat Marketplace Rame", dll
        # Jika Anda menggunakan nama folder part yang berbeda, sesuaikan polanya di sini.
        source_path = os.path.join(base_dir, f"{KATEGORI} Rame", str(i), f"Data {KATEGORI} Tokopedia")
        sources.append(source_path)
        
    global_progress = set()
    total_folders_moved = 0
    
    for source in sources:
        if not os.path.exists(source):
            print(f"Melewati (Tidak ditemukan): {source}")
            continue
            
        print(f"\nMenganalisis: {source}")
        
        # 1. Gabungkan progress_tokopedia.json
        progress_file = os.path.join(source, "progress_tokopedia.json")
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_list = json.load(f)
                    for item in progress_list:
                        global_progress.add(item)
            except Exception as e:
                print(f"  -> Gagal membaca progress json: {e}")
                
        # 2. Pindahkan folder produk
        for item_name in os.listdir(source):
            item_path = os.path.join(source, item_name)
            
            if not os.path.isdir(item_path):
                continue
                
            target_item_path = os.path.join(target_dir, item_name)
            
            if os.path.exists(target_item_path):
                print(f"  -> Melewati folder '{item_name}' (Sudah ada di target)")
                continue
                
            try:
                shutil.move(item_path, target_item_path)
                total_folders_moved += 1
            except Exception as e:
                print(f"  -> Gagal memindahkan '{item_name}': {e}")
                
    # 3. Simpan global progress ke folder tujuan
    target_progress_file = os.path.join(target_dir, "progress_tokopedia.json")
    with open(target_progress_file, 'w', encoding='utf-8') as f:
        json.dump(list(global_progress), f, indent=4)
        
    print("\n" + "="*50)
    print("PENGGABUNGAN SELESAI!")
    print(f"Total Folder Produk Dipindahkan: {total_folders_moved}")
    print(f"Total Kata Kunci di Progress Gabungan: {len(global_progress)}")
    print(f"Lokasi Target Akhir: {target_dir}")
    print("="*50)

if __name__ == "__main__":
    print(f"Memulai penggabungan dataset untuk kategori: {KATEGORI}...")
    merge_datasets()
