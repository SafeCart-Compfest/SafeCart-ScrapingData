import os
import json
import time
import requests
import urllib.parse
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# ==============================================================================
# KONFIGURASI BATCH SCRAPING
# ==============================================================================

# 1. UBAH NAMA PRODUK DI SINI:
# Tambahkan atau hapus nama produk yang ingin di-scrape
PRODUCTS = [
    "Blackmores Multivitamins Minerals",
    "Blackmores Bio C"
]

# 3. UBAH LIMIT PRODUK PER KEYWORD DI SINI:
# Berapa banyak product card yang di-scrape per keyword
LIMIT_PER_KEYWORD = 20

# 4. UBAH MODE BROWSER DI SINI:
# False = browser terlihat (untuk login manual pertama kali)
# True  = browser tersembunyi (untuk scraping otomatis)
HEADLESS = False

# ==============================================================================

def download_image_hd(url, save_path):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, stream=True, timeout=15)
        if response.status_code == 200:
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            return True
        else:
            print(f"      [Gagal Download] HTTP {response.status_code}")
    except Exception as e:
        print(f"      [Error Download] {e}")
    return False

def wait_for_element(page, selector, timeout=15):
    try:
        page.wait_for_selector(selector, timeout=timeout * 1000)
        return True
    except:
        return False

def append_to_metadata(base_dir, product_data):
    meta_path = os.path.join(base_dir, "metadata.json")
    data_list = []
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                data_list = json.load(f)
        except:
            pass
            
    data_list.append(product_data)
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(data_list, f, indent=4, ensure_ascii=False)

def load_progress(base_dir):
    progress_file = os.path.join(base_dir, "progress_tokopedia.json")
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return []

def save_progress(base_dir, keyword):
    completed = load_progress(base_dir)
    if keyword not in completed:
        completed.append(keyword)
        progress_file = os.path.join(base_dir, "progress_tokopedia.json")
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(completed, f, indent=4, ensure_ascii=False)

def scrape_tokopedia_product(page, url, target_dir, global_img_count, current_idx, total_idx):
    print(f"\n  [{current_idx}/{total_idx}] Membuka: {url[:80]}...")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(3) 
    
    found = wait_for_element(page, 'h1', timeout=10)
    if not found:
        print(f"   Gagal memuat halaman produk (mungkin Captcha/Timeout). Skip.")
        return global_img_count, 0
    
    title_el = page.query_selector('h1[data-testid="lblPDPDetailProductName"]') or page.query_selector('h1')
    title = title_el.inner_text().strip() if title_el else "Unknown Title"
    
    price_el = page.query_selector('div[data-testid="lblPDPDetailProductPrice"]')
    price = price_el.inner_text().strip() if price_el else "Unknown Price"
    
    desc_el = page.query_selector('div[data-testid="lblPDPDescriptionProduk"]')
    description = desc_el.inner_text().strip() if desc_el else ""
    
    # STRATEGI BARU BERSKALA PRODUKSI (HASIL INVESTIGASI)
    # 100% Kebal dari Gambar Review Pembeli & Avatar
    js_extractor = """
    async () => {
        const urls = new Set();
        
        const getLargestImg = () => {
            // Ambil dari kontainer spesifik gambar utama
            const mainImg = document.querySelector('[data-testid="PDPMainImage"] img, button.css-qjpdc6 img');
            if (mainImg && mainImg.src && mainImg.src.includes('tokopedia')) {
                return mainImg.src;
            }
            // Fallback cari gambar terbesar (tapi hanya di setengah layar atas)
            let maxArea = 0; let bestSrc = '';
            document.querySelectorAll('img').forEach(img => {
                const rect = img.getBoundingClientRect();
                const area = rect.width * rect.height;
                if(area > maxArea && img.src.includes('tokopedia') && rect.top < 1000) {
                    maxArea = area; bestSrc = img.src;
                }
            });
            return bestSrc;
        };
        
        // HANYA ambil thumbnail etalase resmi
        const thumbs = Array.from(document.querySelectorAll('[data-testid="PDPImageThumbnail"] img, button.css-w2e02c img'));
        
        if (thumbs.length === 0) { 
            urls.add(getLargestImg()); 
            return Array.from(urls); 
        }
        
        for (let thumb of thumbs) {
            thumb.scrollIntoView({block: 'center', inline: 'center'});
            thumb.click();
            await new Promise(r => setTimeout(r, 1200)); 
            const largest = getLargestImg();
            if (largest) urls.add(largest);
        }
        return Array.from(urls).filter(url => url !== '');
    }
    """
    
    images_hd = page.evaluate(js_extractor)
    images_real_dir = os.path.join(target_dir, "images", "real")
    os.makedirs(images_real_dir, exist_ok=True)
    
    saved_images_map = {}
    downloaded_this_product = 0
    
    for img_url in images_hd:
        img_name = f"{global_img_count}.jpg"
        save_path = os.path.join(images_real_dir, img_name)
        if download_image_hd(img_url, save_path):
            saved_images_map[img_name] = img_url
            global_img_count += 1
            downloaded_this_product += 1
            
    product_data = {
        "search_keyword": os.path.basename(target_dir),
        "url": url,
        "title": title,
        "price": price,
        "description": description,
        "images": saved_images_map,
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    append_to_metadata(target_dir, product_data)
    
    print(f"    -> Sukses! Tersimpan {downloaded_this_product} kandidat gambar.")
    return global_img_count, downloaded_this_product

def scrape_batch():
    print(f"{'='*60}")
    print(" TOKOPEDIA BATCH SCRAPER")
    print(f"Total keyword    : {len(PRODUCTS)}")
    print(f"Limit per keyword: {LIMIT_PER_KEYWORD} product cards")
    print(f"{'='*60}")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. UBAH FOLDER OUTPUT DI SINI:
    # "Data Obat Marketplace Tokopedia" adalah nama folder utamanya
    dataset_dir = os.path.join(current_dir, "Data Obat Marketplace Tokopedia")
    os.makedirs(dataset_dir, exist_ok=True)
    profile_dir = os.path.join(current_dir, "chrome_profile")
    
    total_products_scraped = 0
    total_images_downloaded = 0
    completed_keywords = load_progress(dataset_dir)
    
    with sync_playwright() as p:
        # Menggunakan Persistent Context agar user bisa login manual dan statenya tersimpan selamanya!
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=HEADLESS,
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            args=['--disable-blink-features=AutomationControlled']
        )
        page = context.pages[0] if context.pages else context.new_page()
        Stealth().apply_stealth_sync(page)
        
        for idx, keyword in enumerate(PRODUCTS):
            target_name = keyword.title()
            
            # --- CHECKPOINT AUTO-RESUME ---
            if target_name in completed_keywords:
                print(f"\n[{idx+1}/{len(PRODUCTS)}] SKIP: '{keyword}' sudah dikerjakan sebelumnya.")
                continue
            
            print(f"\n[{idx+1}/{len(PRODUCTS)}] Searching: {keyword}")
            
            target_dir = os.path.join(dataset_dir, target_name)
            os.makedirs(os.path.join(target_dir, "images", "real"), exist_ok=True)
            
            encoded_query = urllib.parse.quote(keyword)
            # URL Pencarian telah disuntikkan parameter &shop_tier=2 untuk memaksa hasil dari Toko Resmi (Mall)
            search_url = f"https://www.tokopedia.com/search?navsource=&shop_tier=2&srp_component_id=04.06.00.00&st=&q={encoded_query}"
            
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(5)
                
                target_links = []
                max_scrolls = 30
                
                # Algoritma dynamic scrolling untuk meraup produk organik dan iklan
                for scroll in range(max_scrolls):
                    all_links = page.query_selector_all('a[href*="tokopedia.com"]') or page.query_selector_all('a')
                    for el in all_links:
                        try:
                            href = el.get_attribute('href') or ''
                            
                            # Filter SUPER KETAT: Hanya ambil link produk organik atau link iklan
                            if href.startswith('https://www.tokopedia.com/'):
                                # Cek apakah struktur URL-nya adalah /nama-toko/nama-produk (tepat 2 bagian path)
                                path_only = href.split('?')[0].replace('https://www.tokopedia.com/', '').strip('/')
                                parts = path_only.split('/')
                                
                                if len(parts) == 2:
                                    clean_url = href.split('?')[0]
                                    if clean_url not in target_links:
                                        target_links.append(clean_url)
                                        
                            elif href.startswith('https://ta.tokopedia.com/'):
                                # Iklan (TopAds) tidak dipotong query-nya karena berisi token redirect
                                if href not in target_links:
                                    target_links.append(href)
                        except:
                            pass
                    
                    if len(target_links) >= LIMIT_PER_KEYWORD:
                        break
                        
                    page.evaluate("window.scrollBy(0, 800)")
                    time.sleep(1.5)
                
                final_links = target_links[:LIMIT_PER_KEYWORD]
                print(f"  Found: {len(final_links)} product cards")
                
                global_img_count = 1
                success_count = 0
                
                for i, url in enumerate(final_links):
                    try:
                        global_img_count, imgs = scrape_tokopedia_product(page, url, target_dir, global_img_count, i+1, len(final_links))
                        success_count += 1
                        total_images_downloaded += imgs
                    except Exception as e:
                        print(f"  [{i+1}/{len(final_links)}]  ERROR / TIMEOUT  SKIP. ({e})")
                
                total_products_scraped += success_count
                print(f"  Saved: {global_img_count - 1} candidate images for '{keyword}'.")
                
                # --- SIMPAN PROGRESS SETELAH 1 KEYWORD SELESAI ---
                save_progress(dataset_dir, target_name)
                completed_keywords.append(target_name)
                
            except Exception as e:
                print(f"  ERROR on Search Page  SKIP. ({e})")
                
        # Tutup browser
        context.close()
        
    print(f"\n{'='*60}")
    print("BATCH FINISHED")
    print(f"Total product cards : {total_products_scraped}")
    print(f"Total images        : {total_images_downloaded}")
    print(f"{'='*60}")

if __name__ == "__main__":
    scrape_batch()
