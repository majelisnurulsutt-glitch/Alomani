import requests
import time
import schedule
import os
from datetime import datetime

# ── CONFIG dari Environment Variables ───────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID   = os.environ.get("CHAT_ID", "")

# Filter thresholds
MIN_GAIN_PCT   = 50
MIN_VOLUME_USD = 50_000
MIN_LIQ_USD    = 10_000
MIN_MC_USD     = 100_000
MAX_MC_USD     = 50_000_000

TIER_MEGA_MIN  = 300
TIER_MID_MIN   = 100

CHAINS = ["solana", "ethereum", "bsc", "base", "arbitrum", "polygon", "avalanche", "optimism"]

# ── HELPERS ──────────────────────────────────────────────────────────────
def fmt_usd(n):
    try:
        n = float(n)
        if n >= 1_000_000_000: return f"${n/1e9:.2f}B"
        if n >= 1_000_000:     return f"${n/1e6:.2f}M"
        if n >= 1_000:         return f"${n/1e3:.1f}K"
        return f"${n:.2f}"
    except:
        return "–"

def fmt_price(n):
    try:
        n = float(n)
        if n < 0.000001: return f"${n:.2e}"
        if n < 0.01:     return f"${n:.6f}"
        if n < 1:        return f"${n:.4f}"
        return f"${n:.2f}"
    except:
        return "–"

def fmt_pct(n):
    try:
        n = float(n)
        sign = "+" if n >= 0 else ""
        return f"{sign}{n:.1f}%"
    except:
        return "–"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ── TELEGRAM ─────────────────────────────────────────────────────────────
def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.status_code == 200, r.text
    except Exception as e:
        return False, str(e)

def send_long_message(text):
    """Kirim pesan panjang dalam beberapa bagian jika perlu"""
    MAX_LEN = 4000
    if len(text) <= MAX_LEN:
        ok, resp = send_telegram(text)
        return ok

    # Split per token entry (double newline)
    parts = text.split("\n\n")
    chunk = ""
    for part in parts:
        if len(chunk) + len(part) + 2 > MAX_LEN:
            send_telegram(chunk)
            time.sleep(0.8)
            chunk = part
        else:
            chunk += "\n\n" + part if chunk else part
    if chunk:
        send_telegram(chunk)
    return True

# ── FETCH DATA ────────────────────────────────────────────────────────────
def fetch_pairs():
    all_pairs = []
    seen = set()

    # 1. Token boosts trending
    try:
        r = requests.get("https://api.dexscreener.com/token-boosts/top/v1", timeout=10)
        if r.status_code == 200:
            boosts = r.json() if isinstance(r.json(), list) else []
            addresses = [b.get("tokenAddress") for b in boosts[:20] if b.get("tokenAddress")]
            for addr in addresses:
                try:
                    pr = requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{addr}", timeout=8)
                    if pr.status_code == 200:
                        pairs = pr.json().get("pairs") or []
                        for p in pairs:
                            key = p.get("pairAddress", "")
                            if key and key not in seen:
                                seen.add(key)
                                all_pairs.append(p)
                    time.sleep(0.2)
                except:
                    continue
    except Exception as e:
        log(f"⚠ Boost fetch error: {e}")

    # 2. Per-chain search
    for chain in CHAINS:
        try:
            url = f"https://api.dexscreener.com/latest/dex/search?q=USDC&chainId={chain}"
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                pairs = r.json().get("pairs") or []
                for p in pairs:
                    key = p.get("pairAddress", "")
                    if key and key not in seen:
                        seen.add(key)
                        all_pairs.append(p)
            time.sleep(0.15)
        except:
            continue

    return all_pairs

# ── FILTER ────────────────────────────────────────────────────────────────
def apply_filters(pairs):
    results = []
    for p in pairs:
        try:
            gain_24h = float(p.get("priceChange", {}).get("h24") or 0)
            gain_1h  = float(p.get("priceChange", {}).get("h1")  or 0)
            vol_24h  = float(p.get("volume",      {}).get("h24") or 0)
            liq      = float(p.get("liquidity",   {}).get("usd") or 0)
            mc       = float(p.get("marketCap")   or 0)

            if gain_24h < MIN_GAIN_PCT:            continue
            if vol_24h  < MIN_VOLUME_USD:          continue
            if liq      < MIN_LIQ_USD:             continue
            if mc > 0 and mc < MIN_MC_USD:         continue
            if mc > 0 and mc > MAX_MC_USD:         continue
            if gain_1h  <= 0:                      continue  # anomali masih aktif

            results.append(p)
        except:
            continue

    results.sort(
        key=lambda x: float(x.get("priceChange", {}).get("h24") or 0),
        reverse=True
    )
    return results

# ── BUILD REPORT ──────────────────────────────────────────────────────────
def build_report(tokens):
    now   = datetime.now().strftime("%d %b %Y, %H:%M WIB")
    total = len(tokens)

    mega  = [t for t in tokens if float(t.get("priceChange",{}).get("h24") or 0) >= TIER_MEGA_MIN]
    mid   = [t for t in tokens if TIER_MID_MIN <= float(t.get("priceChange",{}).get("h24") or 0) < TIER_MEGA_MIN]
    micro = [t for t in tokens if float(t.get("priceChange",{}).get("h24") or 0) < TIER_MID_MIN]

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "📡 <b>CRYPTO ANOMALI REPORT</b>",
        f"🕐 {now}",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📊 Total Anomali: <b>{total} token</b>",
        f"🔴 Mega (+300%): {len(mega)}  🟠 Mid (+100%): {len(mid)}  🟡 Micro (+50%): {len(micro)}",
        f"🌐 Chain: ALL | Filter aktif ✅",
        "",
    ]

    if total == 0:
        lines.append("⚪️ Tidak ada anomali yang memenuhi semua filter saat ini.")
        lines.append("Bot akan scan kembali sesuai jadwal.")
    else:
        for tier_name, tier_emoji, tier_tokens in [
            ("MEGA ANOMALI",  "🔴", mega),
            ("MID ANOMALI",   "🟠", mid),
            ("MICRO ANOMALI", "🟡", micro),
        ]:
            if not tier_tokens:
                continue

            lines.append(f"{tier_emoji} <b>{tier_name}</b> ({len(tier_tokens)} token)")
            lines.append("──────────────────────")

            for i, t in enumerate(tier_tokens[:8], 1):
                sym      = t.get("baseToken", {}).get("symbol", "?")
                name     = t.get("baseToken", {}).get("name", sym)
                chain    = (t.get("chainId") or "?").upper()
                price    = fmt_price(t.get("priceUsd"))
                gain_24h = float(t.get("priceChange", {}).get("h24") or 0)
                gain_1h  = float(t.get("priceChange", {}).get("h1")  or 0)
                gain_6h  = float(t.get("priceChange", {}).get("h6")  or 0)
                vol      = fmt_usd(t.get("volume",    {}).get("h24"))
                liq      = fmt_usd(t.get("liquidity", {}).get("usd"))
                mc       = fmt_usd(t.get("marketCap"))
                url      = t.get("url") or "https://dexscreener.com"

                lines.append(
                    f"\n<b>{i}. ${sym}</b> — {name}\n"
                    f"   ⛓ Chain : {chain}\n"
                    f"   💲 Harga : {price}\n"
                    f"   📈 Gain  : 1h {fmt_pct(gain_1h)} | 6h {fmt_pct(gain_6h)} | 24h {fmt_pct(gain_24h)}\n"
                    f"   📊 Vol   : {vol}\n"
                    f"   💧 Liq   : {liq}\n"
                    f"   🏦 MCap  : {mc}\n"
                    f"   🔗 <a href='{url}'>Dexscreener</a>"
                )

            lines.append("")

    lines += [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "⚠️ <i>Informasi saja. Bukan saran investasi. DYOR.</i>",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    return "\n".join(lines)

# ── JOB ───────────────────────────────────────────────────────────────────
def run_scan():
    log("🔍 Mulai scan...")
    try:
        pairs    = fetch_pairs()
        log(f"   → {len(pairs)} pair ditemukan")
        filtered = apply_filters(pairs)
        log(f"   → {len(filtered)} token lolos filter")
        report   = build_report(filtered)
        ok       = send_long_message(report)
        if ok:
            log("✅ Laporan terkirim ke Telegram")
        else:
            log("❌ Gagal kirim ke Telegram")
    except Exception as e:
        log(f"❌ Error saat scan: {e}")
        send_telegram(f"⚠️ <b>Crypto Anomali Bot Error</b>\n\n<code>{str(e)}</code>")

# ── SCHEDULER ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log("🤖 Crypto Anomali Bot starting...")
    log(f"   Jadwal: setiap 6 jam (00:00 / 06:00 / 12:00 / 18:00)")

    if not BOT_TOKEN or not CHAT_ID:
        log("❌ BOT_TOKEN atau CHAT_ID tidak ditemukan di environment variables!")
        exit(1)

    # Kirim notifikasi bot aktif
    send_telegram(
        "🤖 <b>Crypto Anomali Bot aktif!</b>\n\n"
        "Scan pertama akan dimulai sekarang.\n"
        "Jadwal berikutnya: setiap 6 jam.\n\n"
        "Filter aktif:\n"
        "• Gain ≥ +50% (1h masih positif)\n"
        "• Volume ≥ $50K\n"
        "• Liquidity ≥ $10K\n"
        "• Market Cap $100K – $50M\n"
        "• Semua chain"
    )

    # Langsung scan pertama saat start
    run_scan()

    # Jadwal rutin setiap 6 jam
    schedule.every(6).hours.do(run_scan)

    while True:
        schedule.run_pending()
        time.sleep(60)
