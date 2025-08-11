# ------------------
# telegram_handler.py
# ------------------
import re
import requests
import openai
import time
from langdetect import detect

from config import (
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_HIGGS_THREAD_ID,
    OPENAI_API_KEY,
    SYMBOL,
    TIMEFRAME,
)
from market import fetch_data
from indicators import calculate_indicators
from memoria import store_message, add_task
from onchain import fetch_onchain_stats

# Configurar OpenAI (usando GPT-4)
openai.api_key = OPENAI_API_KEY
START_TIME = int(time.time())

MIN_TIME_BETWEEN_OPENAI_CALLS = 3
MIN_TIME_BETWEEN_TELEGRAM_SEND = 2

last_openai_call = 0
last_telegram_send = 0
_last_photo_send = 0    # ← inicialización necesaria para send_telegram_photo

def send_telegram_message(mensaje, chat_id=None, message_thread_id=None):
    global last_telegram_send
    if chat_id is None:
        chat_id = TELEGRAM_CHAT_ID

    now = time.time()
    elapsed = now - last_telegram_send
    if elapsed < MIN_TIME_BETWEEN_TELEGRAM_SEND:
        time.sleep(MIN_TIME_BETWEEN_TELEGRAM_SEND - elapsed)

    payload = {"chat_id": chat_id, "text": mensaje}
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json=payload,
            timeout=30
        )
        if resp.status_code != 200:
            print(f"[Telegram] Error: {resp.text}")
        else:
            print(f"[Telegram] Mensaje enviado a {chat_id} en thread {message_thread_id}")
    except Exception as e:
        print(f"[Telegram] Conexión fallida: {e}")
    last_telegram_send = time.time()

def send_telegram_photo(photo_url: str, chat_id=None, message_thread_id=None, caption: str = None):
    """
    Envía una foto a Telegram usando sendPhoto.
    - photo_url: URL pública de la imagen.
    - chat_id: destino (por defecto TELEGRAM_CHAT_ID).
    - message_thread_id: si queremos en un topic/thread dentro del grupo.
    - caption: texto opcional que acompaña la foto.
    """
    global _last_photo_send
    if chat_id is None:
        chat_id = TELEGRAM_CHAT_ID

    now = time.time()
    elapsed = now - _last_photo_send
    if elapsed < MIN_TIME_BETWEEN_TELEGRAM_SEND:
        time.sleep(MIN_TIME_BETWEEN_TELEGRAM_SEND - elapsed)

    payload = {
        "chat_id": chat_id,
        "photo": photo_url
    }
    if message_thread_id is not None:
        payload["message_thread_id"] = message_thread_id
    if caption is not None:
        payload["caption"] = caption

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
            json=payload,
            timeout=30
        )
        if resp.status_code != 200:
            print(f"[Telegram sendPhoto] Error: {resp.text}")
        else:
            print(f"[Telegram sendPhoto] Foto enviada a {chat_id} en thread {message_thread_id}")
    except Exception as e:
        print(f"[Telegram sendPhoto] Conexión fallida: {e}")
    _last_photo_send = time.time()

def detect_language(texto):
    try:
        return detect(texto)
    except:
        return "es"

def get_updates(offset=None):
    params = {}
    if offset is not None:
        params["offset"] = offset
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
            params=params,
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("result", [])
        print(f"[Telegram] getUpdates error: {resp.text}")
    except Exception as e:
        print(f"[Telegram] getUpdates fallo: {e}")
    return []

def handle_telegram_message(update):
    global last_openai_call

    msg = update.get("message", {})
    text = (msg.get("text") or "").strip()
    chat_id = msg.get("chat", {}).get("id")
    thread_id = msg.get("message_thread_id")
    print(f"[Telegram Handler] Thread ID recibido: {thread_id}")  # Esto va a mostrar el thread_id recibido
    user = msg.get("from", {})
    username = user.get("username") or user.get("first_name", "Agente")
    date = msg.get("date", 0)
    

    # Solo procesar dentro del thread privado de Higgs X
    if thread_id != TELEGRAM_HIGGS_THREAD_ID:
        print(f"[Telegram Handler] Ignorando mensaje en thread {thread_id} (esperaba {TELEGRAM_HIGGS_THREAD_ID})")
        return

    if not text or not chat_id or date < START_TIME:
        return

    # BÚSQUEDA y ampliación de noticia (si quieres incluirla, asegúrate de declarar article_content)
    article_content = ""
    try:
        from news import search_article_by_title, get_article_content
        url = search_article_by_title(text)
        if url:
            try:
                article_content = get_article_content(url)
            except:
                article_content = "No se pudo extraer el contenido de la noticia."
    except ImportError:
        article_content = ""

    # Obtener datos on-chain
    onchain = fetch_onchain_stats()

    # Guardar mensaje en memoria
    store_message(username, text)

    # COMANDO “Programa: X en Y minutos”
    if text.lower().startswith("programa"):
        m = re.search(r"en\s+(\d+)\s+minutos", text.lower())
        if m:
            mins = int(m.group(1))
            run_at = time.time() + mins * 60
            dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(run_at))
            add_task(text, dt)
            send_telegram_message(
                f"Tarea guardada: «{text}»\nSe ejecutará a las {dt}",
                chat_id,
                thread_id,
            )
        else:
            send_telegram_message(
                "Formato inválido. Usa: Programa: <tarea> en X minutos",
                chat_id,
                thread_id,
            )
        return

    # PETICIÓN DE GRÁFICO
    if any(w in text.lower() for w in ("grafico", "gráfico")):
        from PrintGraphic import send_graphic, extract_timeframe

        tf = extract_timeframe(text)
        chart_type = "line"
        if any(k in text.lower() for k in ("vela", "velas", "candlestick", "japonesas")):
            chart_type = "candlestick"

        send_graphic(
            TELEGRAM_CHAT_ID,
            tf,
            chart_type,
            message_thread_id=TELEGRAM_HIGGS_THREAD_ID,
        )
        return

    # Consulta a GPT-4
    system = (
        "Eres Higgs X, agente de inteligencia infiltrado en la blockchain. "
        "Analista mercantil y de noticias sobre Bitcoin (BTC). Tu misión es proteger "
        "al equipo de pérdidas en Bitcoin, usando memoria de contexto. Responde "
        "conciso, serio y misterioso con un toque creativo y firma como 'Higgs X'."
    )

    # Datos técnicos (fetch_data + calculate_indicators)
    data = fetch_data(SYMBOL, TIMEFRAME)
    ind = calculate_indicators(data)

    # Funciones auxiliares de formateo (None → "N/D")
    def fmt_usd(val):
        return f"${val:,.0f}" if isinstance(val, (int, float)) else "N/D"
    def fmt_usd_dec(val):
        return f"${val:,.2f}" if isinstance(val, (int, float)) else "N/D"
    def fmt_num(val, suffix=""):
        return f"{val:,.0f}{suffix}" if isinstance(val, (int, float)) else "N/D"

    # Campos on-chain extraídos
    mc       = onchain.get("marketcap_usd")
    vol24    = onchain.get("volume_24h_usd")
    high24   = onchain.get("high_24h_usd")
    low24    = onchain.get("low_24h_usd")
    ath      = onchain.get("ath_price_usd")
    circ_s   = onchain.get("circulating_supply")
    tot_s    = onchain.get("total_supply")
    # Si no tienes dominance en onchain, sácalo de calculate_indicators:
    dom      = ind.get("btc_dominance")  # <-- ya la devolvía calculate_indicators
    gmcap    = onchain.get("total_marketcap_usd")      # <- estos dos no existen a menos que los añadas a onchain
    gvol     = onchain.get("total_volume_24h_usd")
    hr       = onchain.get("hashrate")
    whales   = onchain.get("whale_count")

    # Formateo
    mc_str     = fmt_usd(mc)
    vol24_str  = fmt_usd(vol24)
    high24_str = fmt_usd_dec(high24)
    low24_str  = fmt_usd_dec(low24)
    ath_str    = fmt_usd(ath)
    circ_str   = fmt_num(circ_s, " BTC")
    tot_str    = fmt_num(tot_s, " BTC")
    dom_str    = f"{dom:.2f}%" if isinstance(dom, (int, float)) else "N/D"
    gmcap_str  = fmt_usd(gmcap)
    gvol_str   = fmt_usd(gvol)
    hr_str     = f"{hr:,.2f} TH/s" if isinstance(hr, (int, float)) else "N/D"
    whales_str = fmt_num(whales)

    prompt = (
        f"@{username}, aquí Higgs X al habla.\n\n"
        f"🔍 Indicadores de {SYMBOL}:\n"
        f"- Precio: ${ind.get('price',0):.2f}\n"
        f"- RSI: {ind.get('rsi',0):.2f}\n"
        f"- MACD: {ind.get('macd',0):.2f} (Señal {ind.get('macd_signal',0):.2f})\n"
        f"- SMA: {ind.get('sma_10',0):.2f}|{ind.get('sma_25',0):.2f}|{ind.get('sma_50',0):.2f}\n"
        f"- Volumen (nivel): {ind.get('volume_level','N/A')} (CMF: {ind.get('cmf',0):.2f})\n\n"
        f"🧮 Datos on-chain actuales:\n"
        f"- MarketCap (USD): {mc_str}\n"
        f"- Volumen 24h (USD): {vol24_str}\n"
        f"- High 24h (USD): {high24_str}\n"
        f"- Low 24h (USD): {low24_str}\n"
        f"- ATH histórico (USD): {ath_str}\n"
        f"- Circulating Supply: {circ_str}\n"
        f"- Total Supply: {tot_str}\n"
        f"- BTC Dominance: {dom_str}\n"
        f"- Global MarketCap (USD): {gmcap_str}\n"
        f"- Global Volumen 24h (USD): {gvol_str}\n"
        f"- Hashrate (TH/s): {hr_str}\n"
        f"- Whale Count (≥1000 BTC): {whales_str}\n\n"
        "Con esta información completa, proporciona un análisis detallado del estado actual del mercado.\n"
        f"Pregunta: {text}"
    )
    if article_content:
        prompt += "\n\n📰 Ampliación:\n" + article_content

    # Throttling OpenAI
    now = time.time()
    if now - last_openai_call < MIN_TIME_BETWEEN_OPENAI_CALLS:
        time.sleep(MIN_TIME_BETWEEN_OPENAI_CALLS - (now - last_openai_call))

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.7,
        )
        answer = resp.choices[0].message.content.strip()
        # Escapado correcto de markdown
        for ch in ["_", "*", "[", "`"]:
            answer = answer.replace(ch, f"\\{ch}")
    except Exception as e:
        answer = f"⚠️ Error al procesar: {e}"

    last_openai_call = time.time()
    send_telegram_message(answer, chat_id, thread_id)
    store_message("Higgs X", answer)
