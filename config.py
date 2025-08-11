import os

# -------------------------------------------------
# Rate Limiting & Caching Settings
# -------------------------------------------------
TELEGRAM_RATE_LIMIT = int(os.getenv('TELEGRAM_RATE_LIMIT', 30))  # Máximo de mensajes por minuto para Telegram
OPENAI_RATE_LIMIT = int(os.getenv('OPENAI_RATE_LIMIT', 20))      # Máximo de llamadas por minuto para OpenAI
CACHING_INTERVAL_INDICATORS = int(os.getenv('CACHING_INTERVAL_INDICATORS', 10))  # Intervalo (segundos) para actualizar indicadores
CACHING_INTERVAL_DOMINANCE = int(os.getenv('CACHING_INTERVAL_DOMINANCE', 300))  # Intervalo (segundos) para actualizar la dominancia de BTC

# -------------------------------------------------
# Feature Columns for ML Model (si se requiere)
# -------------------------------------------------
feature_columns = ['open', 'high', 'low', 'close', 'volume', 'sma_25', 'bb_low', 'bb_medium', 'bb_high']

# -------------------------------------------------
# Coinbase API Keys (modo solo lectura)
# -------------------------------------------------
API_KEY = os.getenv('COINBASE_API_KEY', "")
API_SECRET = os.getenv('COINBASE_API_SECRET', "")

# -------------------------------------------------
# CoinMarketCap API Key 
# -------------------------------------------------
COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY', "")

# -------------------------------------------------
# CoinGecko API Key 
# -------------------------------------------------
COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY', "")

# -------------------------------------------------
# Telegram Configuration
# -------------------------------------------------
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', "")
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-1002534022214')  # chat_id del grupo general

# Topics específicos (message_thread_id dentro del grupo)
TOPICS = {
    "higgs": int(os.getenv('TELEGRAM_HIGGS_THREAD_ID', 6)),  # ID del topic donde se habla con OpenAI y se piden gráficos
    "noticias": int(os.getenv('TELEGRAM_NOTICIAS_THREAD_ID', 24)),  # ID del topic para noticias y mensajes de la interfaz
    "senales": int(os.getenv('TELEGRAM_SENALES_THREAD_ID', 32))  # ID del topic para señales de trading
}

# Para mayor comodidad:
TELEGRAM_HIGGS_THREAD_ID = TOPICS["higgs"]
TELEGRAM_NOTICIAS_THREAD_ID = TOPICS["noticias"]
TELEGRAM_SENALES_THREAD_ID = TOPICS["senales"]

# Este log debería imprimirse ahora en la salida
print(f"[Config] TELEGRAM_HIGGS_THREAD_ID: {TELEGRAM_HIGGS_THREAD_ID}")

# -------------------------------------------------
# OpenAI API Key
# -------------------------------------------------
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', "")

# -------------------------------------------------
# News API
# -------------------------------------------------
NEWS_API_KEY = os.getenv('NEWS_API_KEY', "")

# -------------------------------------------------
# Initial Trading Operations Configuration
# -------------------------------------------------
SYMBOL = os.getenv('SYMBOL', 'BTC/USDT')
TIMEFRAME = os.getenv('TIMEFRAME', '1h')  # Velas de una hora
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 5))  # Número máximo de reintentos al obtener datos

# Variables globales de estado de operación
last_prediction = None   # Almacena la última dirección predicha para evitar mensajes repetidos
is_always_on_top = False  # Estado inicial del modo "siempre en top"
