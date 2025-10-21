import os
import time
import requests
import threading
from datetime import datetime
import pytz
from dotenv import load_dotenv

# --- 1. PENGATURAN DAN INISIALISASI ---
load_dotenv()

# Ambil konfigurasi dari Environment Variables Railway
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Pengaturan API Grow a Garden
GAGAPI_BASE_URL = "https://gagapi.onrender.com/"
ITEMS_TO_TRACK = {
    "Seeds": "seeds",
    "Eggs": "eggs",
    "Gear": "gear"
}

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
        print("Laporan rutin terkirim!")
    except requests.exceptions.RequestException as e:
        print(f"Gagal mengirim laporan: {e}")

def get_current_stock(item_type, api_endpoint):
    """
    Hanya mengambil data stok saat ini dari API dan mengembalikannya apa adanya.
    """
    api_url = f"{GAGAPI_BASE_URL}{api_endpoint}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        current_data = response.json()

        # Konversi data ke format yang konsisten (list of dicts)
        if isinstance(current_data, list):
            return current_data
        elif isinstance(current_data, dict):
            # Jika format lama kembali, ubah ke format baru
            return [{"name": name, **details} for name, details in current_data.items()]
        else:
            print(f"Peringatan: Data untuk '{item_type}' tidak dikenal formatnya.")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengambil data untuk {item_type}: {e}")
        return []

def start_reporting_loop():
    """
    Loop utama yang mengirim laporan rutin setiap 5 menit.
    """
    print("Memulai mode Laporan Rutin Toko...")
    while True:
        print("\\nMemulai siklus laporan baru...")
        
        all_current_items = {}

        # Cek setiap kategori dan kumpulkan isinya
        for item_type, endpoint in ITEMS_TO_TRACK.items():
            current_items = get_current_stock(item_type, endpoint)
            if current_items: # Jika ada item di kategori ini
                all_current_items[item_type] = current_items
        
        # Setelah semua kategori dicek, buat satu laporan besar
        if all_current_items:
            utc_now = datetime.now(pytz.utc)
            wib_timezone = pytz.timezone("Asia/Jakarta")
            wib_now = utc_now.astimezone(wib_timezone)
            timestamp = wib_now.strftime("%Y-%m-%d %H:%M:%S WIB")

            message_parts = [
                "✨ *New Stock Alert!* ✨",
                f"_{timestamp}_",
                ""
            ]
            category_emojis = { "Seeds": "🌱", "Eggs": "🥚", "Gear": "⚙️" }
            for category_name, items_list in all_current_items.items():
                emoji = category_emojis.get(category_name, "➡️")
                message_parts.append(f"{emoji} *{category_name}:*")
                for item in items_list:
                    name = item.get('name', 'N/A').replace('_', ' ').title()
                    stock = item.get('quantity', item.get('stock', 'N/A'))
                    message_parts.append(f"- {name} : {stock}")
                message_parts.append("")
            
            # ==================== FOOTER DITAMBAHKAN KEMBALI DI SINI ====================
            message_parts.append("Happy Gardening! 🌳")
            message_parts.append("_Next check in 5 minutes._")
            # ==========================================================================
            
            full_message = "\n".join(message_parts)
            send_telegram_message(full_message)
        else:
            print("Toko tampaknya sedang kosong, tidak ada laporan yang dikirim.")

        print("Siklus laporan selesai. Menunggu 5 menit (300 detik)...")
        time.sleep(300)

if __name__ == '__main__':
    # Pastikan variabel sudah diset sebelum memulai
    if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"):
        print("ERROR: Pastikan TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID sudah diset di Environment Variables Railway.")
    else:
        # Langsung jalankan loop utama
        start_reporting_loop()