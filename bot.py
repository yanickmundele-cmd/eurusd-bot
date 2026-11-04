import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests

TOKEN = "9271726236:AAE4Xk5O_101xZXVy64LtE8S5dsNsP5FjeQ"

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot EURUSD en ligne !"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bonjour ! Bot EURUSD en ligne ✅\nEnvoie /signal pour un signal.")

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/EUR", timeout=10).json()
        prix = r['rates']['USD']
        await update.message.reply_text(f"EUR/USD actuel : {prix}\nSignal : Surveille le graphique H1")
    except Exception as e:
        await update.message.reply_text(f"Erreur : {e}")

def run_bot():
    app_bot = ApplicationBuilder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("signal", signal))
    app_bot.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
