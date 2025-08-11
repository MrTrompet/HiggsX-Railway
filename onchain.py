# onchain.py

import requests
import logging
import time
from datetime import datetime, timedelta

from config import COINMARKETCAP_API_KEY  # Asegúrate de que existan en config.py

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M"
)

CMC_HEADERS = {
    "X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY,
    "Accept": "application/json"
}


def fetch_cmc_quotes_latest(symbol: str = "BTC") -> dict:
    """
    Llama a /v1/cryptocurrency/quotes/latest de CoinMarketCap para obtener:
      - marketcap_usd
      - volume_24h_usd
    Devuelve campos None si falla o no están disponibles.
    """
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = {"symbol": symbol, "convert": "USD"}

    try:
        resp = requests.get(url, headers=CMC_HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json().get("data", {}).get(symbol, {})
        quote_usd = payload.get("quote", {}).get("USD", {})

        return {
            "marketcap_usd": quote_usd.get("market_cap"),
            "volume_24h_usd": quote_usd.get("volume_24h")
        }
    except requests.exceptions.HTTPError as http_err:
        status = resp.status_code if "resp" in locals() else None
        logging.error(f"CMC quotes/latest HTTP {status}: {http_err}")
    except Exception as e:
        logging.error(f"Error al obtener datos de CMC quotes/latest: {e}")

    return {
        "marketcap_usd": None,
        "volume_24h_usd": None
    }


def fetch_cmc_global_metrics() -> dict:
    """
    Llama a /v1/global-metrics/quotes/latest de CoinMarketCap para obtener:
      - btc_dominance
    Devuelve None si falla o no está disponible.
    """
    url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
    params = {"convert": "USD"}

    try:
        resp = requests.get(url, headers=CMC_HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        gm = resp.json().get("data", {})

        return {
            "btc_dominance": gm.get("btc_dominance")
        }
    except requests.exceptions.HTTPError as http_err:
        status = resp.status_code if "resp" in locals() else None
        logging.error(f"CMC global metrics HTTP {status}: {http_err}")
    except Exception as e:
        logging.error(f"Error al obtener CMC global metrics: {e}")

    return {
        "btc_dominance": None
    }


def fetch_coingecko_market_data() -> dict:
    """
    Consulta CoinGecko para obtener:
      - high_24h_usd
      - low_24h_usd
      - ath_price_usd
      - circulating_supply
      - total_supply
    Devuelve todos los campos None en caso de error.
    """
    url = "https://api.coingecko.com/api/v3/coins/bitcoin"
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false"
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        md = data.get("market_data", {})

        return {
            "high_24h_usd": md.get("high_24h", {}).get("usd"),
            "low_24h_usd": md.get("low_24h", {}).get("usd"),
            "ath_price_usd": md.get("ath", {}).get("usd"),
            "circulating_supply": md.get("circulating_supply"),
            "total_supply": md.get("total_supply")
        }
    except requests.exceptions.HTTPError as http_err:
        if resp.status_code == 429:
            logging.error("CoinGecko 429 Too Many Requests; devolviendo None.")
        else:
            logging.error(f"Error HTTP CoinGecko: {http_err}")
    except Exception as e:
        logging.error(f"Error al obtener datos de CoinGecko: {e}")

    return {
        "high_24h_usd": None,
        "low_24h_usd": None,
        "ath_price_usd": None,
        "circulating_supply": None,
        "total_supply": None
    }


def fetch_blockchain_hashrate() -> float:
    """
    Consulta Blockchain.info para obtener el hashrate (último dato).
    Devuelve None en caso de error.
    """
    url = "https://api.blockchain.info/charts/hash-rate?format=json"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("values", [])
        if data:
            return float(data[-1].get("y"))
    except Exception as e:
        logging.error(f"Error al obtener hashrate de Blockchain.info: {e}")
    return None


def fetch_onchain_stats() -> dict:
    """
    Combina:
      1) CMC quotes/latest para marketcap_usd y volume_24h_usd
      2) CMC global metrics para btc_dominance
      3) Blockchain.info para hashrate
      4) CoinGecko para high_24h_usd, low_24h_usd, ath_price_usd,
         circulating_supply, total_supply

    Campos devueltos:
      - marketcap_usd
      - volume_24h_usd
      - high_24h_usd
      - low_24h_usd
      - ath_price_usd
      - circulating_supply
      - total_supply
      - btc_dominance
      - hashrate
    """
    stats = {
        "marketcap_usd": None,
        "volume_24h_usd": None,
        "high_24h_usd": None,
        "low_24h_usd": None,
        "ath_price_usd": None,
        "circulating_supply": None,
        "total_supply": None,
        "btc_dominance": None,
        "hashrate": None
    }

    # 1) CMC quotes/latest
    cmc_q = fetch_cmc_quotes_latest("BTC")
    stats.update(cmc_q)

    # 2) CMC global metrics
    cmc_gm = fetch_cmc_global_metrics()
    stats.update(cmc_gm)

    # 3) Hashrate de Blockchain.info
    stats["hashrate"] = fetch_blockchain_hashrate()

    # 4) Siempre obtenemos high/low/ath/supply de CoinGecko, 
    #    ya que CMC en el plan actual no da esos datos históricos.
    cg = fetch_coingecko_market_data()
    for key in [
        "high_24h_usd",
        "low_24h_usd",
        "ath_price_usd",
        "circulating_supply",
        "total_supply"
    ]:
        stats[key] = cg.get(key)

    return stats


if __name__ == "__main__":
    t0 = time.time()
    s = fetch_onchain_stats()
    t1 = time.time()
    print(f"On-chain stats obtenidos en {t1-t0:.2f}s:")
    for k, v in s.items():
        print(f"  - {k}: {v}")
