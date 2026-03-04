# main.py
import asyncio
import logging
import re
import secrets
import os
import httpx
from fastapi import FastAPI, Query, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, Response
from scraper import search
from email.utils import formatdate

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
MIN_RESULTS_THRESHOLD = 50

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY_FILE = "/app/data/api_key.txt"

YGG_TO_TORZNAB = {
    "2183": "2040", "2178": "2040", "2180": "2040",
    "2184": "5040", "2179": "5070", "2181": "5080",
    "2182": "5000", "2185": "5000", "2186": "5060", "2187": "5000",
    "2148": "3010", "2147": "3010", "2150": "3010", "2149": "3010", "2139": "3000",
    "2151": "3030",
    "2144": "4000", "2173": "4010", "2171": "4020", "2172": "4030",
    "2174": "4070", "2175": "4070", "2176": "4000", "2177": "4000",
    "2142": "4050", "2159": "4050", "2160": "4050", "2161": "4050",
    "2162": "1040", "2163": "1030", "2164": "1080",
    "2165": "4070", "2166": "4070", "2167": "1090",
    "2140": "7000", "2154": "7020", "2152": "7020", "2153": "7030",
    "2155": "7030", "2156": "7010",
    "2188": "6000", "2189": "6000", "2190": "6000", "2191": "6060",
    "2401": "7020", "2402": "6000",
    "2300": "8000", "2301": "8000", "2302": "8000", "2303": "8000", "2304": "8000",
    "2141": "8000", "2157": "8000", "2158": "8000",
    "2143": "8000", "2168": "8000", "2169": "8000", "2170": "8000",
    "2200": "8000", "2201": "8000", "2202": "8000",
}

TORZNAB_TO_YGG_PCAT = {
    "2000": "2145", "2010": "2145", "2020": "2145", "2030": "2145",
    "2040": "2145", "2045": "2145", "2050": "2145", "2060": "2145",
    "2070": "2145", "2080": "2145",
    "5000": "2145", "5010": "2145", "5020": "2145", "5030": "2145",
    "5040": "2145", "5045": "2145", "5050": "2145", "5060": "2145",
    "5070": "2145", "5080": "2145",
    "3000": "2139", "3010": "2139", "3020": "2139", "3030": "2139",
    "3040": "2139", "3050": "2139", "3060": "2139",
    "4000": "2144", "4010": "2144", "4020": "2144", "4030": "2144",
    "4040": "2144", "4050": "2142", "4060": "2144", "4070": "2144",
    "1000": "2142", "1010": "2142", "1020": "2142", "1030": "2142",
    "1040": "2142", "1050": "2142", "1060": "2142", "1070": "2142",
    "1080": "2142", "1090": "2142",
    "7000": "2140", "7010": "2140", "7020": "2140", "7030": "2140",
    "7040": "2140", "7050": "2140", "7060": "2140",
    "6000": "2188", "6010": "2188", "6020": "2188", "6030": "2188",
    "6040": "2188", "6045": "2188", "6050": "2188", "6060": "2188",
    "6070": "2188", "6080": "2188", "6090": "2188",
    "8000": "2300", "8010": "2300", "8020": "2300",
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


async def get_french_title_by_id(imdbid: str = None, tmdbid: str = None) -> str | None:
    if not TMDB_API_KEY:
        return None
    try:
        async with httpx.AsyncClient() as client:
            if imdbid:
                r = await client.get(
                    f"https://api.themoviedb.org/3/find/{imdbid}",
                    params={"api_key": TMDB_API_KEY, "external_source": "imdb_id"}
                )
                data = r.json()
                results = data.get("movie_results") or data.get("tv_results") or []
                if not results:
                    return None
                tmdbid = results[0]["id"]

            if tmdbid:
                r = await client.get(
                    f"https://api.themoviedb.org/3/movie/{tmdbid}",
                    params={"api_key": TMDB_API_KEY, "language": "fr-FR"}
                )
                data = r.json()
                return data.get("title") or data.get("name")
    except Exception as e:
        logger.warning(f"⚠️ TMDB id error: {e}")
    return None


async def get_french_title_by_query(query: str) -> str | None:
    if not TMDB_API_KEY:
        return None
    # Retire l'année si présente ex: "Howls Moving Castle 2004" -> "Howls Moving Castle"
    clean_query = re.sub(r'\s+\d{4}$', '', query.strip())
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://api.themoviedb.org/3/search/multi",
                params={"api_key": TMDB_API_KEY, "query": clean_query, "language": "fr-FR"}
            )
            data = r.json()
            results = data.get("results", [])
            if not results:
                return None
            title = results[0].get("title") or results[0].get("name")
            if title and title.lower() != clean_query.lower():
                return title
    except Exception as e:
        logger.warning(f"⚠️ TMDB query error: {e}")
    return None


def build_caps_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<caps>
    <server title="PyGégé"/>
    <searching>
        <search available="yes" supportedParams="q,cat,imdbid,tmdbid"/>
        <tv-search available="yes" supportedParams="q,season,ep,cat,imdbid,tmdbid"/>
        <movie-search available="yes" supportedParams="q,cat,imdbid,tmdbid"/>
        <music-search available="yes" supportedParams="q,cat"/>
        <book-search available="yes" supportedParams="q,cat"/>
    </searching>
    <categories>
        <category id="2000" name="Movies">
            <subcat id="2040" name="Movies/HD"/>
            <subcat id="2045" name="Movies/UHD"/>
            <subcat id="2050" name="Movies/BluRay"/>
            <subcat id="2080" name="Movies/WEB-DL"/>
        </category>
        <category id="5000" name="TV">
            <subcat id="5040" name="TV/HD"/>
            <subcat id="5045" name="TV/UHD"/>
            <subcat id="5070" name="TV/Anime"/>
            <subcat id="5080" name="TV/Documentary"/>
            <subcat id="5060" name="TV/Sport"/>
        </category>
        <category id="3000" name="Audio">
            <subcat id="3010" name="Audio/MP3"/>
            <subcat id="3030" name="Audio/Audiobook"/>
        </category>
        <category id="4000" name="PC">
            <subcat id="4010" name="PC/0day"/>
            <subcat id="4020" name="PC/ISO"/>
            <subcat id="4030" name="PC/Mac"/>
            <subcat id="4070" name="PC/Mobile-Android"/>
        </category>
        <category id="4050" name="PC/Games">
            <subcat id="1030" name="Console/Wii"/>
            <subcat id="1040" name="Console/XBox"/>
            <subcat id="1080" name="Console/PS3"/>
            <subcat id="1090" name="Console/Other"/>
        </category>
        <category id="7000" name="Books">
            <subcat id="7010" name="Books/Mags"/>
            <subcat id="7020" name="Books/EBook"/>
            <subcat id="7030" name="Books/Comics"/>
        </category>
        <category id="6000" name="XXX">
            <subcat id="6060" name="XXX/ImageSet"/>
        </category>
        <category id="8000" name="Other">
            <subcat id="8010" name="Other/Misc"/>
        </category>
    </categories>
</caps>"""


def build_torznab_xml(torrents: list[dict]) -> str:
    items = ""
    for t in torrents:
        ygg_cat = str(t['category'] or "2183")
        torznab_cat = YGG_TO_TORZNAB.get(ygg_cat, "8000")
        magnet = t['download_url'].replace('&', '&amp;')

        name = t['name']
        name = name.encode('utf-8', errors='replace').decode('utf-8')
        name = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

        ts = int(t.get("timestamp") or 0)
        pubdate = formatdate(ts, usegmt=True)

        items += f"""<item>
            <title>{name}</title>
            <guid>{t['id']}</guid>
            <link>{magnet}</link>
            <pubDate>{pubdate}</pubDate>
            <size>{t['size']}</size>
            <enclosure url="{magnet}" length="{t['size']}" type="application/x-bittorrent"/>
            <category>{torznab_cat}</category>
            <torznab:attr name="category" value="{torznab_cat}"/>
            <torznab:attr name="seeders" value="{t['seeders']}"/>
            <torznab:attr name="leechers" value="{t['leechers']}"/>
            <torznab:attr name="size" value="{t['size']}"/>
            <torznab:attr name="downloadvolumefactor" value="0"/>
            <torznab:attr name="uploadvolumefactor" value="1"/>
        </item>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:torznab="http://torznab.com/schemas/2015/feed">
    <channel>
        <atom:link href="" rel="self" type="application/rss+xml"/>
        <title>PyGégé</title>
        <description>YGG Torrent via Nostr</description>
        {items}
    </channel>
</rss>"""


app = FastAPI(title="PyGégé - YGG Torznab API")


@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>PyGeGe - Service en ligne</title>
  <style>
    :root {
      color-scheme: light;
      font-family: Arial, sans-serif;
    }
    body {
      margin: 0;
      background: #f4f6f8;
      color: #1f2937;
    }
    .wrap {
      max-width: 720px;
      margin: 8vh auto;
      background: #ffffff;
      border: 1px solid #d1d5db;
      border-radius: 10px;
      padding: 24px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
    }
    h1 {
      margin-top: 0;
      font-size: 1.4rem;
    }
    p {
      line-height: 1.5;
    }
    .tips {
      margin-top: 16px;
      padding: 12px;
      border-left: 4px solid #2563eb;
      background: #eff6ff;
      border-radius: 6px;
    }
    a {
      color: #1d4ed8;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
  </style>
</head>
<body>
  <main class="wrap">
    <h1>Si vous voyez ceci, Pygege est en ligne ! .</h1>
    <p>
      Lien documentation :
      <a href="https://github.com/Masutayunikon/PYGeGe" target="_blank" rel="noopener noreferrer">
        https://github.com/Masutayunikon/PYGeGe
      </a>
    </p>
    <div class="tips">
      <strong>Tips :</strong>
      Si Prowlarr n'arrive pas a s'y connecter, verifiez que vous avez mis
      <code>http</code> et pas <code>https</code> (pas mettre le <code>s</code>).
    </div>
  </main>
</body>
</html>"""


@app.get("/api")
async def torznab(
    request: Request,
    t: str = Query(...),
    q: str = Query(""),
    cat: str = Query(None),
    imdbid: str = Query(None),
    tmdbid: str = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    apikey: str = Depends(verify_api_key)
):
    url = str(request.url)
    url = re.sub(r"apikey=[^&]+", "apikey=***", url)
    logger.info(f"📥 URL: {url}")

    if t == "caps":
        return Response(content=build_caps_xml(), media_type="application/xml")

    if t in ("search", "tvsearch", "movie"):
        ygg_pcats = []
        if cat:
            seen = set()
            for c in cat.split(","):
                pcat = TORZNAB_TO_YGG_PCAT.get(c)
                if pcat and pcat not in seen:
                    ygg_pcats.append(pcat)
                    seen.add(pcat)

        cats = ygg_pcats if ygg_pcats else None

        # Cherche le titre français
        french_title = None
        if TMDB_API_KEY:
            if imdbid or tmdbid:
                french_title = await get_french_title_by_id(imdbid=imdbid, tmdbid=tmdbid)
            if not french_title and q:
                french_title = await get_french_title_by_query(q)
            if french_title and french_title.lower() == re.sub(r'\s+\d{4}$', '', q.strip()).lower():
                french_title = None  # Déjà en français

        if french_title:
            logger.info(f"🇫🇷 Titre français : {french_title} (VO: {q})")
            results = await search(query=french_title, categories=cats, limit=limit + offset)

            if len(results) < MIN_RESULTS_THRESHOLD and q:
                logger.info(f"🔍 {len(results)} résultats FR, recherche VO aussi...")
                results_vo = await search(query=q, categories=cats, limit=limit + offset)
                seen_ids = {r['id'] for r in results}
                for r in results_vo:
                    if r['id'] not in seen_ids:
                        results.append(r)
        else:
            results = await search(query=q, categories=cats, limit=limit + offset)

        page = results[offset:offset + limit]
        logger.info(f"🎯 {len(page)} résultats retournés (offset={offset})")
        return Response(
            content=build_torznab_xml(page).encode("utf-8"),
            media_type="application/xml; charset=utf-8"
        )

    raise HTTPException(status_code=400, detail=f"Type inconnu : {t}")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    #log imbtv is active
    logger.info("🚀 Démarrage de PyGégé...")
    logger.info(f"🔑 Clé IMDB TV : {'✅' if TMDB_API_KEY else '❌'}")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
