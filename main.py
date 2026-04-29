import os
import requests
import time
from datetime import datetime

# Configuration from environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
AGENTROUTER_API_KEY = os.environ.get("AGENTROUTER_API_KEY")

# Filter Constants
MIN_GAIN_24H = 50.0
MIN_VOLUME_24H = 50000.0
MIN_LIQUIDITY = 10000.0
MIN_MARKET_CAP = 100000.0
MAX_MARKET_CAP = 50000000.0
MIN_PRICE = 0.01
MIN_TOKEN_AGE_DAYS = 7

def fetch_boosts():
    """Fetch top boosted tokens from Dexscreener."""
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching boosts: {e}")
    return []

def fetch_token_pairs(token_address):
    """Fetch all pairs for a specific token address."""
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json().get('pairs', [])
    except Exception as e:
        print(f"Error fetching token pairs for {token_address}: {e}")
    return []

def get_token_age_days(pair_created_at):
    """Calculate token age in days from timestamp."""
    if not pair_created_at:
        return 0
    created_time = datetime.fromtimestamp(pair_created_at / 1000)
    age = datetime.now() - created_time
    return age.days

def filter_and_categorize(boosts):
    """Filter tokens based on criteria and categorize them into tiers."""
    results = {
        "Mega": [],
        "Mid": [],
        "Micro": []
    }
    
    processed_tokens = set()
    
    for boost in boosts:
        token_address = boost.get('tokenAddress')
        if not token_address or token_address in processed_tokens:
            continue
        
        processed_tokens.add(token_address)
        pairs = fetch_token_pairs(token_address)
        if not pairs:
            continue
            
        # Use the pair with the highest liquidity
        best_pair = max(pairs, key=lambda x: x.get('liquidity', {}).get('usd', 0))
        
        price_usd = float(best_pair.get('priceUsd', 0))
        gain_24h = float(best_pair.get('priceChange', {}).get('h24', 0))
        gain_1h = float(best_pair.get('priceChange', {}).get('h1', 0))
        volume_24h = float(best_pair.get('volume', {}).get('h24', 0))
        liquidity = float(best_pair.get('liquidity', {}).get('usd', 0))
        market_cap = float(best_pair.get('marketCap', 0) or best_pair.get('fdv', 0))
        age_days = get_token_age_days(best_pair.get('pairCreatedAt'))
        
        # Apply Filters
        if (gain_24h >= MIN_GAIN_24H and 
            gain_1h > 0 and
            volume_24h >= MIN_VOLUME_24H and 
            liquidity >= MIN_LIQUIDITY and 
            market_cap >= MIN_MARKET_CAP and 
            market_cap <= MAX_MARKET_CAP and
            price_usd >= MIN_PRICE and
            age_days >= MIN_TOKEN_AGE_DAYS):
            
            token_data = {
                "symbol": best_pair.get('baseToken', {}).get('symbol'),
                "name": best_pair.get('baseToken', {}).get('name'),
                "chain": best_pair.get('chainId').upper(),
                "gain_24h": gain_24h,
                "volume": volume_24h,
                "liquidity": liquidity,
                "mcap": market_cap,
                "url": best_pair.get('url')
            }
            
            # Categorize
            if gain_24h >= 300:
                results["Mega"].append(token_data)
            elif market_cap >= 1000000:
                results["Mid"].append(token_data)
            else:
                results["Micro"].append(token_data)
                
        # Rate limiting for API calls
        time.sleep(0.2)
        
    return results

def generate_narrative(token_data):
    """Generate narrative using Claude via AgentRouter."""
    if not AGENTROUTER_API_KEY:
        return "Konteks tidak tersedia (API Key missing)."
        
    prompt = f"Berikan narasi singkat (2-3 kalimat) dalam Bahasa Indonesia tentang kenapa token {token_data['symbol']} ({token_data['name']}) di chain {token_data['chain']} mungkin mengalami kenaikan {token_data['gain_24h']}% dengan volume ${token_data['volume']:,.0f}. Fokus pada analisis data dan kemungkinan tren pasar. Jangan berikan saran investasi."
    
    try:
        response = requests.post(
            "https://agentrouter.org/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {AGENTROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "claude-opus-4-6",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error generating narrative: {e}")
    
    return "Gagal mendapatkan narasi otomatis."

def send_telegram_report(categorized_tokens):
    """Format and send the report to Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram configuration missing.")
        return

    report = "🚀 *CRYPTO ANOMALI REPORT*\n"
    report += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    found_any = False
    for tier, tokens in categorized_tokens.items():
        if not tokens:
            continue
        
        found_any = True
        report += f"*{tier} Anomali*\n"
        for token in tokens:
            narrative = generate_narrative(token)
            report += f"🔴 ${token['symbol']} +{token['gain_24h']}% ({token['chain']})\n"
            report += f"💡 *Konteks:* {narrative}\n"
            report += f"📊 Vol: ${token['volume']:,.0f} | Liq: ${token['liquidity']:,.0f} | MCap: ${token['mcap']:,.0f}\n"
            report += f"🔗 [Dexscreener]({token['url']})\n\n"
            
    if not found_any:
        report += "Tidak ada anomali yang ditemukan dalam scan kali ini."

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": report,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        })
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def main():
    print("Starting Crypto Anomali Scan...")
    boosts = fetch_boosts()
    print(f"Fetched {len(boosts)} boosted tokens.")
    categorized = filter_and_categorize(boosts)
    send_telegram_report(categorized)
    print("Scan complete and report sent.")

if __name__ == "__main__":
    main()
