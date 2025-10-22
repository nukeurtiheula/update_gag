import os
import time
import requests
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
        print("Token atau Chat ID belum diset.")
        return
        
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = { 'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown' }
    try:
        # Menambahkan timeout untuk mencegah skrip macet
        response = requests.post(api_url, data=payload, timeout=15)
        response.raise_for_status()
        print("Laporan perubahan stok terkirim!")
    except requests.exceptions.RequestException as e:
        print(f"Gagal mengirim laporan: {e}")

def get_stock_from_api(api_endpoint):
    """Mengambil data stok dari satu endpoint API GAGAPI."""
    api_url = f"{GAGAPI_BASE_URL}{api_endpoint}"
    try:
        # Menambahkan timeout 20 detik
        response = requests.get(api_url, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengambil data dari {api_endpoint}: {e}")
        return [] # Kembalikan list kosong jika gagal, agar konsisten

def start_reporting_loop():
    """
    Loop utama yang mengecek setiap 1 menit dan hanya lapor jika ada perubahan.
    """
    print("Memulai mode Laporan Perubahan Stok...")
    
    # --- VARIABEL 'INGATAN' UNTUK MENYIMPAN STOK TERAKHIR ---
    last_known_stock = {}

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Memulai siklus pengecekan baru...")
        
        current_stock_snapshot = {}
        has_any_stock_to_report = False

        # Langkah 1: Ambil data stok terbaru dari semua kategori
        for category_name, endpoint in ITEMS_TO_TRACK.items():
            current_stock_snapshot[category_name] = get_stock_from_api(endpoint)
        
        # Langkah 2: Bandingkan data terbaru dengan data di 'ingatan'
        if current_stock_snapshot != last_known_stock:
            print(">>> Perubahan stok terdeteksi! Menyiapkan laporan lengkap...")

            # Buat pesan notifikasi hanya jika ada perubahan
            timestamp = datetime.now(pytz.timezone("Asia/Jakarta")).strftime("%Y-%m-%d %H:%M:%S WIB")
            message_parts = [
                "✨ *Store Stock Updated!* ✨",
                f"_{timestamp}_",
                ""
            ]
            category_emojis = { "Seeds": "🌱", "Eggs": "🥚", "Gear": "⚙️" }

            for category_name, items_list in current_stock_snapshot.items():
                items_with_stock_messages = []
                
                for item in items_list:
                    # Filter: Hanya tampilkan item yang stoknya lebih dari 0
                    if int(item.get('stock', 0)) > 0:
                        name = item.get('name', 'N/A').replace('_', ' ').title()
                        stock = item.get('stock')
                        items_with_stock_messages.append(f"- {name} : {stock}")
                        has_any_stock_to_report = True

                # Hanya tampilkan judul kategori jika ada item yang tersedia di dalamnya
                if items_with_stock_messages:
                    emoji = category_emojis.get(category_name, "➡️")
                    message_parts.append(f"{emoji} *{category_name}:*")
                    message_parts.extend(items_with_stock_messages)
                    message_parts.append("")
            
            # Kirim notifikasi hanya jika ada setidaknya satu item yang tersedia untuk dilaporkan
            if has_any_stock_to_report:
                message_parts.append("Happy Gardening! 🌳")
                full_message = "\n".join(message_parts)
                send_telegram_message(full_message)
            else:
                print("Stok berubah, tetapi semua item menjadi kosong. Tidak ada laporan yang dikirim.")

            # Langkah 3: PENTING! Perbarui 'ingatan' dengan data yang baru
            last_known_stock = current_stock_snapshot
        
        else:
            print("Tidak ada perubahan stok. Melewati pengiriman.")

        # Menunggu 1 menit sebelum siklus berikutnya
        print("Siklus selesai. Menunggu 1 menit (60 detik)...")
        time.sleep(60)

if __name__ == '__main__':
    if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"):
        print("ERROR: Pastikan TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID sudah diset.")
    else:
        start_reporting_loop()