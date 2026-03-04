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

YGG_PARENT = {
    "2178": "2145", "2179": "2145", "2180": "2145", "2181": "2145",
    "2182": "2145", "2183": "2145", "2184": "2145", "2185": "2145",
    "2186": "2145", "2187": "2145",
    "2147": "2139", "2148": "2139", "2149": "2139", "2150": "2139",
    "2171": "2144", "2172": "2144", "2173": "2144", "2174": "2144",
    "2175": "2144", "2176": "2144", "2177": "2144",
    "2159": "2142", "2160": "2142", "2161": "2142", "2162": "2142",
    "2163": "2142", "2164": "2142", "2165": "2142", "2166": "2142", "2167": "2142",
    "2151": "2140", "2152": "2140", "2153": "2140", "2154": "2140",
    "2155": "2140", "2156": "2140",
}

YGG_TO_TORZNAB = {
    "2183": "2000", "2178": "2000", "2180": "2000",
    "2145": "5000", "2184": "5000", "2182": "5000", "2185": "5000",
    "2179": "5070", "2181": "5080", "2186": "5060", "2187": "5000",
    "2139": "3000", "2148": "3000", "2147": "3000", "2150": "3000", "2149": "3000",
    "2151": "3010",
    "2144": "4000", "2176": "4000", "2177": "4050", "2173": "4050",
    "2171": "4070", "2172": "4030", "2174": "4040", "2175": "4040",
    "2142": "1000", "2159": "1000", "2160": "1000", "2161": "1000",
    "2162": "1040", "2163": "1030", "2164": "1080",
    "2165": "4040", "2166": "4040", "2167": "1000",
    "2140": "7000", "2154": "7020", "2152": "7000", "2153": "7030",
    "2155": "7030", "2156": "7010",
    "2300": "8000", "2301": "8000", "2302": "8000", "2303": "8000", "2304": "8000",
    "2141": "8000", "2157": "8000", "2158": "8000",
    "2143": "8000", "2168": "8000", "2169": "8000", "2170": "8000",
    "2200": "8000", "2201": "8000", "2202": "8000",
    "2188": "6000", "2189": "6000", "2190": "6000", "2191": "6010",
    "2401": "6000", "2402": "6000",
}

def build_caps_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
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
        <category id="2000" name="Movies">
            <subcat id="2183" name="Film/Vidéo : Film"/>
            <subcat id="2178" name="Film/Vidéo : Animation"/>
            <subcat id="2180" name="Film/Vidéo : Concert"/>
        </category>
        <category id="5000" name="TV">
            <subcat id="2145" name="Film/Vidéo"/>
            <subcat id="2184" name="Film/Vidéo : Série TV"/>
            <subcat id="2182" name="Film/Vidéo : Emission TV"/>
            <subcat id="2185" name="Film/Vidéo : Spectacle"/>
            <subcat id="2179" name="Film/Vidéo : Animation Série"/>
        </category>
        <category id="5060" name="TV/Sport">
            <subcat id="2186" name="Film/Vidéo : Sport"/>
        </category>
        <category id="5080" name="TV/Documentary">
            <subcat id="2181" name="Film/Vidéo : Documentaire"/>
        </category>
        <category id="5070" name="TV/Anime">
            <subcat id="2179" name="Film/Vidéo : Animation Série"/>
        </category>
        <category id="3000" name="Audio">
            <subcat id="2139" name="Audio"/>
            <subcat id="2148" name="Audio : Musique"/>
            <subcat id="2147" name="Audio : Karaoké"/>
            <subcat id="2150" name="Audio : Podcast Radio"/>
            <subcat id="2149" name="Audio : Samples"/>
        </category>
        <category id="3010" name="Audio/Audiobook">
            <subcat id="2151" name="eBook : Audio"/>
        </category>
        <category id="4000" name="PC">
            <subcat id="2144" name="Application"/>
            <subcat id="2176" name="Application : Formation"/>
        </category>
        <category id="4050" name="PC/0day">
            <subcat id="2173" name="Application : Windows"/>
            <subcat id="2177" name="Application : Autre"/>
        </category>
        <category id="4070" name="PC/ISO">
            <subcat id="2171" name="Application : Linux"/>
        </category>
        <category id="4030" name="PC/Mac">
            <subcat id="2172" name="Application : MacOS"/>
        </category>
        <category id="4040" name="PC/Mobile-Android">
            <subcat id="2174" name="Application : Smartphone"/>
            <subcat id="2175" name="Application : Tablette"/>
        </category>
        <category id="1000" name="PC/Games">
            <subcat id="2142" name="Jeu vidéo"/>
            <subcat id="2159" name="Jeu vidéo : Linux"/>
            <subcat id="2160" name="Jeu vidéo : MacOS"/>
            <subcat id="2161" name="Jeu vidéo : Windows"/>
        </category>
        <category id="1040" name="Console/XBox One">
            <subcat id="2162" name="Jeu vidéo : Microsoft"/>
        </category>
        <category id="1030" name="Console/Wii">
            <subcat id="2163" name="Jeu vidéo : Nintendo"/>
        </category>
        <category id="1080" name="Console/PS4">
            <subcat id="2164" name="Jeu vidéo : Sony"/>
        </category>
        <category id="7000" name="Books">
            <subcat id="2140" name="eBook"/>
            <subcat id="2154" name="eBook : Livres"/>
            <subcat id="2152" name="eBook : Bds"/>
        </category>
        <category id="7020" name="Books/EBook">
            <subcat id="2154" name="eBook : Livres"/>
        </category>
        <category id="7030" name="Books/Comics">
            <subcat id="2153" name="eBook : Comics"/>
            <subcat id="2155" name="eBook : Mangas"/>
        </category>
        <category id="7010" name="Books/Mags">
            <subcat id="2156" name="eBook : Presse"/>
        </category>
        <category id="8000" name="Other">
            <subcat id="2300" name="Nulled"/>
            <subcat id="2141" name="Emulation"/>
            <subcat id="2143" name="GPS"/>
            <subcat id="2200" name="Imprimante 3D"/>
        </category>
        <category id="6000" name="XXX">
            <subcat id="2188" name="XXX"/>
            <subcat id="2189" name="XXX : Films"/>
            <subcat id="2190" name="XXX : Hentai"/>
            <subcat id="2191" name="XXX : Images"/>
        </category>
    </categories>
</caps>"""


def build_torznab_xml(torrents: list[dict]) -> str:
    items = ""
    for t in torrents:
        ygg_cat = str(t['category'] or "2183")
        torznab_cat = YGG_TO_TORZNAB.get(ygg_cat, "8000")

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