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

ALL_CATS = {
    "2145": "Film/Vidéo",
    "2178": "Film/Vidéo : Animation",
    "2179": "Film/Vidéo : Animation Série",
    "2180": "Film/Vidéo : Concert",
    "2181": "Film/Vidéo : Documentaire",
    "2182": "Film/Vidéo : Emission TV",
    "2183": "Film/Vidéo : Film",
    "2184": "Film/Vidéo : Série TV",
    "2185": "Film/Vidéo : Spectacle",
    "2186": "Film/Vidéo : Sport",
    "2187": "Film/Vidéo : Vidéo-clips",
    "2139": "Audio",
    "2147": "Audio : Karaoké",
    "2148": "Audio : Musique",
    "2149": "Audio : Samples",
    "2150": "Audio : Podcast Radio",
    "2144": "Application",
    "2171": "Application : Linux",
    "2172": "Application : MacOS",
    "2173": "Application : Windows",
    "2174": "Application : Smartphone",
    "2175": "Application : Tablette",
    "2176": "Application : Formation",
    "2177": "Application : Autre",
    "2142": "Jeu vidéo",
    "2159": "Jeu vidéo : Linux",
    "2160": "Jeu vidéo : MacOS",
    "2161": "Jeu vidéo : Windows",
    "2162": "Jeu vidéo : Microsoft",
    "2163": "Jeu vidéo : Nintendo",
    "2164": "Jeu vidéo : Sony",
    "2165": "Jeu vidéo : Smartphone",
    "2166": "Jeu vidéo : Tablette",
    "2167": "Jeu vidéo : Autre",
    "2140": "eBook",
    "2151": "eBook : Audio",
    "2152": "eBook : Bds",
    "2153": "eBook : Comics",
    "2154": "eBook : Livres",
    "2155": "eBook : Mangas",
    "2156": "eBook : Presse",
    "2300": "Nulled",
    "2301": "Nulled : Wordpress",
    "2302": "Nulled : Scripts PHP &amp; CMS",
    "2303": "Nulled : Mobile",
    "2304": "Nulled : Divers",
    "2200": "Imprimante 3D",
    "2201": "Imprimante 3D : Objets",
    "2202": "Imprimante 3D : Personnages",
    "2141": "Emulation",
    "2157": "Emulation : Emulateurs",
    "2158": "Emulation : Roms",
    "2143": "GPS",
    "2168": "GPS : Applications",
    "2169": "GPS : Cartes",
    "2170": "GPS : Divers",
    "2188": "XXX",
    "2189": "XXX : Films",
    "2190": "XXX : Hentai",
    "2191": "XXX : Images",
    "2401": "XXX : Ebooks",
    "2402": "XXX : Jeux",
}


def load_or_create_api_key() -> str:
    os.makedirs(os.path.dirname(API_KEY_FILE), exist_ok=True)
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r") as f:
            return f.read().strip()
    api_key = secrets.token_hex(32)
    with open(API_KEY_FILE, "w") as f:
        f.write(api_key)
    logger.info(f"🔑 Clé API générée : {api_key}")
    return api_key


API_KEY = load_or_create_api_key()


def verify_api_key(apikey: str = Query(...)):
    if apikey != API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide")
    return apikey

CAT_TREE = {
    "2145": ["2178", "2179", "2180", "2181", "2182", "2183", "2184", "2185", "2186", "2187"],
    "2139": ["2147", "2148", "2149", "2150"],
    "2144": ["2171", "2172", "2173", "2174", "2175", "2176", "2177"],
    "2142": ["2159", "2160", "2161", "2162", "2163", "2164", "2165", "2166", "2167"],
    "2140": ["2151", "2152", "2153", "2154", "2155", "2156"],
    "2300": ["2301", "2302", "2303", "2304"],
    "2200": ["2201", "2202"],
    "2141": ["2157", "2158"],
    "2143": ["2168", "2169", "2170"],
    "2188": ["2189", "2190", "2191", "2401", "2402"],
}

def build_caps_xml() -> str:
    cats = ""
    for parent_id, children in CAT_TREE.items():
        parent_name = ALL_CATS[parent_id]
        subcats = ""
        for child_id in children:
            child_name = ALL_CATS[child_id]
            subcats += f'<subcat id="{child_id}" name="{child_name}"/>\n'
        cats += f'<category id="{parent_id}" name="{parent_name}">\n{subcats}</category>\n'

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<caps>
    ...
    <categories>
        {cats}
    </categories>
</caps>"""


def build_torznab_xml(torrents: list[dict]) -> str:
    items = ""
    for t in torrents:
        ygg_cat = str(t['category'] or "2183")
        magnet = t['download_url'].replace('&', '&amp;')
        name = t['name'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        items += f"""<item>
            <title>{name}</title>
            <guid>{t['id']}</guid>
            <link>{magnet}</link>
            <pubDate>{t['timestamp']}</pubDate>
            <torznab:attr name="seeders" value="{t['seeders']}"/>
            <torznab:attr name="leechers" value="{t['leechers']}"/>
            <torznab:attr name="size" value="{t['size']}"/>
            <torznab:attr name="category" value="{ygg_cat}"/>
        </item>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
    <channel>
        <title>PyGégé</title>
        <description>YGG Torrent Torznab API</description>
        {items}
    </channel>
</rss>"""


app = FastAPI(title="PyGégé - YGG Torznab API")


@app.get("/api")
async def torznab(
    t: str = Query(...),
    q: str = Query(""),
    cat: str = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    apikey: str = Depends(verify_api_key)
):
    logger.info(f"📥 t={t} q={q} cat={cat} limit={limit} offset={offset}")

    if t == "caps":
        return Response(content=build_caps_xml(), media_type="application/xml")

    if t in ("search", "tvsearch", "movie"):
        cats = cat.split(",") if cat else None
        results = await search(query=q, categories=cats, limit=limit)
        logger.info(f"🎯 {len(results)} résultats retournés")
        return Response(content=build_torznab_xml(results), media_type="application/xml")

    raise HTTPException(status_code=400, detail=f"Type inconnu : {t}")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)