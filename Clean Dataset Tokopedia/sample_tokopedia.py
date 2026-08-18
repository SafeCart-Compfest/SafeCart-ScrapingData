import os
import random
import shutil
from glob import glob

# ==============================================================================
# KONFIGURASI
# ==============================================================================
SAMPLES_PER_CATEGORY = 100
SEED = 42

def sample_images():
    random.seed(SEED)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.join(os.path.dirname(base_dir), "Marketplace", "raw")
    
    # Folder output
    unlabeled_dir = os.path.join(base_dir, "samples", "unlabeled")
    keep_dir = os.path.join(base_dir, "samples", "keep")
    discard_dir = os.path.join(base_dir, "samples", "discard")
    
    for d in [unlabeled_dir, keep_dir, discard_dir]:
        os.makedirs(d, exist_ok=True)
    
    categories = {
        "skincare": os.path.join(raw_dir, "Gambar Skincare Tokopedia"),
        "makanan": os.path.join(raw_dir, "Gambar Makanan Tokopedia"),
        "obat": os.path.join(raw_dir, "Gambar Obat Tokopedia"),
    }
    
    total_sampled = 0
    
    for cat_name, cat_dir in categories.items():
        if not os.path.exists(cat_dir):
            print(f"[SKIP] Folder tidak ditemukan: {cat_dir}")
            continue
        
        # Kumpulkan semua gambar dari semua subfolder produk
        all_images = []
        for product_name in os.listdir(cat_dir):
            product_path = os.path.join(cat_dir, product_name)
            if not os.path.isdir(product_path):
                continue
            
            images_dir = os.path.join(product_path, "images", "real")
            if not os.path.exists(images_dir):
                continue
            
            for fname in os.listdir(images_dir):
                if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    all_images.append((product_name, os.path.join(images_dir, fname)))
        
        print(f"[{cat_name.upper()}] Total gambar ditemukan: {len(all_images)}")
        
        # Ambil sampel acak
        sample_count = min(SAMPLES_PER_CATEGORY, len(all_images))
        sampled = random.sample(all_images, sample_count)
        
        for product_name, img_path in sampled:
            # Buat nama unik: kategori_produk_namafile.jpg
            safe_product = product_name.replace(" ", "_")[:30]
            original_name = os.path.basename(img_path)
            new_name = f"{cat_name}_{safe_product}_{original_name}"
            
            target_path = os.path.join(unlabeled_dir, new_name)
            
            # Hindari nama duplikat
            counter = 1
            while os.path.exists(target_path):
                name, ext = os.path.splitext(new_name)
                target_path = os.path.join(unlabeled_dir, f"{name}_{counter}{ext}")
                counter += 1
            
            shutil.copy2(img_path, target_path)
            total_sampled += 1
        
        print(f"  -> Diambil {sample_count} sampel")
    
    print("\n" + "=" * 60)
    print("SAMPLING SELESAI!")
    print(f"Total gambar di 'unlabeled/': {total_sampled}")
    print(f"Lokasi: {unlabeled_dir}")
    print("=" * 60)
    print("\nLANGKAH SELANJUTNYA:")
    print("1. Buka folder 'samples/unlabeled/' di File Explorer")
    print("2. Pindahkan gambar yang ADA KEMASAN PRODUK ke 'samples/keep/'")
    print("3. Pindahkan gambar TANPA KEMASAN ke 'samples/discard/'")
    print("4. Setelah selesai, jalankan 'train_tokopedia.py'")

if __name__ == "__main__":
    sample_images()
