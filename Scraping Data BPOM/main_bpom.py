import os
from dotenv import load_dotenv
import requests
import time
import random
import json
import csv
import logging
import signal
import sys
from datetime import datetime

load_dotenv()

# Constants
API_BASE_URL = "https://satudata.pom.go.id/api/items/app_webreg_masterproduk"
API_PAGE_SIZE = 500
MAX_CSV_ROWS = 150000

# Run modes
RUN_FULL_DOWNLOAD = True  
FORCE_RESTART = False      

# Auth
BPOM_ACCESS_TOKEN = os.getenv("BPOM_ACCESS_TOKEN")

if not BPOM_ACCESS_TOKEN:
    raise ValueError("ERROR: BPOM_ACCESS_TOKEN not found in environment variables. Please check your .env file.")

# Target Directory
DATA_DIR = "Data BPOM"
os.makedirs(DATA_DIR, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(DATA_DIR, "ingestion.log"), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

CHECKPOINT_FILE = os.path.join(DATA_DIR, ".checkpoint.json")

def load_checkpoint():
    if not FORCE_RESTART and os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load checkpoint: {e}")
    
    return {
        "last_successful_offset": 0,
        "records_downloaded": 0,
        "current_csv_file": "bpom_products_001.csv",
        "records_in_current_csv": 0,
        "total_records": 0,
        "updated_at": ""
    }

def save_checkpoint(checkpoint_data):
    checkpoint_data["updated_at"] = datetime.now().isoformat()
    temp_file = CHECKPOINT_FILE + ".tmp"
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(checkpoint_data, f, indent=4)
    os.replace(temp_file, CHECKPOINT_FILE)

def get_bpom_data(offset, max_retries=5):
    params = {
        "fields": "*",
        "limit": API_PAGE_SIZE,
        "offset": offset,
        "meta": "filter_count",
        "access_token": BPOM_ACCESS_TOKEN
    }
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(API_BASE_URL, params=params, timeout=30)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    return data
                except ValueError:
                    logging.warning(f"Attempt {attempt}: Invalid JSON response")
            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 0))
                delay = retry_after if retry_after > 0 else (2 ** attempt) + random.uniform(0, 1)
                logging.warning(f"Attempt {attempt}: Rate limited (429). Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
                continue
            elif response.status_code in [500, 502, 503, 504]:
                logging.warning(f"Attempt {attempt}: Server error ({response.status_code}).")
            else:
                logging.warning(f"Attempt {attempt}: HTTP {response.status_code}")
                
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            logging.warning(f"Attempt {attempt}: Connection error/timeout: {e}")
            
        delay = (10 * (2 ** (attempt - 1))) + random.uniform(0, 2)
        logging.info(f"Retrying in {delay:.2f} seconds...")
        time.sleep(delay)
        
    logging.error(f"Failed to fetch data for offset {offset} after {max_retries} attempts.")
    return None

def validate_response(response_json):
    if not isinstance(response_json, dict):
        return False, "Response is not a JSON object"
    if "data" not in response_json:
        return False, "Missing 'data' field in response"
    
    records = response_json["data"]
    if not isinstance(records, list):
        return False, "'data' is not a list"
        
    if len(records) > API_PAGE_SIZE:
        logging.warning(f"Warning: Received {len(records)} records, which is more than the requested limit {API_PAGE_SIZE}")
        
    return True, records

def write_to_csv(filename, records, mode='a'):
    if not records:
        return
        
    filepath = os.path.join(DATA_DIR, filename)
    file_exists = os.path.exists(filepath) and mode == 'a'
    
    headers = []
    for r in records:
        for k in r.keys():
            if k not in headers:
                headers.append(k)
                
    write_header = not file_exists
    
    with open(filepath, mode, newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore')
        
        if write_header:
            writer.writeheader()
            
        for record in records:
            writer.writerow(record)
            
        csvfile.flush()
        os.fsync(csvfile.fileno())

stop_execution = False

def signal_handler(sig, frame):
    global stop_execution
    print("\nInterrupt received! Stopping gracefully after current batch...")
    stop_execution = True

signal.signal(signal.SIGINT, signal_handler)

def print_progress(checkpoint, api_requests, retries):
    pct = (checkpoint['records_downloaded'] / checkpoint['total_records'] * 100) if checkpoint['total_records'] > 0 else 0
    print("=" * 40)
    print("BPOM MASTER PRODUCT INGESTION")
    print("=" * 40)
    print(f"Total records : {checkpoint['total_records']:,}")
    print(f"Downloaded    : {checkpoint['records_downloaded']:,}")
    print(f"Progress      : {pct:.2f}%")
    print(f"Current offset: {checkpoint['last_successful_offset']:,}")
    print(f"API page size : {API_PAGE_SIZE}")
    print(f"Current file  : {checkpoint['current_csv_file']}")
    print(f"File progress : {checkpoint['records_in_current_csv']:,} / {MAX_CSV_ROWS:,}")
    print(f"API requests  : {api_requests}")
    print(f"Retries       : {retries}")
    print("=" * 40 + "\n")

def run_ingestion(test_mode=True):
    global stop_execution
    stop_execution = False
    
    checkpoint = load_checkpoint()
    
    offset = checkpoint["last_successful_offset"]
    
    if FORCE_RESTART:
        offset = 0
        checkpoint["last_successful_offset"] = 0
        checkpoint["records_downloaded"] = 0
        checkpoint["current_csv_file"] = "bpom_products_001.csv"
        checkpoint["records_in_current_csv"] = 0
        checkpoint["total_records"] = 0
    
    api_requests = 0
    total_retries = 0
    pages_fetched = 0
    max_pages = 3 if test_mode else float('inf')
    
    logging.info(f"Starting ingestion from offset {offset}. Test mode: {test_mode}")
    
    while not stop_execution and pages_fetched < max_pages:
        logging.info(f"Fetching offset {offset}...")
        api_requests += 1
        
        response = get_bpom_data(offset)
        
        if not response:
            logging.error("Failed to fetch data. Saving checkpoint and exiting.")
            break
            
        is_valid, records = validate_response(response)
        
        if not is_valid:
            logging.error(f"Invalid response: {records}. Saving checkpoint and exiting.")
            break
            
        if "meta" in response and "filter_count" in response["meta"]:
            checkpoint["total_records"] = response["meta"]["filter_count"]
            
        if len(records) == 0:
            if offset >= checkpoint["total_records"]:
                logging.info("Reached end of dataset.")
            else:
                logging.warning(f"Received empty data before reaching total records (offset={offset}, total={checkpoint['total_records']}). Stopping.")
            break
            
        if checkpoint["records_in_current_csv"] + len(records) > MAX_CSV_ROWS:
            file_num = int(checkpoint["current_csv_file"].split('_')[-1].split('.')[0])
            new_file_num = file_num + 1
            checkpoint["current_csv_file"] = f"bpom_products_{new_file_num:03d}.csv"
            checkpoint["records_in_current_csv"] = 0
            logging.info(f"Rotated to new CSV file: {checkpoint['current_csv_file']}")
            
        mode = 'w' if checkpoint["records_in_current_csv"] == 0 else 'a'
        write_to_csv(checkpoint["current_csv_file"], records, mode=mode)
        
        checkpoint["records_downloaded"] += len(records)
        checkpoint["records_in_current_csv"] += len(records)
        checkpoint["last_successful_offset"] = offset + API_PAGE_SIZE
        save_checkpoint(checkpoint)
        
        offset += API_PAGE_SIZE
        pages_fetched += 1
        
        print_progress(checkpoint, api_requests, total_retries)
        
        if stop_execution or pages_fetched >= max_pages:
            break
            
        delay = random.uniform(2, 5)
        logging.info(f"Sleeping for {delay:.2f} seconds to respect API limits...")
        time.sleep(delay)
        
    logging.info("Ingestion loop terminated.")
    if stop_execution:
        logging.info("Graceful interrupt completed safely.")

def generate_final_report():
    checkpoint = load_checkpoint()
    
    report = {
        "expected_records": checkpoint["total_records"],
        "downloaded_records": checkpoint["records_downloaded"],
        "csv_files": 0,
        "api_requests": 0,
        "failed_requests": 0,
        "retry_count": 0,
        "duplicate_id_count": 0,
        "duplicate_kode_qr_count": 0,
        "missing_nie_count": 0,
        "missing_kode_qr_count": 0,
        "missing_nama_produk_count": 0,
        "started_at": "",
        "completed_at": datetime.now().isoformat(),
        "duration_seconds": 0
    }
    
    seen_ids = set()
    seen_qrs = set()
    total_rows = 0
    
    files = [f for f in os.listdir(DATA_DIR) if f.startswith("bpom_products_") and f.endswith(".csv")]
    report["csv_files"] = len(files)
    
    print(f"Validating {len(files)} CSV files...")
    
    for filename in sorted(files):
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                
                row_id = row.get("id") or row.get("id_produk")
                if row_id:
                    if row_id in seen_ids:
                        report["duplicate_id_count"] += 1
                    seen_ids.add(row_id)
                
                qr = row.get("kode_qr")
                if not qr or qr.strip() == "":
                    report["missing_kode_qr_count"] += 1
                else:
                    if qr in seen_qrs:
                        report["duplicate_kode_qr_count"] += 1
                    seen_qrs.add(qr)
                    
                if not row.get("nie") or row.get("nie").strip() == "":
                    report["missing_nie_count"] += 1
                    
                if not row.get("nama_produk") or row.get("nama_produk").strip() == "":
                    report["missing_nama_produk_count"] += 1

    print("=" * 40)
    print("FINAL VALIDATION REPORT")
    print("=" * 40)
    print(f"Filter count (expected) : {report['expected_records']:,}")
    print(f"Total rows in CSVs      : {total_rows:,}")
    print(f"Records downloaded      : {report['downloaded_records']:,}")
    print(f"Duplicate IDs           : {report['duplicate_id_count']:,}")
    print(f"Duplicate Kode QR       : {report['duplicate_kode_qr_count']:,}")
    print(f"Missing NIE             : {report['missing_nie_count']:,}")
    print(f"Missing Kode QR         : {report['missing_kode_qr_count']:,}")
    print(f"Missing Nama Produk     : {report['missing_nama_produk_count']:,}")
    
    if total_rows == report['expected_records']:
        print("✅ Data completeness check PASSED!")
    else:
        print("❌ Data completeness check FAILED! Row count mismatch.")
        
    report_path = os.path.join(DATA_DIR, "ingestion_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4)
        
    print(f"Report saved to {report_path}")

if __name__ == "__main__":
    if not RUN_FULL_DOWNLOAD:
        print("Running in TEST MODE (max 3 pages)")
        run_ingestion(test_mode=True)
    else:
        print("Running in FULL DOWNLOAD MODE")
        run_ingestion(test_mode=False)
        generate_final_report()
