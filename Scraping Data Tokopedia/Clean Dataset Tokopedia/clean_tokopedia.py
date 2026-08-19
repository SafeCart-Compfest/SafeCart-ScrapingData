import os
import shutil
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
from tqdm import tqdm

# ==============================================================================
# KONFIGURASI
# Ubah TARGET_CATEGORY untuk memproses kategori lain, atau set ke None untuk semua
# ==============================================================================
TARGET_CATEGORY = "Gambar Makanan Tokopedia"  # None = proses semua kategori sekaligus
CONFIDENCE_THRESHOLD = 0.6  # Minimum probability untuk "keep". Naikkan kalau terlalu longgar.
MIN_FILE_SIZE_BYTES = 5120  # 5 KB
IMAGE_SIZE = 224

# ==============================================================================

def is_valid_image(filepath):
    """Cek apakah file gambar bisa dibuka dan tidak korup."""
    if os.path.getsize(filepath) < MIN_FILE_SIZE_BYTES:
        return False
    try:
        img = Image.open(filepath)
        img.verify()
        return True
    except Exception:
        return False

def load_model(model_path, device):
    """Load model MobileNetV2 yang sudah di-train."""
    model = models.mobilenet_v2(weights=None)
    model.classifier = nn.Sequential(
        nn.Dropout(0.2),
        nn.Linear(1280, 2),
    )
    
    checkpoint = torch.load(model_path, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint['model_state_dict'])
    model = model.to(device)
    model.eval()
    
    print(f"  Model loaded (Val Accuracy saat training: {checkpoint['val_accuracy']:.1f}%)")
    return model

def predict_image(model, image_path, transform, device):
    """Prediksi apakah gambar ada kemasan (1) atau tidak (0)."""
    try:
        image = Image.open(image_path).convert("RGB")
        tensor = transform(image).unsqueeze(0).to(device)
        
        with torch.no_grad():
            outputs = model(tensor)
            probabilities = torch.softmax(outputs, dim=1)
            confidence, predicted = torch.max(probabilities, 1)
            
        return predicted.item(), confidence.item()
    except Exception:
        return -1, 0.0  # Error

def clean_dataset():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, "model", "packaging_classifier.pth")
    
    marketplace_dir = os.path.join(os.path.dirname(base_dir), "Marketplace")
    raw_base = os.path.join(marketplace_dir, "raw")
    clean_base = os.path.join(marketplace_dir, "clean")
    
    if not os.path.exists(model_path):
        print("[ERROR] Model belum ada! Jalankan 'train_tokopedia.py' dulu.")
        return
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print("=" * 60)
    print("[START] CLEANING DATASET DENGAN TRAINED MODEL")
    print(f"  Device: {device}")
    print(f"  Confidence threshold: {CONFIDENCE_THRESHOLD}")
    print("=" * 60)
    
    model = load_model(model_path, device)
    
    transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    
    # Tentukan kategori yang akan diproses
    if TARGET_CATEGORY:
        categories = [TARGET_CATEGORY]
    else:
        categories = [d for d in os.listdir(raw_base) if os.path.isdir(os.path.join(raw_base, d))]
    
    grand_total = 0
    grand_kept = 0
    grand_marketing = 0
    grand_corrupted = 0
    
    for category in categories:
        raw_category_dir = os.path.join(raw_base, category)
        clean_category_dir = os.path.join(clean_base, category)
        
        if not os.path.exists(raw_category_dir):
            print(f"\n[SKIP] {category} — folder tidak ditemukan")
            continue
        
        os.makedirs(clean_category_dir, exist_ok=True)
        
        product_folders = [f for f in os.listdir(raw_category_dir) if os.path.isdir(os.path.join(raw_category_dir, f))]
        
        print(f"\n[KATEGORI] {category} — {len(product_folders)} folder produk")
        
        cat_total = 0
        cat_kept = 0
        cat_marketing = 0
        cat_corrupted = 0
        
        for product_name in tqdm(product_folders, desc=f"  {category}", unit="produk"):
            raw_product_dir = os.path.join(raw_category_dir, product_name)
            clean_product_dir = os.path.join(clean_category_dir, product_name)
            
            raw_images_dir = os.path.join(raw_product_dir, "images", "real")
            clean_images_dir = os.path.join(clean_product_dir, "images", "real")
            
            os.makedirs(clean_images_dir, exist_ok=True)
            
            # Copy metadata.json
            raw_metadata = os.path.join(raw_product_dir, "metadata.json")
            clean_metadata = os.path.join(clean_product_dir, "metadata.json")
            if os.path.exists(raw_metadata):
                shutil.copy2(raw_metadata, clean_metadata)
            
            if not os.path.exists(raw_images_dir):
                continue
            
            for filename in os.listdir(raw_images_dir):
                if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    continue
                
                cat_total += 1
                source_path = os.path.join(raw_images_dir, filename)
                target_path = os.path.join(clean_images_dir, filename)
                
                # Resume: skip jika sudah ada di clean
                if os.path.exists(target_path):
                    cat_kept += 1
                    continue
                
                # PASS 1: discard gambar korup / gagal download
                if not is_valid_image(source_path):
                    cat_corrupted += 1
                    continue
                
                # PASS 2: Model prediction
                prediction, confidence = predict_image(model, source_path, transform, device)
                
                if prediction == -1:
                    cat_corrupted += 1
                    continue
                
                # prediction=1 = keep, prediction=0 = discard
                if prediction == 1 and confidence > CONFIDENCE_THRESHOLD:
                    shutil.copy2(source_path, target_path)
                    cat_kept += 1
                else:
                    cat_marketing += 1
        
        # Copy progress file
        raw_progress = os.path.join(raw_category_dir, "progress_tokopedia.json")
        clean_progress = os.path.join(clean_category_dir, "progress_tokopedia.json")
        if os.path.exists(raw_progress):
            shutil.copy2(raw_progress, clean_progress)
        
        print(f"  Hasil {category}: [KEEP] {cat_kept} | [discard] {cat_marketing} | [KORUP] {cat_corrupted} | Total: {cat_total}")
        
        grand_total += cat_total
        grand_kept += cat_kept
        grand_marketing += cat_marketing
        grand_corrupted += cat_corrupted
    
    print("\n" + "=" * 60)
    print("[SELESAI] SELURUH DATASET BERSIH!")
    print(f"  Total Gambar Scan  : {grand_total}")
    print(f"  [KEEP] Bersih (Copy) : {grand_kept}")
    print(f"  [discard] Marketing    : {grand_marketing}")
    print(f"  [KORUP] Gagal        : {grand_corrupted}")
    print(f"  Lokasi Clean       : {clean_base}")
    print("=" * 60)

if __name__ == "__main__":
    clean_dataset()
