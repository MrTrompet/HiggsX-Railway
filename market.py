# market.py

import ccxt
import time
import pandas as pd
import requests
import threading
from config import (
    SYMBOL,
    TIMEFRAME,
    MAX_RETRIES,
    CACHING_INTERVAL_DOMINANCE,
    COINMARKETCAP_API_KEY,
)

exchange = ccxt.coinbase()

# Variables globales para la dominancia de BTC y su timestamp
BTC_DOMINANCE = None
BTC_DOMINANCE_TIMESTAMP = 0

def fetch_data(symbol=SYMBOL, timeframe=TIMEFRAME, limit=100):
    """
    Obtiene datos OHLCV con manejo de errores y retrasos mínimos.
    """
    retries = 0
    while retries < MAX_RETRIES:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"[Error fetch_data] {e}. Reintentando...")
            time.sleep(1)
            retries += 1
    raise Exception("No se pudieron obtener datos tras varios intentos.")

def fetch_btc_dominance():
    """
    Obtiene la dominancia de BTC utilizando la API de CoinMarketCap.
    Se cachea durante CACHING_INTERVAL_DOMINANCE segundos.
    """
    global BTC_DOMINANCE, BTC_DOMINANCE_TIMESTAMP
    current_time = time.time()

    # Si la dominancia ya está cacheada y no expiró, retornarla
    if BTC_DOMINANCE is not None and (current_time - BTC_DOMINANCE_TIMESTAMP) < CACHING_INTERVAL_DOMINANCE:
        return BTC_DOMINANCE
    

    url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json().get("data", {})
        dominance = data.get("btc_dominance")

        if dominance is None:
            print("Dominancia de BTC no encontrada en la respuesta de CoinMarketCap.")
        else:
            BTC_DOMINANCE = dominance
            BTC_DOMINANCE_TIMESTAMP = current_time

        return dominance

    except requests.exceptions.HTTPError as http_err:
        status = response.status_code if 'response' in locals() else None
        if status == 401:
            print("[Error fetch_btc_dominance] Unauthorized: verifica tu COINMARKETCAP_API_KEY.")
        else:
            print(f"[Error fetch_btc_dominance] HTTP error al obtener dominancia de BTC: {http_err}")
        return None
    except Exception as e:
        print(f"[Error fetch_btc_dominance] Excepción al obtener dominancia de BTC: {e}")
        return None

def update_btc_dominance_loop():
    """
    Hilo que actualiza BTC_DOMINANCE cada CACHING_INTERVAL_DOMINANCE segundos.
    """
    while True:
        dominance = fetch_btc_dominance()
        if dominance is not None:
            ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            print(f"[{ts}] BTC Dominancia actualizada: {dominance:.2f}%")
        else:
            ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            print(f"[{ts}] No se pudo actualizar BTC Dominancia.")
        time.sleep(CACHING_INTERVAL_DOMINANCE)

def start_dominance_monitor():
    """
    Inicia un hilo que actualiza la dominancia de BTC.
    Realiza una actualización inicial inmediata.
    """
    initial = fetch_btc_dominance()
    print(f"Valor inicial BTC Dominancia: {initial}")
    thread = threading.Thread(target=update_btc_dominance_loop, daemon=True)
    thread.start()

def get_btc_indicators():
    """
    Obtiene indicadores básicos para BTC: precio y dominancia.
    Usa el par BTC/USDT en timeframe 5m para precio y la función fetch_btc_dominance() para dominancia.
    """
    data = fetch_data("BTC/USDT", "5m", limit=1)
    price = data['close'].iloc[-1] if data is not None and not data.empty else None
    dominance = fetch_btc_dominance()
    return {'price': price, 'dominance': dominance}
