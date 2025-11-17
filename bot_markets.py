import requests
import time
import yfinance as yf
import statistics
from datetime import datetime

TELEGRAM_BOT_TOKEN = "8446878977:AAHmN1tLgrPf3NiRyhQCvSWfotdnowqh7KI"
TELEGRAM_CHAT_ID = "5973425345"

def send_telegram(msg: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print("Erreur Telegram:", e)

# -------------------------------
# CRYPTOS (top CoinGecko)
# -------------------------------

def get_top_cryptos():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 200,
                "page": 1
            },
            timeout=20
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("Erreur CoinGecko:", e)
        return []

def scan_cryptos():
    print("[CRYPTO] Scan...")
    coins = get_top_cryptos()

    for coin in coins:
        try:
            symbol = (coin.get("symbol") or "").upper()
            price = coin.get("current_price")
            if price is None:
                continue

            # yfinance symbol pattern "BTC-USD"
            yf_symbol = f"{symbol}-USD"

            hist = yf.Ticker(yf_symbol).history(period="1d", interval="5m")
            if hist.empty or len(hist) < 21:
                continue

            close = hist["Close"]
            volume = hist["Volume"]

            p_now = float(close.iloc[-1])
            p_prev = float(close.iloc[-2])
            v_now = float(volume.iloc[-1])
            v_avg = float(statistics.mean(volume.iloc[-20:]))

            change = (p_now - p_prev) / p_prev * 100.0
            vol_spike = (v_now / v_avg) * 100.0 if v_avg > 0 else 0.0
            ma20 = float(statistics.mean(close.iloc[-20:]))

            if change >= 1.5 and vol_spike >= 120.0 and p_now > ma20:
                msg = (
                    "SIGNAL ACHAT CRYPTO\n\n"
                    f"Symbole: {yf_symbol}\n"
                    f"Variation 5 min: {change:.2f} %\n"
                    f"Volume: {vol_spike:.1f} % de la moyenne\n"
                    f"Prix: {p_now:.4f} USD"
                )
                print(msg)
                send_telegram(msg)

        except Exception as e:
            print("Erreur crypto:", e)
            continue

# -------------------------------
# ACTIONS USA + EUROPE
# -------------------------------

STOCKS = [
    "AAPL", "TSLA", "META", "NVDA", "AMZN", "MSFT",
    "AIR.PA", "MC.PA", "BNP.PA", "TTE.PA", "ORA.PA"
]

def scan_stocks():
    print("[ACTIONS] Scan...")
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

            change = (p_now - p_prev) / p_prev * 100.0
            vol_spike = (v_now / v_avg) * 100.0 if v_avg > 0 else 0.0
            ma20 = float(statistics.mean(close.iloc[-20:]))

            if change >= 1.5 and vol_spike >= 120.0 and p_now > ma20:
                msg = (
                    "SIGNAL ACHAT ACTION\n\n"
                    f"Ticker: {ticker}\n"
                    f"Variation 5 min: {change:.2f} %\n"
                    f"Volume: {vol_spike:.1f} % de la moyenne\n"
                    f"Prix: {p_now:.2f} USD"
                )
                print(msg)
                send_telegram(msg)

        except Exception as e:
            print("Erreur action:", e)
            continue

# -------------------------------
# MAIN LOOP
# -------------------------------

print("BOT SIGNAL D'ACHAT DEMARRE")

while True:
    scan_cryptos()
    scan_stocks()
    print("[INFO] Pause 60 secondes...\n")
    time.sleep(60)
