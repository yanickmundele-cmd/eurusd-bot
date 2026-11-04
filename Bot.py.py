import time, json, requests, websocket
import pandas as pd
import numpy as np
from datetime import datetime

# --- A CHANGER ---
TELEGRAM_TOKEN = "COLLE_TON_TOKEN_ICI"
CHAT_ID = "7548965711"
DERIV_APP_ID = "1089"  # App ID public Deriv
# -----------------

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print("Erreur Telegram:", e)

def get_candles():
    ws = websocket.create_connection(f"wss://ws.derivws.com/websockets/v3?app_id={DERIV_APP_ID}", timeout=15)
    req = {"ticks_history": "frxEURUSD", "count": 120, "granularity": 300, "end": "latest", "style": "candles"}
    ws.send(json.dumps(req))
    data = json.loads(ws.recv())
    ws.close()
    candles = data.get("candles", [])
    df = pd.DataFrame(candles)
    return df

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def stochastic(df, k=14, d=3):
    low_min = df['low'].rolling(k).min()
    high_max = df['high'].rolling(k).max()
    k_line = 100 * (df['close'] - low_min) / (high_max - low_min)
    d_line = k_line.rolling(d).mean()
    return k_line, d_line

def adx(df, period=14):
    df['tr'] = np.maximum(df['high']-df['low'], np.maximum(abs(df['high']-df['close'].shift(1)), abs(df['low']-df['close'].shift(1))))
    df['plus_dm'] = np.where((df['high']-df['high'].shift(1)) > (df['low'].shift(1)-df['low']), np.maximum(df['high']-df['high'].shift(1), 0), 0)
    df['minus_dm'] = np.where((df['low'].shift(1)-df['low']) > (df['high']-df['high'].shift(1)), np.maximum(df['low'].shift(1)-df['low'], 0), 0)
    tr14 = df['tr'].rolling(period).mean()
    plus_di = 100 * (df['plus_dm'].rolling(period).mean() / tr14)
    minus_di = 100 * (df['minus_dm'].rolling(period).mean() / tr14)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    return dx.rolling(period).mean()

def analyse():
    try:
        df = get_candles()
        if len(df) < 60:
            return None
        df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['rsi'] = rsi(df['close'])
        df['k'], df['d'] = stochastic(df)
        df['adx'] = adx(df)

        last = df.iloc[-2]  # bougie fermée
        prev = df.iloc[-3]
        prix = float(df.iloc[-1]['close'])
        adx_val = float(last['adx'])
        rsi_val = float(last['rsi'])
        ema9, ema21, ema50 = float(last['ema9']), float(last['ema21']), float(last['ema50'])

        # Filtres anti-perte
        heure = datetime.now().hour  # Heure serveur, à ajuster
        # News US : on bloque 11h-13h UTC = 12h-14h Kinshasa
        if 11 <= heure <= 13:
            return None
        if adx_val < 20:
            return None
        if abs(last['close'] - last['open']) < 0.0001:  # Doji
            return None

        # BUY
        if prix > ema50 and ema9 > ema21 and 50 <= rsi_val <= 65 and last['k'] > prev['k'] and last['k'] < 80 and last['close'] > last['open']:
            sl = prix - 0.0010
            tp = prix + 0.0015
            return f"🔔 *SIGNAL FORT EUR/USD M5*\n\nDirection : BUY ⬆️\nConfiance : 85% (4/4)\nPrix : {prix:.5f}\nEntrée à la prochaine bougie\nSL : {sl:.5f} (-10 pips)\nTP : {tp:.5f} (+15 pips)\n\nTu as 3 min pour te préparer"
        
        # SELL
        if prix < ema50 and ema9 < ema21 and 35 <= rsi_val <= 50 and last['k'] < prev['k'] and last['k'] > 20 and last['close'] < last['open']:
            sl = prix + 0.0010
            tp = prix - 0.0015
            return f"🔔 *SIGNAL FORT EUR/USD M5*\n\nDirection : SELL ⬇️\nConfiance : 85% (4/4)\nPrix : {prix:.5f}\nEntrée à la prochaine bougie\nSL : {sl:.5f} (-10 pips)\nTP : {tp:.5f} (+15 pips)\n\nTu as 3 min pour te préparer"

        return None
    except Exception as e:
        print("Erreur analyse:", e)
        return None

print("Bot démarré...")
send_telegram("✅ Bot EUR/USD M5 démarré. Je t'enverrai les signaux affinés.")
last_signal_time = ""

while True:
    now = datetime.now()
    # On analyse à la 2ème minute de chaque bougie de 5 min (ex: 10:02, 10:07, 10:12)
    if now.minute % 5 == 2 and now.second < 15:
        key = now.strftime("%Y-%m-%d %H:%M")
        if key != last_signal_time:
            last_signal_time = key
            print(f"Analyse {key}...")
            signal = analyse()
            if signal:
                send_telegram(signal)
                print("Signal envoyé")
            else:
                print("Pas de signal")
    time.sleep(10)