import pandas as pd        
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, ADXIndicator
from ta.volume import ChaikinMoneyFlowIndicator
from ta.volatility import BollingerBands
import market  # Para acceder a market.BTC_DOMINANCE

def calculate_indicators(data):
    """
    Calcula indicadores técnicos a partir de un DataFrame con datos OHLCV (en 1h)
    y agrega la BTC dominancia actual (obtenida desde market.BTC_DOMINANCE).

    Parámetros:
      - data (DataFrame): debe contener las columnas 'open', 'high', 'low', 'close' y 'volume'.

    Retorna un diccionario con los siguientes indicadores:
      'price': último precio (close)
      'rsi': RSI (window=14)
      'adx': ADX (window=14)
      'macd': MACD (EMA12 - EMA26)
      'macd_signal': línea de señal (SMA del MACD, window=9)
      'hist': histograma (MACD - línea de señal)
      'sma_10': SMA de 10 períodos
      'sma_25': SMA de 25 períodos
      'sma_50': SMA de 50 períodos
      'cmf': Chaikin Money Flow
      'volume_level': "Alto", "Moderado" o "Bajo" según CMF
      'bb_low': Banda inferior de Bollinger (window=20, window_dev=2)
      'bb_medium': Media móvil de Bollinger
      'bb_high': Banda superior de Bollinger
      'prev_close': precio de cierre anterior
      'btc_dominance': valor cacheado de la dominancia de BTC (desde market.py)
    """
    close = data['close']
    high = data['high']
    low = data['low']
    volume = data['volume']

    # --- Cálculo de MACD al estilo TradingView ---
    # Calcular EMA rápida y lenta
    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    # La línea de señal se calcula como la SMA del MACD en 9 períodos
    signal_line = macd_line.rolling(window=9).mean()
    hist = macd_line - signal_line

    # --- Otros indicadores ---
    # Chaikin Money Flow (CMF)
    cmf = ChaikinMoneyFlowIndicator(high, low, close, volume).chaikin_money_flow().iloc[-1]
    volume_level = "Alto" if cmf > 0.1 else "Bajo" if cmf < -0.1 else "Moderado"

    # Medias móviles simples (SMA)
    sma_10 = SMAIndicator(close, window=10).sma_indicator().iloc[-1]
    sma_25 = SMAIndicator(close, window=25).sma_indicator().iloc[-1]
    sma_50 = SMAIndicator(close, window=50).sma_indicator().iloc[-1]

    # RSI y ADX
    rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
    adx = ADXIndicator(high, low, close).adx().iloc[-1]

    # Bandas de Bollinger (window=20, window_dev=2)
    bb_indicator = BollingerBands(close, window=20, window_dev=2)
    bb_low = bb_indicator.bollinger_lband().iloc[-1]
    bb_medium = bb_indicator.bollinger_mavg().iloc[-1]
    bb_high = bb_indicator.bollinger_hband().iloc[-1]

    indicators = {
        'price': close.iloc[-1],
        'rsi': rsi,
        'adx': adx,
        'macd': macd_line.iloc[-1],
        'macd_signal': signal_line.iloc[-1],
        'hist': hist.iloc[-1],
        'sma_10': sma_10,
        'sma_25': sma_25,
        'sma_50': sma_50,
        'cmf': cmf,
        'volume_level': volume_level,
        'bb_low': bb_low,
        'bb_medium': bb_medium,
        'bb_high': bb_high,
        'prev_close': close.iloc[-2],
        'btc_dominance': market.BTC_DOMINANCE  # Valor cacheado actualizado en market.py
    }
    return indicators

# Ejemplo de uso (para pruebas)
if __name__ == "__main__":
    import ccxt
    import pandas as pd
    # Ejemplo de obtención de datos desde Coinbase (esto normalmente se gestiona en market.py)
    exchange = ccxt.coinbase()
    markets = exchange.load_markets()
    pairs = list(markets.keys())
    if not pairs:
        raise Exception("No se encontraron pares disponibles.")
    selected_pair = pairs[0]
    print(f"Par seleccionado para análisis: {selected_pair}")

    timeframe = "1h"  # Aseguramos 1 hora
    limit = 100
    ohlcv = exchange.fetch_ohlcv(selected_pair, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    print("\nDatos OHLCV (muestra):")
    print(df.head())

    # Calcular indicadores técnicos
    ind = calculate_indicators(df)
    print("\nIndicadores calculados:")
    for key, value in ind.items():
        print(f"{key}: {value}")
