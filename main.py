# main.py
import logging
import secrets
import os
from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.responses import Response
from scraper import search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY_FILE = "/app/data/api_key.txt"

CATEGORIES = {
    "2145": {"id": 2145, "name": "Film/Vidéo"},
    "2178": {"id": 2178, "name": "Film/Vidéo : Animation"},
    "2179": {"id": 2179, "name": "Film/Vidéo : Animation Série"},
    "2180": {"id": 2180, "name": "Film/Vidéo : Concert"},
    "2181": {"id": 2181, "name": "Film/Vidéo : Documentaire"},
    "2182": {"id": 2182, "name": "Film/Vidéo : Emission TV"},
    "2183": {"id": 2183, "name": "Film/Vidéo : Film"},
    "2184": {"id": 2184, "name": "Film/Vidéo : Série TV"},
    "2185": {"id": 2185, "name": "Film/Vidéo : Spectacle"},
    "2186": {"id": 2186, "name": "Film/Vidéo : Sport"},
    "2187": {"id": 2187, "name": "Film/Vidéo : Vidéo-clips"},
}


def load_or_create_api_key() -> str:
    os.makedirs(os.path.dirname(API_KEY_FILE), exist_ok=True)
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r") as f:
            return f.read().strip()
    api_key = secrets.token_hex(32)
    with open(API_KEY_FILE, "w") as f:
        f.write(api_key)
    logger.info(f"🔑 Clé API générée pour la première fois : {api_key}")
    logger.info(f"🔑 Clé sauvegardée dans '{API_KEY_FILE}'")
    return api_key


API_KEY = load_or_create_api_key()


def verify_api_key(apikey: str = Query(...)):
    if apikey != API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide")
    return apikey


def build_torznab_xml(torrents: list[dict], query: str = "") -> str:
    items = ""
    for t in torrents:
        magnet = t['download_url'].replace('&', '&amp;')
        name = t['name'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        items += f"""
        <item>
            <title>{name}</title>
            <guid>{t['id']}</guid>
            <link>{magnet}</link>
            <pubDate>{t['timestamp']}</pubDate>
            <torznab:attr name="seeders" value="{t['seeders']}"/>
            <torznab:attr name="leechers" value="{t['leechers']}"/>
            <torznab:attr name="size" value="{t['size']}"/>
            <torznab:attr name="category" value="{t['category'] or 2145}"/>
        </item>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
    <channel>
        <title>PyGégé</title>
        <description>YGG Torrent Torznab API</description>
        {items}
    </channel>
</rss>"""


def build_caps_xml() -> str:
    cats = ""
    for cat in CATEGORIES.values():
        cats += f'<category id="{cat["id"]}" name="{cat["name"]}"/>\n'

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<caps>
    <server title="PyGégé"/>
    <searching>
        <search available="yes" supportedParams="q,cat"/>
    </searching>
    <categories>
        {cats}
    </categories>
</caps>"""


app = FastAPI(title="PyGégé - YGG Torznab API")


@app.get("/api")
async def torznab(
    t: str = Query(...),
    q: str = Query(""),
    cat: str = Query(None),
    apikey: str = Depends(verify_api_key)
):
    if t == "caps":
        return Response(content=build_caps_xml(), media_type="application/xml")

    if t == "search":
        results = await search(query=q, category=cat)
        return Response(content=build_torznab_xml(results, q), media_type="application/xml")

    raise HTTPException(status_code=400, detail=f"Type inconnu : {t}")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)