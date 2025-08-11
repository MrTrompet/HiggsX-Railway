# dominance_historical.py

import requests
import logging
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pytz

from config import COINMARKETCAP_API_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M"
)

def fetch_historical_dominance(days_back: int = 100):
    """
    Llama a CoinMarketCap /v1/global-metrics/quotes/historical para
    obtener la dominancia de BTC, ETH y Others durante los últimos `days_back` días.
    Retorna un dict con:
      {
        "dates": [lista_datetime_UTC],
        "btc": [valores_float],
        "eth": [valores_float],
        "others": [valores_float]
      }
    Si ocurre un error (403, 401, etc.), imprime un mensaje y devuelve listas vacías.
    """
    url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/historical"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY
    }

    # Determinar rango de fechas: desde hace `days_back` días hasta ahora (UTC).
    now = datetime.utcnow()
    start = now - timedelta(days=days_back)
    params = {
        "time_start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "time_end": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "interval": "daily",
        "convert": "USD"
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json().get("data", {}).get("quotes", [])
        if not payload:
            logging.error("No se recibieron cotizaciones en 'quotes'. Verifica tu plan de CMC.")
            return {"dates": [], "btc": [], "eth": [], "others": []}

        fechas = []
        btc_dom = []
        eth_dom = []
        oth_dom = []

        for punto in payload:
            # Cada 'punto' tiene: 'timestamp' y 'quote': {'USD': {...}}
            ts_str = punto.get("timestamp")  # p.ej. "2025-03-01T00:00:00.000Z"
            try:
                # Convertir string ISO a objeto datetime (UTC)
                dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                # En caso de que falte .%f
                dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
            valor_usd = punto.get("quote", {}).get("USD", {})
            fechas.append(dt)
            btc_dom.append(valor_usd.get("btc_dominance", 0.0))
            eth_dom.append(valor_usd.get("eth_dominance", 0.0))
            oth_dom.append(valor_usd.get("other_dominance", 0.0))

        return {"dates": fechas, "btc": btc_dom, "eth": eth_dom, "others": oth_dom}

    except requests.exceptions.HTTPError as http_err:
        status = resp.status_code if 'resp' in locals() else None
        if status == 403:
            logging.error("CMC Historical Forbidden (403): tu plan no soporta este endpoint.")
        elif status == 401:
            logging.error("CMC Unauthorized (401): verifica tu COINMARKETCAP_API_KEY.")
        else:
            logging.error("HTTP error al llamar a global-metrics/historical: %s", http_err)
        return {"dates": [], "btc": [], "eth": [], "others": []}

    except Exception as e:
        logging.error("Error genérico al obtener dominancia histórica: %s", e)
        return {"dates": [], "btc": [], "eth": [], "others": []}


def plot_dominance_historical(series: dict):
    """
    Dibuja en Matplotlib la serie histórica de dominancia.
    series debe tener las claves: "dates", "btc", "eth", "others".
    """
    fechas = series.get("dates", [])
    btc_dom = series.get("btc", [])
    eth_dom = series.get("eth", [])
    oth_dom = series.get("others", [])

    if not fechas:
        print("No hay datos para graficar.")
        return

    # Convertir todas las fechas a UTC para que el eje X esté bien ordenado
    # (ya vinieron en UTC, pero por si acaso las re-localizamos)
    fechas_utc = [pytz.utc.localize(dt) for dt in fechas]

    plt.figure(figsize=(14, 6))
    ax = plt.gca()
    ax.set_facecolor("#222222")
    plt.plot(fechas_utc, btc_dom, color="#FFA500", label="BTC Dominancia")
    plt.plot(fechas_utc, eth_dom, color="#00BFFF", label="ETH Dominancia")
    plt.plot(fechas_utc, oth_dom, color="#AAAAAA", label="Others Dominancia")

    # Formato de ejes y etiquetas
    plt.title("Dominancia BTC / ETH / Others (últimos {} días)".format(len(fechas)), color="white")
    plt.suptitle(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), color="white", fontsize="small")
    plt.xlabel("Fecha (UTC)", color="white")
    plt.ylabel("Dominancia (%)", color="white")
    plt.ylim(0, 100)
    plt.grid(color="#555555", linestyle="--", linewidth=0.5)
    plt.legend(facecolor="#333333", edgecolor="white", labelcolor="white")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("white")

    # Formato de fecha en el eje X: mostrar 4 fechas distribuidas
    ax.xaxis.set_major_locator(plt.MaxNLocator(6))
    plt.xticks(rotation=30, ha="right")

    # Ajuste final
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # 1) Descargamos los últimos 100 días de dominancia
    datos = fetch_historical_dominance(days_back=100)
    # 2) Dibujamos la serie
    plot_dominance_historical(datos)
