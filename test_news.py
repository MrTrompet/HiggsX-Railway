import requests
import logging
from datetime import datetime, timedelta

# Tu API key de NewsAPI
NEWS_API_KEY = "b2b85c50bcbf4c69ab92ffd14063b913"

# Configuramos el logging para que solo muestre advertencias y errores
logging.basicConfig(level=logging.WARNING, format='%(asctime)s [%(levelname)s] %(message)s')

# Lista de palabras clave relevantes (en minúsculas)
# Se incluyen términos que esperamos estén en titulares informativos sobre el mundo crypto, ETFs, SEC, etc.
REQUIRED_KEYWORDS = [
    "sui", "etf", "bitcoin", "ethereum", "Microstrategy", "BlackRock", "Ripple", "powell", "crypto", "sec", "federal reserve", "trump",
    "investment", "blockchain", "japan", "tariff", "price", "nvidia", "traders"
]

def is_informative(title):
    """
    Retorna True si el título contiene al menos una de las palabras clave relevantes.
    """
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in REQUIRED_KEYWORDS)

def test_get_headlines(limit=4):
    url = "https://newsapi.org/v2/everything"
    
    # Rango de fechas: últimos 48 horas (UTC)
    now = datetime.utcnow()
    two_days_ago = now - timedelta(days=2)
    
    # Consulta para temas de interés. (La consulta puede devolver artículos amplios; el filtrado posterior se hará con is_informative)
    query = 'bitcoin OR crypto OR blockchain OR SEC OR "Federal Reserve" OR ETF OR trump OR traders'
    
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
        if response.status_code == 200:
            data = response.json()
            if data.get("status") != "ok":
                logging.error("Error en la respuesta de NewsAPI: %s", data)
                return "Error en la respuesta de NewsAPI."
            articles = data.get("articles", [])
            unique_headlines = []
            seen = set()
            for article in articles:
                title = article.get("title", "").strip()
                published_at = article.get("publishedAt", "")
                if not title:
                    continue
                # Filtrar sólo los titulares que resulten informativos
                if not is_informative(title):
                    continue
                # Convertir la fecha de publicación a formato legible
                try:
                    pub_date = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
                    pub_date_str = pub_date.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pub_date_str = published_at
                if title not in seen:
                    unique_headlines.append(f"{pub_date_str} - {title}")
                    seen.add(title)
            if unique_headlines:
                return "\n".join(unique_headlines[:limit])
            else:
                return "No se encontraron titulares informativos."
        else:
            logging.error("Error al obtener noticias: %s", response.text)
            return "Error al obtener titulares."
    except Exception as e:
        logging.error("Excepción al obtener titulares: %s", e)
        return f"Excepción al obtener titulares: {e}"

if __name__ == "__main__":
    print("Titulares obtenidos:")
    print(test_get_headlines(4))
