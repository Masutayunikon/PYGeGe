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
    "2139": {"id": 2139, "name": "Audio"},
    "2147": {"id": 2147, "name": "Audio : Karaoké"},
    "2148": {"id": 2148, "name": "Audio : Musique"},
    "2150": {"id": 2150, "name": "Audio : Podcast Radio"},
    "2149": {"id": 2149, "name": "Audio : Samples"},
    "2144": {"id": 2144, "name": "Application"},
    "2177": {"id": 2177, "name": "Application : Autre"},
    "2176": {"id": 2176, "name": "Application : Formation"},
    "2171": {"id": 2171, "name": "Application : Linux"},
    "2172": {"id": 2172, "name": "Application : MacOS"},
    "2174": {"id": 2174, "name": "Application : Smartphone"},
    "2175": {"id": 2175, "name": "Application : Tablette"},
    "2173": {"id": 2173, "name": "Application : Windows"},
    "2142": {"id": 2142, "name": "Jeu vidéo"},
    "2167": {"id": 2167, "name": "Jeu vidéo : Autre"},
    "2159": {"id": 2159, "name": "Jeu vidéo : Linux"},
    "2160": {"id": 2160, "name": "Jeu vidéo : MacOS"},
    "2162": {"id": 2162, "name": "Jeu vidéo : Microsoft"},
    "2163": {"id": 2163, "name": "Jeu vidéo : Nintendo"},
    "2165": {"id": 2165, "name": "Jeu vidéo : Smartphone"},
    "2164": {"id": 2164, "name": "Jeu vidéo : Sony"},
    "2166": {"id": 2166, "name": "Jeu vidéo : Tablette"},
    "2161": {"id": 2161, "name": "Jeu vidéo : Windows"},
    "2140": {"id": 2140, "name": "eBook"},
    "2151": {"id": 2151, "name": "eBook : Audio"},
    "2152": {"id": 2152, "name": "eBook : Bds"},
    "2153": {"id": 2153, "name": "eBook : Comics"},
    "2154": {"id": 2154, "name": "eBook : Livres"},
    "2155": {"id": 2155, "name": "eBook : Mangas"},
    "2156": {"id": 2156, "name": "eBook : Presse"},
    "2300": {"id": 2300, "name": "Nulled"},
    "2301": {"id": 2301, "name": "Nulled : Wordpress"},
    "2302": {"id": 2302, "name": "Nulled : Scripts PHP & CMS"},
    "2303": {"id": 2303, "name": "Nulled : Mobile"},
    "2304": {"id": 2304, "name": "Nulled : Divers"},
    "2200": {"id": 2200, "name": "Imprimante 3D"},
    "2201": {"id": 2201, "name": "Imprimante 3D : Objets"},
    "2202": {"id": 2202, "name": "Imprimante 3D : Personnages"},
    "2141": {"id": 2141, "name": "Emulation"},
    "2157": {"id": 2157, "name": "Emulation : Emulateurs"},
    "2158": {"id": 2158, "name": "Emulation : Roms"},
    "2143": {"id": 2143, "name": "GPS"},
    "2168": {"id": 2168, "name": "GPS : Applications"},
    "2169": {"id": 2169, "name": "GPS : Cartes"},
    "2170": {"id": 2170, "name": "GPS : Divers"},
    "2188": {"id": 2188, "name": "XXX"},
    "2401": {"id": 2401, "name": "XXX : Ebooks"},
    "2189": {"id": 2189, "name": "XXX : Films"},
    "2190": {"id": 2190, "name": "XXX : Hentai"},
    "2191": {"id": 2191, "name": "XXX : Images"},
    "2402": {"id": 2402, "name": "XXX : Jeux"},
}

# Mapping Torznab -> liste de cats YGG correspondantes
TORZNAB_TO_YGG = {}
for ygg_id, data in CATEGORIES.items():
    torznab_id = str(data["id"])
    if torznab_id not in TORZNAB_TO_YGG:
        TORZNAB_TO_YGG[torznab_id] = []
    TORZNAB_TO_YGG[torznab_id].append(ygg_id)


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


# Mapping parent -> enfants
CAT_CHILDREN = {
    "2145": ["2178", "2179", "2180", "2181", "2182", "2183", "2184", "2185", "2186", "2187"],
    "2139": ["2147", "2148", "2150", "2149"],
    "2144": ["2177", "2176", "2171", "2172", "2174", "2175", "2173"],
    "2142": ["2167", "2159", "2160", "2162", "2163", "2165", "2164", "2166", "2161"],
    "2140": ["2151", "2152", "2153", "2154", "2155", "2156"],
    "2300": ["2301", "2302", "2303", "2304"],
    "2200": ["2201", "2202"],
    "2141": ["2157", "2158"],
    "2143": ["2168", "2169", "2170"],
    "2188": ["2401", "2189", "2190", "2191", "2402"],
}

def build_torznab_xml(torrents: list[dict], query: str = "", requested_cats: list[str] = None) -> str:
    # Expand les catégories parentes vers leurs enfants
    expanded_cats = set()
    if requested_cats:
        for cat in requested_cats:
            expanded_cats.add(cat)
            if cat in CAT_CHILDREN:
                expanded_cats.update(CAT_CHILDREN[cat])

    items = ""
    for t in torrents:
        ygg_cat = str(t['category'] or "2183")
        torznab_cat = CATEGORIES.get(ygg_cat, {}).get("id", ygg_cat)

        if expanded_cats and str(ygg_cat) not in expanded_cats:
            continue
        ...
        ...

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
            <torznab:attr name="category" value="{torznab_cat}"/>
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
    seen = set()
    for cat in CATEGORIES.values():
        key = f"{cat['id']}-{cat['name']}"
        if key not in seen:
            seen.add(key)
            name = cat['name'].replace('&', '&amp;')
            cats += f'<category id="{cat["id"]}" name="{name}"/>\n'

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<caps>
    <server title="PyGégé"/>
    <searching>
        <search available="yes" supportedParams="q,cat"/>
        <tv-search available="yes" supportedParams="q,season,ep,cat"/>
        <movie-search available="yes" supportedParams="q,cat"/>
        <music-search available="yes" supportedParams="q,cat"/>
        <book-search available="yes" supportedParams="q,cat"/>
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
    logger.info(f"📥 Requête : t={t} q={q} cat={cat}")

    if t == "caps":
        return Response(content=build_caps_xml(), media_type="application/xml")

    if t == "search" or t == "tvsearch" or t == "movie":
        requested_cats = cat.split(",") if cat else None
        results = await search(query=q)
        return Response(content=build_torznab_xml(results, q, requested_cats), media_type="application/xml")

    raise HTTPException(status_code=400, detail=f"Type inconnu : {t}")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)