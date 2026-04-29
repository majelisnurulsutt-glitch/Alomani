# 📡 Crypto Anomali Bot

Bot Telegram otomatis yang scan token dengan pergerakan anomali dari semua chain via Dexscreener API.

## Filter Aktif
- Gain 24h ≥ +50% dan gain 1h masih positif (anomali masih aktif)
- Volume 24h ≥ $50,000
- Liquidity ≥ $10,000
- Market Cap $100K – $50M
- Semua chain (SOL, ETH, BSC, BASE, ARB, MATIC, AVAX, OP)

## Tier Laporan
- 🔴 Mega Anomali → gain ≥ +300%
- 🟠 Mid Anomali  → gain +100% – +300%
- 🟡 Micro Anomali → gain +50% – +100%

---

## 🚀 Deploy ke Railway

### Langkah 1 — Upload ke GitHub
1. Buat repo baru di GitHub (misal: `crypto-anomali-bot`)
2. Upload 4 file ini: `main.py`, `requirements.txt`, `Procfile`, `README.md`

### Langkah 2 — Buat project di Railway
1. Buka [railway.app](https://railway.app) → login dengan GitHub
2. Klik **New Project** → **Deploy from GitHub repo**
3. Pilih repo `crypto-anomali-bot`

### Langkah 3 — Set Environment Variables
Di Railway, masuk ke tab **Variables**, tambahkan:

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | token bot dari @BotFather |
| `CHAT_ID` | chat ID kamu dari @userinfobot |

⚠️ JANGAN tulis token langsung di kode — selalu gunakan Variables.

### Langkah 4 — Deploy
1. Railway otomatis detect `Procfile` dan jalankan `python main.py`
2. Cek tab **Logs** untuk memastikan bot berjalan
3. Bot akan kirim notifikasi ke Telegram saat pertama aktif

---

## ⚙️ Mengubah Jadwal Scan

Default: setiap **6 jam**.

Untuk mengubah, edit baris ini di `main.py`:
```python
schedule.every(6).hours.do(run_scan)   # setiap 6 jam
schedule.every(3).hours.do(run_scan)   # setiap 3 jam
schedule.every(12).hours.do(run_scan)  # setiap 12 jam
```

---

## ⚠️ Disclaimer
Data bersifat informatif. Bukan saran investasi. DYOR.
