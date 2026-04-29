# Crypto Anomali Bot

Bot ini memantau token di Dexscreener yang mengalami kenaikan harga signifikan (anomali) dan mengirimkan laporannya ke Telegram dengan narasi otomatis dari Claude AI.

## Fitur
- Fetch data otomatis dari Dexscreener API.
- Filter ketat: Gain >50%, Volume >$50K, Liquidity >$10K, Market Cap $100K-$50M.
- Narasi otomatis menggunakan Claude AI (via AgentRouter).
- Laporan terformat di Telegram.

## Cara Deploy ke Railway
1. Buat repository baru di GitHub dan upload semua file ini.
2. Hubungkan repository ke [Railway](https://railway.app/).
3. Tambahkan Environment Variables berikut di Railway:
   - `BOT_TOKEN`: Token bot Telegram dari @BotFather.
   - `CHAT_ID`: ID chat Telegram kamu.
   - `AGENTROUTER_API_KEY`: API Key dari AgentRouter.
4. Railway akan otomatis menjalankan bot sebagai worker.

## Disclaimer
Data ini hanya untuk tujuan informasi. Bukan saran investasi. Selalu lakukan riset sendiri (DYOR).
