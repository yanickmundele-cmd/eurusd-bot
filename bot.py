import os
import threading
import requests
import json
import websocket
from datetime import datetime, timedelta
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

def get_all_deriv_prices(symbols):
    # UNE SEULE connexion pour tous les marchés Deriv, sinon Render bloque
    results = {}
    try:
        ws = websocket.create_connection("wss://ws.derivws.com/websockets/v3?app_id=1089", timeout=20)
        for symbol in symbols:
            try:
                ws.send(json.dumps({"ticks_history": symbol, "end": "latest", "count": 1, "style": "ticks", "req_id": symbol}))
                found = False
                for _ in range(5):
                    data = json.loads(ws.recv())
                    # On vérifie que c'est bien le bon symbole
                    if data.get("req_id") == symbol or "history" in data:
                        if "history" in data and "prices" in data["history"] and len(data["history"]["prices"]) > 0:
                            results[symbol] = float(data["history"]["prices"][-1])
                            found = True
                            break
                    if "error" in data:
                        break
                if not found:
                    results[symbol] = None
            except:
                results[symbol] = None
        ws.close()
    except Exception as e:
        print(f"Erreur Deriv connexion: {e}")
        for s in symbols:
            results[s] = None
    return results

def analyse_all():
    now = datetime.now()
    deadline = now + timedelta(minutes=1)
    next_signal = now + timedelta(minutes=5)
    heure_msg = f"⏰ Signal de {now.strftime('%H:%M')}\n⚠️ ENTRE AVANT {deadline.strftime('%H:%M')}, sinon attends le prochain à {next_signal.strftime('%H:%M')}\n\n"
    msg = "📊 SIGNAUX DERIV + FOREX - Toutes les 5 min\n" + heure_msg

    eurusd = get_yahoo_price("EURUSD")
    if eurusd:
        if eurusd <= 1.12150:
            msg += f"🟢 EURUSD: {eurusd:.5f} -> BUY | Entrée {eurusd:.5f} | SL 1.11850 | TP 1.12600 | ENTRE MAINTENANT avant {deadline.strftime('%H:%M')}\n"
        elif eurusd <= 1.12350:
            msg += f"🟡 EURUSD: {eurusd:.5f} -> PATIENCE, on attend 1.12150 - N'ENTRE PAS\n"
        else:
            msg += f"🔴 EURUSD: {eurusd:.5f} -> TROP HAUT, pas d'entrée - N'ENTRE PAS\n"
    else:
        msg += "⚠️ EURUSD: prix indisponible\n"

    gbpusd = get_yahoo_price("GBPUSD")
    if gbpusd:
        if gbpusd <= 1.3410:
            msg += f"🟢 GBPUSD: {gbpusd:.5f} -> BUY ZONE 1.3410 | ENTRE MAINTENANT avant {deadline.strftime('%H:%M')}\n"
        else:
            msg += f"🟡 GBPUSD: {gbpusd:.5f} -> PATIENCE, attend 1.3410 - N'ENTRE PAS\n"

    gold = get_yahoo_price("GC")
    if gold:
        if gold >= 4074:
            msg += f"🟢 GOLD: {gold:.1f} -> BUY, cassure 4074 | ENTRE MAINTENANT avant {deadline.strftime('%H:%M')}\n"
        elif gold <= 4000:
            msg += f"🟢 GOLD: {gold:.1f} -> BUY ZONE 4000 | ENTRE MAINTENANT avant {deadline.strftime('%H:%M')}\n"
        else:
            msg += f"🟡 GOLD: {gold:.1f} -> PATIENCE entre 4000 et 4074 - N'ENTRE PAS\n"

    btc = get_yahoo_price("BTC-USD")
    if btc:
        if btc >= 80300:
            msg += f"🟢 BTC: {btc:.0f} -> BUY cassure 80300 | ENTRE MAINTENANT avant {deadline.strftime('%H:%M')}\n"
        else:
            msg += f"🟡 BTC: {btc:.0f} -> PATIENCE, attend 80300 - N'ENTRE PAS\n"

    msg += "\n--- INDICES DERIV ---\n"

    deriv_symbols = ["R_75", "R_100", "R_50", "R_25", "BOOM_1000", "CRASH_1000", "BOOM_500", "CRASH_500"]
    prices = get_all_deriv_prices(deriv_symbols)

    for name, symbol in [("V75", "R_75"), ("V100", "R_100"), ("V50", "R_50"), ("V25", "R_25")]:
        p = prices.get(symbol)
        if p:
            msg += f"📈 {name}: {p:.2f}\n"
        else:
            msg += f"⚠️ {name}: indisponible\n"

    for name, symbol in [("BOOM 1000", "BOOM_1000"), ("CRASH 1000", "CRASH_1000"), ("BOOM 500", "BOOM_500"), ("CRASH 500", "CRASH_500")]:
        p = prices.get(symbol)
        if p:
            msg += f"💥 {name}: {p:.2f}\n"
        else:
            msg += f"⚠️ {name}: indisponible\n"

    msg += f"\n📌 RÈGLE: 🟢 = Entre avant {deadline.strftime('%H:%M')}. Après, c'est trop tard, attends {next_signal.strftime('%H:%M')}. 🟡🔴 = N'ENTRE PAS."
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
