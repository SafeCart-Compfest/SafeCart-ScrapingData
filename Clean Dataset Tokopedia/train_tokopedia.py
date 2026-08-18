import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import transforms, models
from PIL import Image
from tqdm import tqdm

# ==============================================================================
# KONFIGURASI
# ==============================================================================
EPOCHS = 10
BATCH_SIZE = 16
LEARNING_RATE = 0.001
IMAGE_SIZE = 224
VALIDATION_SPLIT = 0.2

# ==============================================================================

class PackagingDataset(Dataset):
    def __init__(self, keep_dir, discard_dir, transform=None):
        self.samples = []
        self.transform = transform
        
        # Label 1 = keep (ada kemasan), Label 0 = discard (tidak ada kemasan)
        for fname in os.listdir(keep_dir):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                self.samples.append((os.path.join(keep_dir, fname), 1))
        
        for fname in os.listdir(discard_dir):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                self.samples.append((os.path.join(discard_dir, fname), 0))
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, label

def train_model():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    keep_dir = os.path.join(base_dir, "samples", "keep")
    discard_dir = os.path.join(base_dir, "samples", "discard")
    model_dir = os.path.join(base_dir, "model")
    os.makedirs(model_dir, exist_ok=True)
    
    # Cek labeling sudah dilakukan
    keep_count = len([f for f in os.listdir(keep_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]) if os.path.exists(keep_dir) else 0
    discard_count = len([f for f in os.listdir(discard_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]) if os.path.exists(discard_dir) else 0
    
    if keep_count == 0 or discard_count == 0:
        print("[ERROR] Folder 'keep/' atau 'discard/' masih kosong!")
        print(f"  keep/: {keep_count} gambar")
        print(f"  discard/: {discard_count} gambar")
        print("Labeling dulu gambar dari 'unlabeled/' ke 'keep/' dan 'discard/'.")
        return
    
    print("=" * 60)
    print("[START] TRAINING MobileNetV2 Binary Classifier")
    print(f"  Gambar 'keep' (ada kemasan): {keep_count}")
    print(f"  Gambar 'discard' (tanpa kemasan): {discard_count}")
    print("=" * 60)
    
    # Data augmentation untuk training, normalize untuk MobileNet
    train_transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    
    val_transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    
    # Dataset
    full_dataset = PackagingDataset(keep_dir, discard_dir, transform=train_transform)
    
    # Split train/val
    val_size = int(len(full_dataset) * VALIDATION_SPLIT)
    train_size = len(full_dataset) - val_size
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])
    
    # Override transform untuk validation set
    val_dataset.dataset = PackagingDataset(keep_dir, discard_dir, transform=val_transform)
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    
    # Model: MobileNetV2 pretrained, ganti classifier terakhir
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")
    
    model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
    
    # Freeze semua layer kecuali classifier
    for param in model.features.parameters():
        param.requires_grad = False
    
    # Ganti classifier head: 1280 -> 2 (binary)
    model.classifier = nn.Sequential(
        nn.Dropout(0.2),
        nn.Linear(1280, 2),
    )
    model = model.to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.classifier.parameters(), lr=LEARNING_RATE)
    
    best_val_acc = 0.0
    model_path = os.path.join(model_dir, "packaging_classifier.pth")
    
    for epoch in range(EPOCHS):
        # Training
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        for images, labels in tqdm(train_loader, desc=f"Epoch {epoch+1}/{EPOCHS} [Train]", leave=False):
            images, labels = images.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            train_total += labels.size(0)
            train_correct += (predicted == labels).sum().item()
        
        train_acc = train_correct / train_total * 100
        
        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                _, predicted = torch.max(outputs, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
        
        val_acc = val_correct / val_total * 100 if val_total > 0 else 0
        
        print(f"  Epoch {epoch+1}/{EPOCHS} — Train Acc: {train_acc:.1f}% | Val Acc: {val_acc:.1f}%")
        
        # Simpan model terbaik
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                'model_state_dict': model.state_dict(),
                'val_accuracy': val_acc,
                'epoch': epoch + 1,
            }, model_path)
    
    print("\n" + "=" * 60)
    print("TRAINING SELESAI!")
    print(f"  Best Validation Accuracy: {best_val_acc:.1f}%")
    print(f"  Model tersimpan di: {model_path}")
    print("=" * 60)
    print("\nLANGKAH SELANJUTNYA:")
    print("Jalankan 'clean_tokopedia.py' untuk membersihkan seluruh dataset.")

if __name__ == "__main__":
    train_model()
