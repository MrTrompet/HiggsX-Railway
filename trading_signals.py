# trading_signals.py

import time
import logging
import threading
import sys
from config import SYMBOL, TIMEFRAME, TELEGRAM_CHAT_ID, TELEGRAM_SENALES_THREAD_ID
from market import fetch_data, get_btc_indicators
from indicators import calculate_indicators
from telegram_handler import send_telegram_message

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def flush_logs():
    for h in logging.getLogger().handlers:
        h.flush()
    sys.stdout.flush()

# Estado para no repetir señales
last_signal_direction = None
last_confirmed_signal = None
last_reversion_signal = None
last_volatility_signal = False

# Estado BTC
last_btc_price = None
last_btc_dominance = None

def send_signal_message(signal_type, details, indicators):
    global last_signal_direction, last_confirmed_signal, last_reversion_signal, last_volatility_signal

    thread_id = TELEGRAM_SENALES_THREAD_ID

    # Cruce
    if signal_type=="cruce" and details.get("signal") and details["signal"]!=last_signal_direction:
        msg = (
            f"🦉 Cruce detectado {'long📈' if details['signal']=='long' else 'short📉'}."
        )
        send_telegram_message(msg, chat_id=TELEGRAM_CHAT_ID, message_thread_id=thread_id)
        flush_logs()

        def chart():
            try:
                from PrintGraphic import send_graphic
                send_graphic(None, "1h", "candlestick", message_thread_id=thread_id)
            except Exception as e:
                logging.error("Error gráfico cruce: %s", e)
                flush_logs()
        threading.Thread(target=chart, daemon=True).start()

        last_signal_direction = details["signal"]

    # Confirmado
    if signal_type=="confirmado" and details.get("signal") and details["signal"]!=last_confirmed_signal:
        macd, macd_s = indicators.get("macd"), indicators.get("macd_signal")
        msg = (
            f"🦉 Confirmación {'long' if details['signal']=='long' else 'short'}:\n"
            f"- MACD:{macd:.2f} Signal:{macd_s:.2f}\n"
            f"- RSI:{indicators.get('rsi',0):.2f}  ADX:{indicators.get('adx',0):.2f}"
        )
        send_telegram_message(msg, chat_id=TELEGRAM_CHAT_ID, message_thread_id=thread_id)
        flush_logs()
        last_confirmed_signal = details["signal"]

    # Sobreventa / sobrecompra
    if signal_type=="sobre" and details.get("signal") and details["signal"]!=last_reversion_signal:
        if details["signal"]=="long":
            msg = "🔻 Zona sobreventa. Posible long."
        else:
            msg = "🔺 Zona sobrecompra. Posible short."
        send_telegram_message(msg, chat_id=TELEGRAM_CHAT_ID, message_thread_id=thread_id)
        flush_logs()
        last_reversion_signal = details["signal"]

    # Volatilidad
    if signal_type=="volatilidad" and not last_volatility_signal:
        msg = "📉 Apretón Bollinger: volatilidad baja, pronto gran movimiento."
        send_telegram_message(msg, chat_id=TELEGRAM_CHAT_ID, message_thread_id=thread_id)
        flush_logs()
        last_volatility_signal = True

def evaluate_signals(indicators):
    s = {}
    macd, macd_s = indicators.get("macd"), indicators.get("macd_signal")
    s["cruce"] = {"signal": "long" if macd and macd>macd_s else "short"} if macd is not None else {"signal": None}

    rsi, adx = indicators.get("rsi"), indicators.get("adx")
    sma10, sma25, sma50 = indicators.get("sma_10"), indicators.get("sma_25"), indicators.get("sma_50")
    if None not in (macd, macd_s, rsi, adx, sma10, sma25):
        if macd>macd_s and rsi>50 and adx>20 and (sma10>sma25 or (sma50 and sma25>sma50)):
            s["confirmado"]={"signal":"long"}
        elif macd<macd_s and rsi<50 and adx>20 and (sma10<sma25 or (sma50 and sma25<sma50)):
            s["confirmado"]={"signal":"short"}
        else:
            s["confirmado"]={"signal":None}
    else:
        s["confirmado"]={"signal":None}

    bb_h, bb_l, price = indicators.get("bb_high"), indicators.get("bb_low"), indicators.get("price")
    if None not in (bb_h, bb_l, price, rsi, adx):
        if price>=bb_h*0.98 and rsi>=68 and adx>30:
            s["sobre"]={"signal":"short"}
        elif price<=bb_l*1.02 and rsi<=40 and adx<30:
            s["sobre"]={"signal":"long"}
        else:
            s["sobre"]={"signal":None}
    else:
        s["sobre"]={"signal":None}

    if None not in (bb_h, bb_l, price):
        bw = (bb_h-bb_l)/price
        s["volatilidad"]={"signal": bw<0.02}
    else:
        s["volatilidad"]={"signal":False}

    return s

def process_signals(indicators):
    sigs = evaluate_signals(indicators)
    for t in ["cruce","confirmado","sobre"]:
        if sigs[t]["signal"]:
            send_signal_message(t, sigs[t], indicators)
    if sigs["volatilidad"]["signal"]:
        send_signal_message("volatilidad", {}, indicators)

def monitor_signals():
    global last_btc_price, last_btc_dominance
    last_btc_price = last_btc_dominance = None
    last_log = time.time()

    while True:
        try:
            data = fetch_data(SYMBOL, TIMEFRAME)
            ind = calculate_indicators(data)
            process_signals(ind)

            btc = get_btc_indicators()
            price, dom = btc.get("price"), btc.get("dominance")
            if last_btc_price is not None and last_btc_dominance is not None:
                if price<last_btc_price and dom>last_btc_dominance:
                    alert = "📡🐋 Whale Hunt: BTC baja pero dominancia sube."
                    send_telegram_message(alert,
                                          chat_id=TELEGRAM_CHAT_ID,
                                          message_thread_id=TELEGRAM_SENALES_THREAD_ID)
                    flush_logs()
            last_btc_price, last_btc_dominance = price, dom

        except Exception as e:
            logging.error("Error monitor: %s", e)
            flush_logs()

        if time.time()-last_log>300:
            logging.info("Monitor activo")
            flush_logs()
            last_log = time.time()

        time.sleep(30)

if __name__=="__main__":
    monitor_signals()
