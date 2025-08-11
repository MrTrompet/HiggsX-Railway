# scheduler.py

import datetime
import pytz
import time
import threading
import logging
import requests

from config import SYMBOL, TIMEFRAME, TELEGRAM_CHAT_ID
from telegram_handler import send_telegram_message, send_telegram_photo
from market import fetch_data
from indicators import calculate_indicators
from news import test_get_headlines
from memoria import store_message

# Importar on-chain para marketcap y volumen
from onchain import fetch_onchain_stats

# Importar la función para enviar gráfico 6h
from PrintGraphic import send_6h_report_chart

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def flush_logs():
    for handler in logging.getLogger().handlers:
        handler.flush()

last_market_open_day = None
last_morning_day = None
last_evening_day = None
last_weekend_day = None

last_6h_report = None
last_daily_report = None
last_top3_report = None
last_fng_day = None  # para el Fear & Greed Index

def send_fng_image():
    """
    Envía la imagen actual del Fear & Greed Index al chat general.
    Agrega un 'cache‐buster' para evitar versiones muy antiguas en caché.
    """
    ts = int(time.time())
    fng_url = f"https://alternative.me/crypto/fear-and-greed-index.png?ts={ts}"
    caption = f"📊 Fear & Greed Index (actualizado al {datetime.datetime.now(pytz.timezone('America/Caracas')).strftime('%d-%m-%Y %H:%M')})"
    # Pasamos None como message_thread_id para que el caption se reconozca correctamente
    send_telegram_photo(fng_url, TELEGRAM_CHAT_ID, None, caption=caption)
    logging.info("Imagen Fear & Greed Index enviada.")
    flush_logs()
    store_message("Scheduler", "Envío de Fear & Greed Index (19:40 PM)")

def send_market_open_message():
    mensaje = (
        "Buenos días Agentes!☀️ Activación completada, iniciando el monitoreo y análisis... "
        "Estén atentos al informe (Mercado de Londres entrando en minutos)."
    )
    send_telegram_message(mensaje, chat_id=TELEGRAM_CHAT_ID)
    logging.info("Mensaje de activación enviado.")
    flush_logs()
    time.sleep(5)
    send_analysis_message()
    time.sleep(5)
    send_news_message()
    store_message("Scheduler", "Envío de mensaje de activación (04:00 AM)")

def send_analysis_message():
    try:
        data = fetch_data(SYMBOL, TIMEFRAME)
        indicadores = calculate_indicators(data)
        dominance_text = (
            f"{indicadores.get('btc_dominance', 0):.2f}%"
            if indicadores.get('btc_dominance') is not None else "N/D"
        )
        mensaje = (
            f"📟Análisis Completado - Informe 1º:\n"
            f"Precio BTC: ${indicadores.get('price', 0):.2f}\n"
            f"RSI: {indicadores.get('rsi', 0):.2f}\n"
            f"MACD: {indicadores.get('macd', 0):.2f} (Señal: {indicadores.get('macd_signal', 0):.2f})\n"
            f"ADX: {indicadores.get('adx', 0):.2f}\n"
            f"SMA: {indicadores.get('sma_10', 0):.2f} | {indicadores.get('sma_25', 0):.2f} | {indicadores.get('sma_50', 0):.2f}\n"
            f"Volumen: {indicadores.get('volume_level', 'N/A')} (CMF: {indicadores.get('cmf', 0):.2f})\n\n"
            f"BTC Dominancia: {dominance_text}"
        )
        send_telegram_message(mensaje, chat_id=TELEGRAM_CHAT_ID)
        logging.info("Mensaje de análisis enviado.")
        flush_logs()
    except Exception as e:
        logging.error("Error en send_analysis_message: %s", e)
        flush_logs()

def send_news_message():
    try:
        titulares = test_get_headlines(limit=4)
        mensaje = f"🗞Titulares destacados del momento:\n{titulares}"
        send_telegram_message(mensaje, chat_id=TELEGRAM_CHAT_ID)
        logging.info("Mensaje de noticias enviado.")
        flush_logs()
    except Exception as e:
        logging.error("Error en send_news_message: %s", e)
        flush_logs()

def send_morning_message():
    mensaje = (
        "Hola agentes, ¿qué tal la mañana?🥪☕️ La activación fue completada. "
        "Iniciando monitoreo y análisis del mercado (Wall Street entra en breve)... "
        "Atento al informe de esta hora."
    )
    send_telegram_message(mensaje, chat_id=TELEGRAM_CHAT_ID)
    logging.info("Mensaje de mañana enviado.")
    flush_logs()
    time.sleep(5)
    send_analysis_message()
    time.sleep(5)
    send_news_message()
    store_message("Scheduler", "Envío de mensaje de mañana (09:00 AM)")

def send_evening_message():
    mensaje = (
        "Buenas noches agentes!🌙 Día largo, pero seguimos analizando en secreto. "
        "Activación completada. Ahora inicia el monitoreo y análisis del mercado para la apertura en Asia... "
        "Estate atento al informe."
    )
    send_telegram_message(mensaje, chat_id=TELEGRAM_CHAT_ID)
    logging.info("Mensaje de noche enviado.")
    flush_logs()
    time.sleep(5)
    send_analysis_message()
    time.sleep(5)
    send_news_message()
    store_message("Scheduler", "Envío de mensaje de noche (20:00 PM)")

def send_weekend_message():
    try:
        titulares = test_get_headlines(limit=5)
        mensaje = (
            f"Buenos días agentes!☕️ Feliz fin de semana. Aquí te comparto las noticias más importantes:\n{titulares}"
        )
        send_telegram_message(mensaje, chat_id=TELEGRAM_CHAT_ID)
        logging.info("Mensaje de fin de semana enviado.")
        flush_logs()
        store_message("Scheduler", "Envío de mensaje de fin de semana (09:00 AM)")
    except Exception as e:
        logging.error("Error en send_weekend_message: %s", e)
        flush_logs()

def send_6h_report():
    """
    Se invoca al cierre de cada vela de 6 horas (00:00, 06:00, 12:00, 18:00).
    Envía únicamente un gráfico combinado: Candle 6h + RSI + MACD, con el texto
    incorporado en la propia imagen/foto.
    """
    global last_6h_report
    ahora = datetime.datetime.now(pytz.timezone("America/Caracas"))
    dia_hora = (ahora.year, ahora.month, ahora.day, ahora.hour)

    # Evitar duplicados: solo enviar una vez por cada múltiplo de 6h
    if last_6h_report == dia_hora:
        return

    try:
        # 1) Obtener datos de velas 6h
        df_6h = fetch_data(SYMBOL, "6h")
        indicadores_6h = calculate_indicators(df_6h)

        # Precio de cierre de la última vela 6h
        precio_actual = indicadores_6h.get("price", 0.0)
        # Calcular % de cambio: último cierre vs penúltimo
        if "close" in df_6h.columns and len(df_6h["close"]) >= 2:
            cierre_ultimo = df_6h["close"].iloc[-1]
            cierre_anterior = df_6h["close"].iloc[-2]
            pct = ((cierre_ultimo - cierre_anterior) / cierre_anterior) * 100 if cierre_anterior != 0 else 0.0
        else:
            pct = 0.0

        # Dominancia de BTC al cierre 6h
        dominancia = indicadores_6h.get("btc_dominance", 0.0)

        # Formatear el texto que irá como caption del gráfico
        texto_caption = (
            "🦉Buenas agentes, informe del cierre en 6h:\n\n"
            "📋 👑 #BTC\n"
            f"Precio: ${precio_actual:.2f} {pct:+.2f}%\n"
            f"Dominancia: {dominancia:.2f}%"
        )

        # 2) Enviar únicamente el gráfico
        send_6h_report_chart(texto_caption)

        # Registrar en memoria
        store_message(
            "Scheduler",
            f"Informe 6h enviado: precio {precio_actual:.2f}, pct {pct:+.2f}, dom {dominancia:.2f}%"
        )

        # Marcar que ya enviamos este bloque de 6h
        last_6h_report = dia_hora

        logging.info("Informe 6h enviado correctamente (solo gráfico).")
        flush_logs()

    except Exception as e:
        logging.error("Error en send_6h_report: %s", e)
        flush_logs()

def send_daily_1d_report():
    """
    Envía un informe diario al cierre de la vela 1D:
      🦉Buenas Agentes, como van? Informe del cierre en 1D:  📋 👑 #BTC
      Precio: $XXXXX +X.XX %
      Dominancia: XX.XX %
      MarketCap: $XXX
      Volumen Últimas 24 horas: $XXX

    Luego adjunta un gráfico combinado 1D + Dominancia (si existe send_daily_report_chart).
    """
    try:
        ahora = datetime.datetime.now(pytz.timezone("America/Caracas"))
        fecha_str = ahora.strftime("%Y-%m-%d")

        # 1) Obtener datos de velas 1D
        df_1d = fetch_data(SYMBOL, "1d")
        indicadores_1d = calculate_indicators(df_1d)

        # Precio de cierre de la última vela 1D
        precio_actual = indicadores_1d.get("price", 0.0)
        # Porcentaje de cambio: cierre último vs penúltimo
        if "close" in df_1d.columns and len(df_1d["close"]) >= 2:
            cierre_ultimo = df_1d["close"].iloc[-1]
            cierre_anterior = df_1d["close"].iloc[-2]
            pct = ((cierre_ultimo - cierre_anterior) / cierre_anterior) * 100 if cierre_anterior != 0 else 0.0
        else:
            pct = 0.0

        # Dominancia de BTC (último dato)
        dominancia = indicadores_1d.get("btc_dominance", 0.0)

        # Datos on-chain: marketcap y volumen 24h
        onchain = fetch_onchain_stats()
        mc = onchain.get("marketcap_usd")
        vol24 = onchain.get("volume_24h_usd")

        mc_str = f"${mc:,.0f}" if isinstance(mc, (int, float)) else "N/D"
        vol24_str = f"${vol24:,.0f}" if isinstance(vol24, (int, float)) else "N/D"

        # Construir el mensaje de texto
        mensaje = (
            f"🦉Buenas Agentes, como van? Informe del cierre en 1D ({fecha_str}):\n\n"
            f"📋 👑 #BTC\n"
            f"Precio: ${precio_actual:.2f} {pct:+.2f} %\n"
            f"Dominancia: {dominancia:.2f}%\n"
            f"MarketCap: {mc_str}\n"
            f"Volumen Últimas 24 horas: {vol24_str}"
        )
        send_telegram_message(mensaje, chat_id=TELEGRAM_CHAT_ID)
        store_message("Scheduler", f"Informe 1D enviado: precio {precio_actual:.2f}, pct {pct:+.2f}, dom {dominancia:.2f}%")

        # 2) Enviar el gráfico combinado 1D + Dominancia (si existe)
        try:
            from PrintGraphic import send_all_dominance_chart
            caption = f"📈 Gráfico 1D + Dominancia de BTC ({fecha_str})"
            send_all_dominance_chart(caption)
        except ImportError:
            logging.warning("send_all_dominance_chart no existe en PrintGraphic.py; omito gráfico 1D.")

        logging.info("Informe 1D enviado correctamente.")
        flush_logs()

    except Exception as e:
        logging.error("Error en send_daily_1d_report: %s", e)
        flush_logs()

def fetch_top3_gainers_losers() -> tuple[list, list]:
    """
    Usa CoinGecko para obtener el top 100 de monedas según MarketCap y
    devuelve dos listas de tuplas:
      - top3_gainers: [(symbol, change_pct_24h), ...]
      - top3_losers:  [(symbol, change_pct_24h), ...]
    """
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100,
            "page": 1,
            "price_change_percentage": "24h"
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()  # lista de dicts

        # Filtrar los que tengan price_change_percentage_24h
        valid = [coin for coin in data if coin.get("price_change_percentage_24h") is not None]

        # Ordenar por cambio porcentual
        sorted_coins = sorted(valid, key=lambda c: c["price_change_percentage_24h"])

        # Los 3 primeros de sorted_coins negativamente → top3 perdedoras
        top3_losers = sorted_coins[:3]
        # Los 3 últimos de sorted_coins → top3 ganadoras
        top3_gainers = sorted_coins[-3:]

        # Formatear como lista de (símbolo, porcentaje)
        gainers = [
            (coin["symbol"].upper() + "USDT", coin["price_change_percentage_24h"])
            for coin in reversed(top3_gainers)
        ]
        losers = [
            (coin["symbol"].upper() + "USDT", coin["price_change_percentage_24h"])
            for coin in top3_losers
        ]
        return gainers, losers

    except Exception as e:
        logging.error("Error al obtener top3 de CoinGecko: %s", e)
        return [], []

def send_daily_top3():
    """
    Envía el top 3 de ganadoras y perdedoras del día usando CoinGecko.
    """
    try:
        gainers, losers = fetch_top3_gainers_losers()
        if not gainers or not losers:
            mensaje = "No se pudo obtener el top 3 de ganadoras/perdedoras en este momento."
            send_telegram_message(mensaje, chat_id=TELEGRAM_CHAT_ID)
            return

        texto = "Agentes, por acá les dejo el top de hoy:\n\n"
        texto += "🟢 TOP 3 GANADORAS 🟢\n"
        for i, (sym, pct) in enumerate(gainers, start=1):
            texto += f" {i}⃣ #{sym} {pct:+.2f} %\n"
        texto += "\n🔴 TOP 3 PERDEDORAS 🔴\n"
        for i, (sym, pct) in enumerate(reversed(losers), start=1):
            texto += f" {i}⃣ #{sym} {pct:+.2f} %\n"

        send_telegram_message(texto, chat_id=TELEGRAM_CHAT_ID)
        store_message("Scheduler", "Envío de top 3 ganadoras/perdedoras diario")
        logging.info("Top 3 diario enviado correctamente.")
        flush_logs()

    except Exception as e:
        logging.error("Error en send_daily_top3: %s", e)
        flush_logs()

def scheduler_loop():
    global last_market_open_day, last_morning_day, last_evening_day, last_weekend_day
    global last_daily_report, last_top3_report, last_fng_day

    venezuela_tz = pytz.timezone("America/Caracas")
    while True:
        now = datetime.datetime.now(venezuela_tz)
        current_hour = now.hour
        current_minute = now.minute
        current_day = now.strftime("%A")
        logging.info("Scheduler chequeo: %s %02d:%02d", current_day, current_hour, current_minute)
        flush_logs()

        # 1) Cierres de velas 6h: si es hora múltiplo de 6 y minuto <2
        if current_hour % 6 == 0 and current_minute < 2:
            send_6h_report()
            time.sleep(120)

        # 2) Informe diario 1D al cierre de día (00:00 local)
        if current_hour == 0 and current_minute < 1:
            if last_daily_report != now.day:
                send_daily_1d_report()
                last_daily_report = now.day
                # Esperar un poco antes de enviar el top3
                time.sleep(5)
                send_daily_top3()
                last_top3_report = now.day
                time.sleep(120)

        # 3) Días de semana: mensajes programados
        if current_day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            if current_hour == 4 and current_minute < 2 and last_market_open_day != now.day:
                send_market_open_message()
                last_market_open_day = now.day
                time.sleep(120)
            elif current_hour == 9 and current_minute < 2 and last_morning_day != now.day:
                send_morning_message()
                last_morning_day = now.day
                time.sleep(120)
            elif current_hour == 20 and current_minute < 2 and last_evening_day != now.day:
                send_evening_message()
                last_evening_day = now.day
                time.sleep(120)
        else:
            # 4) Fines de semana
            if current_hour == 9 and current_minute < 2 and last_weekend_day != now.day:
                send_weekend_message()
                last_weekend_day = now.day
                time.sleep(120)

        # —— FEAR & GREED INDEX (TODOS LOS DÍAS A LAS 19:40) ——
        if current_hour == 19 and current_minute == 40 and last_fng_day != now.day:
            try:
                send_fng_image()
                last_fng_day = now.day
            except Exception as e:
                logging.error("Error enviando Fear & Greed Index: %s", e)
                flush_logs()
            time.sleep(120)

        time.sleep(30)

def start_scheduler():
    threading.Thread(target=scheduler_loop, daemon=True).start()

if __name__ == "__main__":
    start_scheduler()
    while True:
        time.sleep(1)
