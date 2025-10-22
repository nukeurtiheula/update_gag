import os
import time
import requests
from datetime import datetime
import pytz
from dotenv import load_dotenv

# --- 1. PENGATURAN DAN INISIALISASI ---
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

GAGAPI_BASE_URL = "https://gagapi.onrender.com/"
ITEMS_TO_TRACK = {
    "Seeds": "seeds",
    "Eggs": "eggs",
    "Gear": "gear"
}

# --- 2. FUNGSI-FUNGSI UTAMA ---
def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Token atau Chat ID belum diset.")
        return
        
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = { 'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown' }
    try:
        response = requests.post(api_url, data=payload, timeout=15)
        response.raise_for_status()
        print("Laporan perubahan stok terkirim!")
    except requests.exceptions.RequestException as e:
        print(f"Gagal mengirim laporan: {e}")

def get_stock_from_api(api_endpoint):
    api_url = f"{GAGAPI_BASE_URL}{api_endpoint}"
    try:
        response = requests.get(api_url, timeout=20)
        response.raise_for_status()
        data = response.json()
        # --- TAMBAHAN: Cetak data mentah yang diterima untuk debugging ---
        print(f"Data mentah diterima dari '{api_endpoint}': {data}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengambil data dari {api_endpoint}: {e}")
        return []

def start_reporting_loop():
    print("Memulai mode Laporan Perubahan Stok...")
    last_known_stock = {}

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Memulai siklus pengecekan...")
        
        current_stock_snapshot = {}
        for category_name, endpoint in ITEMS_TO_TRACK.items():
            current_stock_snapshot[category_name] = get_stock_from_api(endpoint)
        
        if current_stock_snapshot != last_known_stock:
            print(">>> Perubahan terdeteksi! Mengirim laporan lengkap...")

            timestamp = datetime.now(pytz.timezone("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M:%S WIB")
            message_parts = [
                "✨ *Stock Updated!* ✨",
                f"_{timestamp}_",
                ""
            ]
            category_emojis = { "Seeds": "🌱", "Eggs": "🥚", "Gear": "⚙️" }

            for category_name, items_list in current_stock_snapshot.items():
                if items_list:
                    message_parts.append(f"{category_emojis.get(category_name, '➡️')} *{category_name}:*")
                    for item in items_list:
                        name = item.get('name', 'N/A').replace('_', ' ').title()
                        
                        # ==================== PERUBAHAN UTAMA DI SINI ====================
                        # Logika ini mencoba mencari nilai stok dengan beberapa kemungkinan nama.
                        # Ini persis menyamakan dengan apa yang GAGAPI berikan.
                        
                        stock = 'N/A' # Default jika tidak ada key stok sama sekali
                        if 'stock' in item:
                            stock = item['stock']
                        elif 'quantity' in item: # Coba cari 'quantity' sebagai alternatif
                            stock = item['quantity']
                        # ===============================================================
                        
                        message_parts.append(f"- {name} : {stock}")
                    message_parts.append("")
            
            message_parts.append("Happy Gardening! 🌳")
            message_parts.append("_Next check in 5 minute._")
            
            full_message = "\n".join(message_parts)
            send_telegram_message(full_message)

            last_known_stock = current_stock_snapshot
        
        else:
            print("Tidak ada perubahan stok. Melewati pengiriman.")

        print("Siklus selesai. Menunggu 1 menit...")
        time.sleep(60)

if __name__ == '__main__':
    if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"):
        print("ERROR: Pastikan TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID sudah diset.")
    else:
        start_reporting_loop()