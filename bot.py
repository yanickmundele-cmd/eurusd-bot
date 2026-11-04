import os
import threading
import requests
import json
import websocket
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "9264641964:AAEC_Ffv61DJ9SYviVbXTgiEZnmI3XuQsh4"
CHAT_ID = 7548965711

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Deriv en ligne ✅"

def get_yahoo_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}=X"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        return r['chart']['result'][0]['meta']['regularMarketPrice']
    except:
        return None

def get_deriv_price(symbol):
    try:
        ws = websocket.create_connection("wss://ws.derivws.com/websockets/v3?app_id=1089", timeout=15)
        ws.send(json.dumps({"ticks_history": symbol, "end": "latest", "count": 1, "style": "ticks"}))
        for _ in range(5):
            data = json.loads(ws.recv())
            if "history" in data and "prices" in data["history"]:
                price = data["history"]["prices"][-1]
                ws.close()
                return float(price)
            if "tick" in data:
                price = data["tick"]["quote"]
                ws.close()
                return float(price)
        ws.close()
        return None
    except Exception as e:
        print(f"Erreur Deriv {symbol}: {e}")
        return None

def analyse_all():
    msg = "📊 SIGNAUX DERIV + FOREX - Toutes les 5 min\n\n"

    eurusd = get_yahoo_price("EURUSD")
    if eurusd:
        if eurusd <= 1.12150:
            msg += f"🟢 EURUSD: {eurusd:.5f} -> BUY | Entrée {eurusd:.5f} | SL 1.11850 | TP 1.12600\n"
        elif eurusd <= 1.12350:
            msg += f"🟡 EURUSD: {eurusd:.5f} -> PATIENCE, on attend 1.12150\n"
        else:
            msg += f"🔴 EURUSD: {eurusd:.5f} -> TROP HAUT, pas d'entrée\n"
    else:
        msg += "⚠️ EURUSD: prix indisponible\n"

    gbpusd = get_yahoo_price("GBPUSD")
    if gbpusd:
        if gbpusd <= 1.3410:
            msg += f"🟢 GBPUSD: {gbpusd:.5f} -> BUY ZONE 1.3410\n"
        else:
            msg += f"🟡 GBPUSD: {gbpusd:.5f} -> PATIENCE, attend 1.3410\n"

    gold = get_yahoo_price("GC")
    if gold:
        if gold >= 4074:
            msg += f"🟢 GOLD: {gold:.1f} -> BUY, cassure 4074\n"
        elif gold <= 4000:
            msg += f"🟢 GOLD: {gold:.1f} -> BUY ZONE 4000\n"
        else:
            msg += f"🟡 GOLD: {gold:.1f} -> PATIENCE entre 4000 et 4074\n"

    btc = get_yahoo_price("BTC-USD")
    if btc:
        if btc >= 80300:
            msg += f"🟢 BTC: {btc:.0f} -> BUY cassure 80300\n"
        else:
            msg += f"🟡 BTC: {btc:.0f} -> PATIENCE, attend 80300\n"

    msg += "\n--- INDICES DERIV ---\n"

    for name, symbol in [("V75", "R_75"), ("V100", "R_100"), ("V50", "R_50"), ("V25", "R_25")]:
        p = get_deriv_price(symbol)
        if p:
            msg += f"📈 {name}: {p:.2f} -> Surveille, en attente de signal\n"
        else:
            msg += f"⚠️ {name}: indisponible\n"

    for name, symbol in [("BOOM 1000", "BOOM_1000"), ("CRASH 1000", "CRASH_1000"), ("BOOM 500", "BOOM_500"), ("CRASH 500", "CRASH_500")]:
        p = get_deriv_price(symbol)
        if p:
            msg += f"💥 {name}: {p:.2f}\n"
        else:
            msg += f"⚠️ {name}: indisponible\n"

    msg += "\nNe trade que les 🟢. Les 🟡 = PATIENCE."
    return msg

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bonjour Yan ! Bot Deriv en ligne ✅\nJe t'envoie tous les marchés toutes les 5 min.\nEnvoie /signal pour voir maintenant.")

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(analyse_all())

async def auto_signal(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=CHAT_ID, text=analyse_all())

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("signal", signal))
    application.job_queue.run_repeating(auto_signal, interval=300, first=10)
    application.run_polling()
