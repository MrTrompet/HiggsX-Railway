# news.py

import requests
import logging
from datetime import datetime, timedelta
from config import NEWS_API_KEY  # La API key se define en config.py
from newspaper3k import Article

logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(levelname)s] %(message)s')

REQUIRED_KEYWORDS = [
    "sui", "etf", "bitcoin", "ethereum", "microstrategy", "grayscale", "blackrock",
    "fidelity", "ark invest", "bitwise", "ripple", "xrp", "cardano", "ondo", "aave",
    "avax", "gold", "interest rate", "powell", "crypto", "fed", "federal reserve",
    "solana", "memecoin", "elon musk", "dogecoin", "shiba inu", "metaverse",
    "defi", "huobi", "hashrate", "gas fees", "blockchain", "japan",
    "nvidia", "traders", "alcoin"
]

def is_informative(title):
    if not title:
        return False
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in REQUIRED_KEYWORDS)

def translate_to_spanish(text):
    """
    Traduce 'text' de inglés a español usando el API gratuito MyMemory.
    Si falla, devuelve el texto original.
    """
    try:
        params = {
            "q": text,
            "langpair": "en|es"
        }
        resp = requests.get("https://api.mymemory.translated.net/get", params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return data.get("responseData", {}).get("translatedText", text)
    except Exception:
        return text

def translate_to_english(text):
    """
    Traduce 'text' de español a inglés usando el API gratuito MyMemory.
    Si falla, devuelve el texto original.
    """
    try:
        params = {
            "q": text,
            "langpair": "es|en"
        }
        resp = requests.get("https://api.mymemory.translated.net/get", params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return data.get("responseData", {}).get("translatedText", text)
    except Exception:
        return text

def test_get_headlines(limit=4):
    """
    Obtiene titulares de NewsAPI (inglés), filtra por palabras clave
    y traduce al español. Devuelve hasta 'limit' titulares en español.
    """
    url = "https://newsapi.org/v2/everything"
    now = datetime.utcnow()
    two_days_ago = now - timedelta(days=2)
    query = 'bitcoin OR crypto OR blockchain OR FED OR "Federal Reserve" OR ETF OR traders'

    params = {
        "apiKey": NEWS_API_KEY,
        "q": query,
        "from": two_days_ago.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 50
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "ok":
            logging.error("Error en la respuesta de NewsAPI: %s", data)
            return "Error en la respuesta de NewsAPI."
        articles = data.get("articles", [])
        unique_headlines = []
        seen = set()

        for article in articles:
            title = article.get("title")
            if title:
                title = title.strip()
            else:
                continue

            if not is_informative(title):
                continue

            # Traducir al español usando MyMemory
            title_es = translate_to_spanish(title)

            published_at = article.get("publishedAt", "")
            try:
                pub_date = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
                pub_date_str = pub_date.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pub_date_str = published_at

            if title_es not in seen:
                unique_headlines.append(f"{pub_date_str} - {title_es}")
                seen.add(title_es)

        if unique_headlines:
            return "\n".join(unique_headlines[:limit])
        else:
            return "No se encontraron titulares informativos."

    except requests.exceptions.HTTPError as http_err:
        logging.error("Error al obtener noticias: %s", http_err)
        return "Error al obtener titulares."
    except Exception as e:
        logging.error("Excepción al obtener titulares: %s", e)
        return f"Excepción al obtener titulares: {e}"

def search_article_by_title(title):
    """
    Busca en NewsAPI un artículo que coincida exactamente (entre comillas) con el título dado.
    Dado que el usuario puede pasar el título en español, primero lo traducimos a inglés.
    Retorna la URL del primer artículo encontrado o None si no se encuentra.
    """
    url = "https://newsapi.org/v2/everything"
    now = datetime.utcnow()
    two_days_ago = now - timedelta(days=2)

    # Traducir el título de español a inglés antes de buscar
    title_en = translate_to_english(title)

    params = {
       "apiKey": NEWS_API_KEY,
       "q": f'"{title_en}"',
       "from": two_days_ago.strftime("%Y-%m-%dT%H:%M:%SZ"),
       "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
       "language": "en",
       "sortBy": "publishedAt",
       "pageSize": 1
    }
    try:
       response = requests.get(url, params=params, timeout=10)
       response.raise_for_status()
       data = response.json()
       if data.get("status") != "ok":
          logging.error("Error en search_article_by_title: %s", data)
          return None
       articles = data.get("articles", [])
       if articles:
          return articles[0].get("url")
       else:
          return None
    except Exception as e:
       logging.error("Excepción en search_article_by_title: %s", e)
       return None

def get_article_content(article_url):
    """
    Descarga y extrae el contenido del artículo usando Newspaper (en inglés),
    y luego lo traduce al español. Retorna el texto traducido o un mensaje de error.
    """
    try:
        article = Article(article_url)
        article.download()
        article.parse()
        content = article.text
        if not content:
            return "No se pudo extraer el contenido de la noticia."
        # Traducir todo el contenido al español
        return translate_to_spanish(content)
    except Exception as e:
        logging.error("Error al extraer contenido de la noticia: %s", e)
        return "No se pudo extraer el contenido de la noticia."

if __name__ == "__main__":
    print("Titulares obtenidos:")
    print(test_get_headlines(4))
    # Para probar la búsqueda y extracción, puedes descomentar:
    # title_es = "La elección de un aliado de Trump en Polonia podría alterar las políticas de la UE y Ucrania"
    # url = search_article_by_title(title_es)
    # if url:
    #     print("URL:", url)
    #     print("Contenido del artículo:")
    #     print(get_article_content(url))
