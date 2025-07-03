# SmartDCA-Pro Bot for SOL/USDT (Trailing TP, RSI Filter, Telegram Alerts)
import requests, time
from config import *

def get_price():
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={TRADING_PAIR}"
    return float(requests.get(url).json()['price'])

def get_rsi(symbol, interval='1h', limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url).json()
    closes = [float(x[4]) for x in data]
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        (gains if delta > 0 else losses).append(abs(delta))
    avg_gain = sum(gains[-14:]) / 14
    avg_loss = sum(losses[-14:]) / 14
    rs = avg_gain / avg_loss if avg_loss else 0.0001
    rsi = 100 - (100 / (1 + rs))
    return rsi

def send_telegram(message):
    if not TELEGRAM_ENABLED: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=data)

entries = []
max_drawdown_reached = False
trailing_tp_price = None

def execute_trade():
    global entries, max_drawdown_reached, trailing_tp_price
    price = get_price()
    rsi = get_rsi(TRADING_PAIR)

    if rsi < RSI_BUY_LIMIT:
        send_telegram(f"⚠️ RSI too low ({rsi:.2f}). Skipping buy.")
        return

    if len(entries) == 0:
        entries.append(price)
        send_telegram(f"✅ [ENTRY 1] Bought at ${price:.2f}")
        trailing_tp_price = price * (1 + TP_TRAIL_PERCENT / 100)
        return

    last_entry = entries[-1]
    if price <= last_entry * (1 - DCA_GAP_PERCENT / 100) and len(entries) < MAX_DCA_ENTRIES:
        entries.append(price)
        send_telegram(f"✅ [ENTRY {len(entries)}] Bought at ${price:.2f}")
        trailing_tp_price = price * (1 + TP_TRAIL_PERCENT / 100)
        return

    if trailing_tp_price and price > trailing_tp_price:
        trailing_tp_price = price * (1 - TP_TRAIL_CALLBACK / 100)

    if trailing_tp_price and price < trailing_tp_price:
        avg_price = sum(entries) / len(entries)
        profit = (price - avg_price) * len(entries)
        send_telegram(f"📈 [SELL] Sold all at ${price:.2f} | Profit: ${profit:.2f}")
        entries.clear()
        trailing_tp_price = None

    if entries:
        avg = sum(entries) / len(entries)
        drop = (1 - price / avg) * 100
        if drop >= MAX_TOTAL_DRAWDOWN and not max_drawdown_reached:
            max_drawdown_reached = True
            send_telegram(f"🚨 Drawdown Alert: –{drop:.2f}% from avg entry. Bot paused.")

def main():
    send_telegram("🤖 SmartDCA-Pro Bot started.")
    while True:
        try:
            if not max_drawdown_reached:
                execute_trade()
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            send_telegram(f"❌ Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
