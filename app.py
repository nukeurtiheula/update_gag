import os
import time
import requests
import threading
from flask import Flask
from dotenv import load_dotenv

# --- 1. PENGATURAN DAN INISIALISASI ---
load_dotenv()

# Ambil konfigurasi dari Environment Variables Railway
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# Railway akan memberikan PORT secara dinamis
PORT = int(os.getenv("PORT", 5000)) 

# Pengaturan API Grow a Garden
GAGAPI_BASE_URL = "https://gagapi.onrender.com/"
ITEMS_TO_TRACK = {
    "Seeds": "seeds",
    "Eggs": "eggs",
    "Gear": "gear"
}
previous_stocks = {}

# Inisialisasi server Flask
app = Flask(__name__)

# --- 2. FUNGSI-FUNGSI UTAMA ---
def send_telegram_message(message):
    """Mengirim pesan notifikasi ke grup Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Token atau Chat ID belum diset di environment variables Railway.")
        return
        
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = { 'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown' }
    try:
        response = requests.post(api_url, data=payload)
        response.raise_for_status()
        print("Notifikasi Telegram terkirim!")
    except requests.exceptions.RequestException as e:
        print(f"Gagal mengirim notifikasi Telegram: {e}")

def check_stock(item_type, api_endpoint):
    """
    Memeriksa stok item dan mengembalikan item yang stoknya BERUBAH (dan > 0).
    """
    global previous_stocks
    api_url = f"{GAGAPI_BASE_URL}{api_endpoint}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        current_data = response.json()

        processed_stock = {}
        if isinstance(current_data, list):
            for item in current_data:
                if 'name' in item:
                    item_name = item['name']
                    if 'quantity' in item:
                        item['stock'] = item.pop('quantity')
                    processed_stock[item_name] = item
        elif isinstance(current_data, dict):
            processed_stock = current_data
        else:
            print(f"Peringatan: Data untuk '{item_type}' tidak dikenal formatnya.")
            return []

        if item_type not in previous_stocks:
            previous_stocks[item_type] = processed_stock
            print(f"Inisialisasi data stok awal untuk {item_type}.")
            return []

        previous_item_stock = previous_stocks.get(item_type, {})
        changed_stock_items = []
        
        for item_name, details in processed_stock.items():
            prev_details = previous_item_stock.get(item_name, {'stock': None})
            
            if details.get('stock', 'N/A') != prev_details.get('stock', 'N/A'):
                changed_stock_items.append({'name': item_name, 'details': details})
        
        previous_stocks[item_type] = processed_stock
        return changed_stock_items

    except requests.exceptions.RequestException as e:
        print(f"Error saat cek stok {item_type}: {e}")
        return []

def start_polling_loop():
    """
    Loop utama yang mengumpulkan perubahan stok dan langsung mengirim notifikasi.
    """
    print("Memulai pemantauan stok (Mode Lapor Perubahan Stok > 0)...")
    while True:
        print("\\nMemulai siklus pengecekan baru...")
        all_changed_items_this_cycle = {}
        for item_type, endpoint in ITEMS_TO_TRACK.items():
            changed_items = check_stock(item_type, endpoint)
            if changed_items:
                print(f"Perubahan stok terdeteksi untuk {item_type}!")
                all_changed_items_this_cycle[item_type] = changed_items
        
        if all_changed_items_this_cycle:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            message_parts = [
                "✨ *New Stock Alert!* ✨",
                f"_{timestamp}_",
                ""
            ]
            category_emojis = { "Seeds": "🌱", "Eggs": "🥚", "Gear": "⚙️" }
            for category_name, items_list in all_changed_items_this_cycle.items():
                emoji = category_emojis.get(category_name, "➡️")
                message_parts.append(f"{emoji} *{category_name}:*")
                for item in items_list:
                    name = item['name'].replace('_', ' ').title()
                    stock = item['details'].get('stock', 'N/A')
                    message_parts.append(f"- {name} : {stock}")
                message_parts.append("")
            
            message_parts.append("Happy Gardening! 🌳")
            message_parts.append("_Next check in 5 minutes._")
            full_message = "\n".join(message_parts)
            
            # Karena tidak ada webhook, panggil fungsi pengiriman pesan secara LANGSUNG
            send_telegram_message(full_message)

        print("Siklus pengecekan selesai. Menunggu 5 menit (300 detik)...")
        time.sleep(300)

# Endpoint sederhana untuk health check dari Railway
@app.route('/')
def home():
    return "Bot Notifikasi Grow a Garden Aktif."

if __name__ == '__main__':
    # Jalankan loop polling di thread terpisah agar tidak memblokir server web
    polling_thread = threading.Thread(target=start_polling_loop)
    polling_thread.daemon = True
    polling_thread.start()
    
    # Jalankan server web utama (Gunicorn akan menangani ini di Railway)
    app.run(host='0.0.0.0', port=PORT)