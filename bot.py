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
DERIV_TOKEN = "pat_5f035818cade5234e92f8ef4e019a4d1badb367a8261a7461589e24004ad0590"

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Auto-Trade Deriv + V75 en ligne ✅"

positions_ouvertes = {}

def get_yahoo_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}=X"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        return r['chart']['result'][0]['meta']['regularMarketPrice']
    except:
        return None

def get_deriv_history(symbol, count=20):
    # Récupère les 20 derniers ticks pour voir si ça monte ou ça casse
    try:
        ws = websocket.create_connection("wss://ws.derivws.com/websockets/v3?app_id=1089", timeout=20)
        ws.send(json.dumps({"ticks_history": symbol, "end": "latest", "count": count, "style": "ticks", "req_id": symbol}))
        for _ in range(5):
            data = json.loads(ws.recv())
            if "history" in data and "prices" in data["history"]:
                ws.close()
                return [float(p) for p in data["history"]["prices"]]
        ws.close()
        return None
    except:
        return None

def get_all_deriv_prices(symbols):
    results = {}
    for s in symbols:
        hist = get_deriv_history(s, 20)
        if hist and len(hist) > 0:
            results[s] = hist
        else:
            results[s] = None
    return results

def ouvrir_position_deriv(symbol_deriv, direction):
    # Stake 1 USD, TP 1 USD, SL 0.50 USD
    try:
        ws = websocket.create_connection("wss://ws.derivws.com/websockets/v3?app_id=1089", timeout=20)
        ws.send(json.dumps({"authorize": DERIV_TOKEN}))
        auth = json.loads(ws.recv())
        if "error" in auth:
            ws.close()
            return f"❌ Erreur auth Deriv: {auth['error'].get('message')}"
        ws.send(json.dumps({
            "buy": 1,
            "price": 1,
            "parameters": {
                "amount": 1,
                "basis": "stake",
                "contract_type": direction,
                "currency": "USD",
                "multiplier": 100,
                "symbol": symbol_deriv,
                "take_profit": 1,
                "stop_loss": 0.5
            }
        }))
        res = json.loads(ws.recv())
        ws.close()
        if "error" in res:
            return f"❌ Echec {symbol_deriv} {direction}: {res['error'].get('message')}"
        if "buy" in res:
            return f"✅ POSITION OUVERTE {symbol_deriv} {direction} | Stake 1$ | TP +1$ | SL -0.50$ | ID: {res['buy']['contract_id']}"
        return f"⚠️ Réponse inconnue {symbol_deriv}: {res}"
    except Exception as e:
        return f"❌ Exception {symbol_deriv}: {e}"

def analyse_et_trade():
    now = datetime.now()
    deadline = now + timedelta(minutes=1)
    next_signal = now + timedelta(minutes=5)
    msg = f"📊 SIGNAUX + AUTO-TRADE - {now.strftime('%H:%M')}\n⚠️ ENTRE AVANT {deadline.strftime('%H:%M')}, sinon attends {next_signal.strftime('%H:%M')}\n\n"

    eurusd = get_yahoo_price("EURUSD")
    if eurusd:
        if eurusd <= 1.12150:
            msg += f"🟢 EURUSD: {eurusd:.5f} -> BUY\n"
            if positions_ouvertes.get("frxEURUSD") != "ouvert":
                res = ouvrir_position_deriv("frxEURUSD", "MULTUP")
                msg += f"🤖 AUTO: {res}\n"
                if "✅" in res:
                    positions_ouvertes["frxEURUSD"] = "ouvert"
            else:
                msg += "⏳ EURUSD déjà ouvert\n"
        elif eurusd <= 1.12350:
            msg += f"🟡 EURUSD: {eurusd:.5f} -> PATIENCE\n"
        else:
            msg += f"🔴 EURUSD: {eurusd:.5f} -> TROP HAUT\n"

    gbpusd = get_yahoo_price("GBPUSD")
    if gbpusd:
        if gbpusd <= 1.3410:
            msg += f"🟢 GBPUSD: {gbpusd:.5f} -> BUY\n"
            if positions_ouvertes.get("frxGBPUSD") != "ouvert":
                res = ouvrir_position_deriv("frxGBPUSD", "MULTUP")
                msg += f"🤖 AUTO: {res}\n"
                if "✅" in res:
                    positions_ouvertes["frxGBPUSD"] = "ouvert"
            else:
                msg += "⏳ GBPUSD déjà ouvert\n"
        else:
            msg += f"🟡 GBPUSD: {gbpusd:.5f} -> PATIENCE\n"

    gold = get_yahoo_price("GC")
    if gold:
        if gold >= 4074:
            msg += f"🟢 GOLD: {gold:.1f} -> BUY cassure 4074\n"
            if positions_ouvertes.get("frxXAUUSD") != "ouvert":
                res = ouvrir_position_deriv("frxXAUUSD", "MULTUP")
                msg += f"🤖 AUTO: {res}\n"
                if "✅" in res:
                    positions_ouvertes["frxXAUUSD"] = "ouvert"
        elif gold <= 4000:
            msg += f"🟢 GOLD: {gold:.1f} -> BUY ZONE 4000\n"
            if positions_ouvertes.get("frxXAUUSD") != "ouvert":
                res = ouvrir_position_deriv("frxXAUUSD", "MULTUP")
                msg += f"🤖 AUTO: {res}\n"
                if "✅" in res:
                    positions_ouvertes["frxXAUUSD"] = "ouvert"
        else:
            msg += f"🟡 GOLD: {gold:.1f} -> PATIENCE\n"

    btc = get_yahoo_price("BTC-USD")
    if btc:
        if btc >= 80300:
            msg += f"🟢 BTC: {btc:.0f} -> BUY cassure 80300\n"
            if positions_ouvertes.get("cryBTCUSD") != "ouvert":
                res = ouvrir_position_deriv("cryBTCUSD", "MULTUP")
                msg += f"🤖 AUTO: {res}\n"
                if "✅" in res:
                    positions_ouvertes["cryBTCUSD"] = "ouvert"
        else:
            msg += f"🟡 BTC: {btc:.0f} -> PATIENCE\n"

    msg += "\n--- INDICES DERIV AUTO V75 ---\n"
    deriv_symbols = ["R_75", "R_100", "R_50", "R_25"]
    all_hist = get_all_deriv_prices(deriv_symbols)

    for name, symbol in [("V75", "R_75"), ("V100", "R_100"), ("V50", "R_50"), ("V25", "R_25")]:
        hist = all_hist.get(symbol)
        if hist and len(hist) >= 20:
            prix = hist[-1]
            max_prev = max(hist[:-1])
            min_prev = min(hist[:-1])
            # Stratégie V75 : Cassure des 19 derniers ticks
            if prix > max_prev:
                msg += f"🟢 {name}: {prix:.2f} -> BUY CASSURE HAUT\n"
                if positions_ouvertes.get(symbol) != "ouvert":
                    res = ouvrir_position_deriv(symbol, "MULTUP")
                    msg += f"🤖 AUTO V75: {res}\n"
                    if "✅" in res:
                        positions_ouvertes[symbol] = "ouvert"
                else:
                    msg += f"⏳ {name} déjà ouvert\n"
            elif prix < min_prev:
                msg += f"🟢 {name}: {prix:.2f} -> SELL CASSURE BAS\n"
                if positions_ouvertes.get(symbol) != "ouvert":
                    res = ouvrir_position_deriv(symbol, "MULTDOWN")
                    msg += f"🤖 AUTO V75: {res}\n"
                    if "✅" in res:
                        positions_ouvertes[symbol] = "ouvert"
                else:
                    msg += f"⏳ {name} déjà ouvert\n"
            else:
                msg += f"🟡 {name}: {prix:.2f} -> PATIENCE, pas de cassure\n"
        else:
            msg += f"⚠️ {name}: indisponible\n"

    msg += "\n--- BOOM / CRASH - Affichage seulement ---\n"
    boom_hist = get_all_deriv_prices(["BOOM_1000", "CRASH_1000", "BOOM_500", "CRASH_500"])
    for name, symbol in [("BOOM 1000", "BOOM_1000"), ("CRASH 1000", "CRASH_1000"), ("BOOM 500", "BOOM_500"), ("CRASH 500", "CRASH_500")]:
        hist = boom_hist.get(symbol)
        if hist:
            msg += f"💥 {name}: {hist[-1]:.2f}\n"
        else:
            msg += f"⚠️ {name}: indisponible\n"

    msg += f"\n📌 AUTO-TRADE: 1$ par position | TP +1$ = ferme | SL -0.50$ = ferme"
    return msg

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bonjour Yan ! Bot AUTO-TRADE V75 en ligne ✅\n1$ par position | TP +1$ | SL -0.50$\nEnvoie /signal pour voir maintenant.")

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(analyse_et_trade())

async def auto_signal(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=CHAT_ID, text=analyse_et_trade())

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
