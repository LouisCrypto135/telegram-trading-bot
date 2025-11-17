import os
import time
import requests
import statistics
import yfinance as yf

# =====================================================================
# CONFIG TELEGRAM (lues depuis Render, avec fallback en dur)
# =====================================================================

TELEGRAM_BOT_TOKEN = os.environ.get(
    "BOT_TOKEN",
    "8446878977:AAHmN1tLgrPf3NiRyhQCvSWfotdnowqh7KI"
)
TELEGRAM_CHAT_ID = os.environ.get("CHAT_ID", "5973425345")

# Intervalle entre deux scans (secondes)
SLEEP_SECONDS = 60

# =====================================================================
# OUTILS
# =====================================================================

def log(msg: str) -> None:
    print(msg, flush=True)

def send_telegram(text: str) -> None:
    """Envoie un message Telegram simple."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("Token ou chat_id manquant, message non envoye.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        log(f"Erreur Telegram: {e}")

# =====================================================================
# SCAN CRYPTOS (CoinGecko, top 200)
# =====================================================================

def get_top_cryptos():
    """Recupere le top 200 cryptos par market cap via CoinGecko."""
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 200,
        "page": 1,
        "price_change_percentage": "1h,24h"
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log(f"Erreur CoinGecko: {e}")
        return []

def scan_cryptos():
    log("[CRYPTO] Scan...")
    data = get_top_cryptos()
    if not data:
        return

    for coin in data:
        try:
            symbol = str(coin.get("symbol", "")).upper()
            name = coin.get("name", "?")
            price = coin.get("current_price")
            change_1h = coin.get("price_change_percentage_1h_in_currency") or 0.0
            change_24h = coin.get("price_change_percentage_24h_in_currency") or 0.0
            volume_24h = coin.get("total_volume") or 0
            market_cap = coin.get("market_cap") or 0

            if price is None or market_cap == 0:
                continue

            # Ratio volume / market cap (activite)
            vol_ratio = (volume_24h / market_cap) * 100.0 if market_cap > 0 else 0.0

            # Conditions "signal d achat"
            if change_1h >= 2.0 and 0 < change_24h <= 15.0 and vol_ratio >= 5.0:
                msg = (
                    "SIGNAL ACHAT CRYPTO\n\n"
                    f"{name} ({symbol})\n"
                    f"Prix: {price:.4f} USD\n"
                    f"Changement 1h: {change_1h:.2f} %\n"
                    f"Changement 24h: {change_24h:.2f} %\n"
                    f"Volume/MarketCap: {vol_ratio:.2f} %"
                )
                log(msg)
                send_telegram(msg)

        except Exception as e:
            log(f"Erreur sur coin {coin.get('id', '?')}: {e}")
            continue

# =====================================================================
# SCAN ACTIONS (USA + EUROPE) via yfinance
# =====================================================================

STOCKS = [
    # USA
    "AAPL", "MSFT", "NVDA", "META", "AMZN", "TSLA",
    # EUROPE (Euronext Paris)
    "AIR.PA",  # Airbus
    "MC.PA",   # LVMH
    "BNP.PA",  # BNP Paribas
    "TTE.PA",  # TotalEnergies
    "ORA.PA"   # Orange
]

def scan_stocks():
    log("[ACTIONS] Scan...")
    for ticker in STOCKS:
        try:
            hist = yf.Ticker(ticker).history(period="1d", interval="5m")
            if hist.empty or len(hist) < 21:
                continue

            close = hist["Close"]
            volume = hist["Volume"]

            p_now = float(close.iloc[-1])
            p_prev = float(close.iloc[-2])
            v_now = float(volume.iloc[-1])
            v_avg = float(statistics.mean(volume.iloc[-20:]))

            change_5m = (p_now - p_prev) / p_prev * 100.0
            vol_spike = (v_now / v_avg) * 100.0 if v_avg > 0 else 0.0
            ma20 = float(statistics.mean(close.iloc[-20:]))

            # Conditions "signal d achat" pour actions
            if change_5m >= 1.5 and vol_spike >= 120.0 and p_now > ma20:
                msg = (
                    "SIGNAL ACHAT ACTION\n\n"
                    f"Ticker: {ticker}\n"
                    f"Variation 5 min: {change_5m:.2f} %\n"
                    f"Volume vs moyenne: {vol_spike:.1f} %\n"
                    f"Prix: {p_now:.2f} USD"
                )
                log(msg)
                send_telegram(msg)

        except Exception as e:
            log(f"Erreur action {ticker}: {e}")
            continue

# =====================================================================
# MAIN LOOP
# =====================================================================

def main():
    log("BOT SIGNAL D ACHAT DEMARRE")
    send_telegram("Bot demarre : scan cryptos + actions en continu.")

    while True:
        scan_cryptos()
        scan_stocks()
        log(f"[INFO] Pause {SLEEP_SECONDS} secondes...\n")
        time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    main()
