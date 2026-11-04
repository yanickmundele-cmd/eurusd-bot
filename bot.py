import os
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "9264641964:AAEC_Ffv61DJ9SYviVbXTgiEZnmI3XuQsh4"
CHAT_ID = 7548965711

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot EURUSD en ligne ✅"

def get_price():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        return r['chart']['result'][0]['meta']['regularMarketPrice']
    except:
        return None

def analyse():
    price = get_price()
    if price is None:
        return "⚠️ Impossible de récupérer le prix EURUSD pour l'instant."

    if price <= 1.12150:
        return f"🟢 SIGNAL EURUSD M5 - BUY\n\nPrix actuel: {price:.5f}\nEntrée: {price:.5f} (dans ta BUY ZONE 1.12150)\nSL: 1.11850\nTP1: 1.12600\nTP2: 1.12900\n\nRaison: Prix dans ta zone Bollinger milieu, on achète."
    elif price <= 1.12350:
        return f"🟡 EURUSD M5 - PATIENCE\n\nPrix actuel: {price:.5f}\nOn attend 1.12150 pour acheter.\nNe pas acheter maintenant, encore {price-1.12150:.5f} au-dessus de la zone."
    else:
        return f"🔴 EURUSD M5 - PAS D'ENTREE\n\nPrix actuel: {price:.5f}\nTrop haut au-dessus de 1.12150.\nOn attend la descente."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bonjour ! Bot EURUSD en ligne ✅\nJe t'envoie un signal toutes les 5 min.\nEnvoie /signal pour un signal maintenant.")

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(analyse())

async def auto_signal(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=CHAT_ID, text=analyse())

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
