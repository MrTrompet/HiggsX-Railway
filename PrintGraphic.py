# printgraphic.py

import matplotlib
import matplotlib.pyplot as plt
# Usamos Agg para evitar GUI en hilos
matplotlib.use('Agg')
import ccxt
import pandas as pd
import numpy as np
import mplfinance as mpf
import io
import requests
import re
import time
from datetime import datetime, timedelta
from matplotlib.lines import Line2D
from dominance_historical import fetch_historical_dominance

from config import (
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_HIGGS_THREAD_ID,
    TELEGRAM_SENALES_THREAD_ID,
    COINMARKETCAP_API_KEY,
)

# Parámetros de gráfico
SYMBOL = 'BTC/USD'
LIMIT = 100
GRAPH_CACHE_INTERVAL = 60  # segundos
GRAPH_CACHE = {}

# Conexión a Coinbase
exchange = ccxt.coinbase()

# Mapeo de intervalos
TIMEFRAME_MAPPING = {
    "1m":  "1m",
    "5m":  "5m",
    "15m": "15m",
    "1h":  "1h",
    "6h":  "6h",
    "1d":  "1d",
}

def extract_timeframe(text: str) -> str:
    pattern = r'\b(\d+m|\d+h|\d+d)\b'
    for m in re.findall(pattern, text.lower()):
        if m in TIMEFRAME_MAPPING:
            return TIMEFRAME_MAPPING[m]
    return "1h"

def get_ohlcv_data(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    """
    Obtiene OHLCV mediante CCXT y genera DataFrame:
    timestamp (índice), Open, High, Low, Close, Volume
    """
    candles = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(candles, columns=['timestamp','open','high','low','close','volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df.rename(columns={'open':'Open','high':'High','low':'Low','close':'Close','volume':'Volume'}, inplace=True)
    return df

def plot_candlestick_chart(df: pd.DataFrame, symbol: str, timeframe: str):
    """
    Genera un gráfico candlestick sencillo con SMA y anotaciones de soporte/resistencia.
    """
    sma10 = df['Close'].rolling(10).mean()
    sma20 = df['Close'].rolling(20).mean()
    sma50 = df['Close'].rolling(50).mean()
    support, resistance = df['Close'].min(), df['Close'].max()
    current = df['Close'].iloc[-1]

    mc = mpf.make_marketcolors(up='#00ff00', down='#ff4500',
                               edge={'up':'#00ff00','down':'#ff4500'},
                               wick={'up':'#00ff00','down':'#ff4500'})
    style = mpf.make_mpf_style(base_mpf_style='nightclouds',
                               marketcolors=mc,
                               facecolor='#0f0f0f',
                               gridcolor='dimgray',
                               gridstyle='--',
                               rc={'font.size':10,
                                   'figure.facecolor':'#0f0f0f',
                                   'axes.facecolor':'#0f0f0f',
                                   'axes.edgecolor':'white',
                                   'axes.labelcolor':'white',
                                   'xtick.color':'white',
                                   'ytick.color':'white'})

    ap = [
        mpf.make_addplot(sma10, color='green', width=1.2),
        mpf.make_addplot(sma20, color='lightskyblue', width=1.2),
        mpf.make_addplot(sma50, color='pink', width=1.2),
        mpf.make_addplot([support]*len(df), color='red', linestyle='--', width=1),
        mpf.make_addplot([resistance]*len(df), color='yellow', linestyle='--', width=1),
        mpf.make_addplot([current]*len(df), color='white', linestyle='-', width=1),
    ]

    title = f"{symbol} - {timeframe} - {datetime.now():%Y-%m-%d %H:%M:%S}"
    fig, axes = mpf.plot(df, type='candle', style=style,
                         title=title, addplot=ap,
                         returnfig=True, figsize=(10,6))

    fig.patch.set_facecolor('black')
    for ax in axes:
        ax.set_facecolor('black')
        ax.yaxis.label.set_color('lime')
        for label in ax.get_xticklabels():
            label.set_color('white')
        for label in ax.get_yticklabels():
            label.set_color('white')
    fig.suptitle(title, color='lime', fontsize=9, ha='center', y=0.95)

    last, prev = df['Close'].iloc[-1], df['Close'].iloc[-2]
    move_text, move_color = ("Bajada","red") if last < prev else ("Subida","green")
    idx = df.index[-1]
    axes[0].annotate(move_text,
                     xy=(idx, last),
                     xytext=(idx, last*0.99),
                     arrowprops=dict(facecolor=move_color, shrink=0.05),
                     color=move_color, fontsize=10)

    legend = [
        Line2D([0],[0], color='green',        lw=1.2, label='SMA10'),
        Line2D([0],[0], color='lightskyblue', lw=1.2, label='SMA20'),
        Line2D([0],[0], color='pink',         lw=1.2, label='SMA50'),
        Line2D([0],[0], color='red',          lw=1,   linestyle='--', label='Soporte'),
        Line2D([0],[0], color='yellow',       lw=1,   linestyle='--', label='Resistencia'),
        Line2D([0],[0], color='white',        lw=1,   label='Precio Actual'),
    ]
    axes[0].legend(handles=legend, loc='upper center',
                   bbox_to_anchor=(0.5,1.05), ncol=3,
                   facecolor='black', edgecolor='black', fontsize=8)

    # Firma
    fig.text(0.90, 0.02, "HiggsX - Ulu Labs", ha='center', va='bottom', color='lime', fontsize=7)
    return fig

def send_chart_to_telegram(fig, caption: str, message_thread_id: int = None):
    """
    Dado un objeto `fig` de matplotlib, lo convierte en PNG y lo envía a Telegram.
    """
    buf = io.BytesIO()
    fig.savefig(buf, dpi=150, format='png', facecolor=fig.get_facecolor())
    buf.seek(0)

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    files = {'photo': buf}
    data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
    if message_thread_id is not None:
        data['message_thread_id'] = message_thread_id

    resp = requests.post(url, data=data, files=files)
    if resp.status_code != 200:
        print("Error al enviar el gráfico:", resp.text)
    else:
        print(f"Gráfico enviado en topic {message_thread_id or 'general'}.")

def send_graphic(_, timeframe_input="1h", __="candlestick", message_thread_id: int=None):
    """
    Función para peticiones de gráficos desde Higgs Handler.
    Reutiliza cache y llama a plot_candlestick_chart.
    """
    timeframe = extract_timeframe(timeframe_input)
    cache_key = f"{SYMBOL}_{timeframe}"
    now = time.time()

    # Reutilizar cache
    if cache_key in GRAPH_CACHE:
        ts, fig = GRAPH_CACHE[cache_key]
        if now - ts < GRAPH_CACHE_INTERVAL:
            send_chart_to_telegram(fig, f"{SYMBOL} en {timeframe}", message_thread_id)
            return

    df = get_ohlcv_data(SYMBOL, timeframe, LIMIT)
    if df.empty:
        print("No hay datos para gráfico.")
        return

    fig = plot_candlestick_chart(df, SYMBOL, timeframe)
    GRAPH_CACHE[cache_key] = (now, fig)
    send_chart_to_telegram(fig, f"{SYMBOL} en {timeframe}", message_thread_id)

#############################
# NUEVO: GRÁFICO COMBINADO 6h
#############################

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calcula el RSI de la Serie `series` (usualmente precio de cierre).
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(series: pd.Series):
    """
    Calcula las tres líneas del MACD: macd_line, signal_line y histogram.
    Parámetros: EMA rápida 12, EMA lenta 26, señal 9.
    """
    ema_fast = series.ewm(span=12, adjust=False).mean()
    ema_slow = series.ewm(span=26, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def plot_6h_report_chart(symbol: str = SYMBOL, limit: int = 100):
    """
    Genera un gráfico con tres paneles:
      - Panel 0: candlestick (velas 6h) + SMA (10,20,50) + soporte/resistencia
      - Panel 1: RSI (14)
      - Panel 2: MACD (línea, señal y histograma)

    Devuelve la figura matplotlib.
    """
    # 1) Obtener DataFrame 6h
    df = get_ohlcv_data(symbol, "6h", limit)
    if df.empty:
        return None

    # 2) Calcular RSI y MACD sobre precios de cierre
    close = df['Close']
    rsi = compute_rsi(close, period=14)
    macd_line, signal_line, histogram = compute_macd(close)

    # 3) Calcular SMAs para candlestick
    sma10 = close.rolling(10).mean()
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    support = close.min()
    resistance = close.max()

    # 4) Definir estilo
    mc = mpf.make_marketcolors(up='#00ff00', down='#ff4500',
                               edge={'up':'#00ff00','down':'#ff4500'},
                               wick={'up':'#00ff00','down':'#ff4500'})
    style = mpf.make_mpf_style(base_mpf_style='nightclouds',
                               marketcolors=mc,
                               facecolor='#0f0f0f',
                               gridcolor='dimgray',
                               gridstyle='--',
                               rc={'font.size': 8,
                                   'figure.facecolor':'#0f0f0f',
                                   'axes.facecolor':'#0f0f0f',
                                   'axes.edgecolor':'white',
                                   'axes.labelcolor':'white',
                                   'xtick.color':'white',
                                   'ytick.color':'white'})

    # 5) Construir las “addplot” para cada panel
    ap = [
        # Panel 0: SMAs y niveles de soporte/resistencia
        mpf.make_addplot(sma10, color='green', panel=0, width=1.0),
        mpf.make_addplot(sma20, color='lightskyblue', panel=0, width=1.0),
        mpf.make_addplot(sma50, color='pink', panel=0, width=1.0),
        mpf.make_addplot([support]*len(df), color='red', linestyle='--', panel=0, width=1),
        mpf.make_addplot([resistance]*len(df), color='yellow', linestyle='--', panel=0, width=1),

        # RSI en panel 1
        mpf.make_addplot(rsi, panel=1, color='white', ylabel='RSI'),

        # MACD en panel 2: línea MACD, línea señal y histograma
        mpf.make_addplot(macd_line, panel=2, color='yellow', width=1.0, ylabel='MACD'),
        mpf.make_addplot(signal_line, panel=2, color='white', width=1.0),
        mpf.make_addplot(histogram, type='bar', panel=2, color='dimgray', alpha=0.6)
    ]

    title = f"{symbol} - 6h - {datetime.now():%Y-%m-%d %H:%M:%S}"
    # panel_ratios: 3 para el candlestick, 1 para RSI, 1 para MACD
    fig, axes = mpf.plot(
        df,
        type='candle',
        style=style,
        title=title,
        addplot=ap,
        returnfig=True,
        figsize=(10, 8),
        panel_ratios=(3, 1, 1),
        volume=False  # no mostramos volumen en este reporte
    )

    # Ajustes estéticos
    fig.patch.set_facecolor('black')
    for ax in axes:
        ax.set_facecolor('black')
        ax.yaxis.label.set_color('lime')
        for label in ax.get_xticklabels():
            label.set_color('white')
        for label in ax.get_yticklabels():
            label.set_color('white')

    fig.suptitle(title, color='lime', fontsize=9, ha='center', y=0.95)

    # Firma
    fig.text(0.90, 0.02, "HiggsX - Ulu Labs", ha='center', va='bottom', color='lime', fontsize=7)

    return fig

def send_6h_report_chart(caption: str, message_thread_id: int = None):
    """
    Llama a plot_6h_report_chart(), genera la figura y la envía a Telegram
    junto con el caption (mensaje de texto).
    """
    fig = plot_6h_report_chart(SYMBOL, LIMIT)
    if fig is None:
        print("No se pudo generar el gráfico 6h (sin datos).")
        return

    buf = io.BytesIO()
    fig.savefig(buf, dpi=150, format='png', facecolor=fig.get_facecolor())
    buf.seek(0)

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    files = {'photo': buf}
    data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
    if message_thread_id is not None:
        data['message_thread_id'] = message_thread_id

    resp = requests.post(url, data=data, files=files)
    if resp.status_code != 200:
        print("Error al enviar el gráfico 6h:", resp.text)
    else:
        print(f"Gráfico 6h enviado en topic {message_thread_id or 'general'}.")

#############################
# NUEVO: GRÁFICO COMBINADO 1D + DOMINANCIA
#############################

def plot_all_dominance_chart(limit_days: int = 90) -> plt.Figure:
    """
    Genera un gráfico de líneas que muestra, para los últimos `limit_days` días:
      - Dominancia diaria de BTC (%) en naranja
      - Dominancia diaria de ETH (%) en azul
      - Dominancia diaria de Others (%) en gris
    Como CMC solo entrega el valor actual (no histórico), aquí simularíamos
    una serie “plana” con el valor actual para cada día en el rango. Si en
    punto deseas datos históricos reales, necesitarías otro endpoint/pago.
    De momento, graficamos el valor actual repetido para los últimos limit_days.
    """
    # 1) Obtener la dominancia actual de BTC/ETH/Others
    dom = fetch_historical_dominance()
    btc_dom   = dom.get("btc")
    eth_dom   = dom.get("eth")
    others_dom= dom.get("others")

    # 2) Construir un índice de fechas (últimos `limit_days` días hasta hoy)
    hoy = pd.Timestamp.utcnow().normalize()
    fechas = pd.date_range(end=hoy, periods=limit_days, freq='D')

    # 3) Construir tres series: si el valor es None, ponemos NaN
    if btc_dom is not None:
        serie_btc = pd.Series([btc_dom]*limit_days, index=fechas)
    else:
        serie_btc = pd.Series([np.nan]*limit_days, index=fechas)

    if eth_dom is not None:
        serie_eth = pd.Series([eth_dom]*limit_days, index=fechas)
    else:
        serie_eth = pd.Series([np.nan]*limit_days, index=fechas)

    if others_dom is not None:
        serie_others = pd.Series([others_dom]*limit_days, index=fechas)
    else:
        serie_others = pd.Series([np.nan]*limit_days, index=fechas)

    # 4) Crear la figura y el único panel
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(serie_btc.index, serie_btc.values, label='BTC Dominancia', color='orange', linewidth=2)
    ax.plot(serie_eth.index, serie_eth.values, label='ETH Dominancia', color='skyblue', linewidth=2)
    ax.plot(serie_others.index, serie_others.values, label='Others Dominancia', color='lightgray', linewidth=2)

    # 5) Formato: ejes, leyenda, títulos
    ax.set_title(f"Dominancia BTC / ETH / Others (últimos {limit_days} días)\n{datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC", color='white', fontsize=12)
    ax.set_ylabel("Dominancia (%)", color='white')
    ax.set_xlabel("Fecha (UTC)", color='white')
    ax.set_ylim(0, 100)
    ax.grid(True, linestyle='--', color='dimgray', alpha=0.7)

    # Colorear ticks
    ax.tick_params(axis='x', colors='white', rotation=45)
    ax.tick_params(axis='y', colors='white')
    # Leyenda
    legend = ax.legend(loc='upper left', facecolor='#333333', framealpha=0.8, fontsize=9)
    for text in legend.get_texts():
        text.set_color("white")

    # Firma y fondo
    fig.patch.set_facecolor('#0f0f0f')
    ax.set_facecolor('#0f0f0f')
    fig.tight_layout(pad=2)

    # Firma pequeña abajo a la derecha
    fig.text(0.90, 0.02, "HiggsX - Ulu Labs", ha='center', va='bottom', color='lime', fontsize=7)

    return fig

def send_all_dominance_chart(caption: str = "Dominancia BTC/ETH/Others", message_thread_id: int = None):
    """
    Llama a plot_all_dominance_chart(), genera la figura y la envía a Telegram.
    """
    fig = plot_all_dominance_chart(limit_days=LIMIT)
    if fig is None:
        print("No se pudo generar el gráfico de dominancia.")
        return

    buf = io.BytesIO()
    fig.savefig(buf, dpi=150, format='png', facecolor=fig.get_facecolor())
    buf.seek(0)

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    files = {'photo': buf}
    data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}
    if message_thread_id is not None:
        data['message_thread_id'] = message_thread_id

    resp = requests.post(url, data=data, files=files)
    if resp.status_code != 200:
        print("Error al enviar dominancia a Telegram:", resp.text)
    else:
        print(f"Gráfico de dominancia enviado en thread {message_thread_id or 'general'}.")

# Si quieres probar localmente:
if __name__ == "__main__":
    fig = plot_all_dominance_chart(limit_days=30)
    if fig:
        send_all_dominance_chart("Prueba de Dominancia BTC/ETH/Others", message_thread_id=None)