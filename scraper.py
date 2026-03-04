# scraper.py
import asyncio
import json
import logging
import websockets
from urllib.parse import quote

logger = logging.getLogger(__name__)

RELAY_URL = "wss://relay.ygg.gratis/"
YGG_KIND = 2003


def _get_tag(tags: list, key: str) -> str | None:
    """Récupère la première valeur d'un tag par clé."""
    for tag in tags:
        if tag[0] == key:
            return tag[1]
    return None


def _get_tag_prefix(tags: list, prefix: str) -> str | None:
    """Récupère la valeur d'un tag 'l' qui commence par un préfixe."""
    for tag in tags:
        if tag[0] == "l" and tag[1].startswith(prefix):
            return tag[1].split(":")[1]
    return None

DEFAULT_TRACKERS = [
    "https://tracker.yggleak.top/announce",
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.demonii.com:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://exodus.desync.com:6969/announce",
    "https://torrent.tracker.durukanbal.com:443/announce",
    "udp://tracker1.myporn.club:9337/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.theoks.net:6969/announce",
    "udp://tracker.srv00.com:6969/announce",
    "udp://tracker.filemail.com:6969/announce",
    "udp://tracker.dler.org:6969/announce",
    "udp://tracker.corpscorp.online:80/announce",
    "udp://tracker.alaskantf.com:6969/announce",
    "udp://tracker-udp.gbitt.info:80/announce",
    "udp://t.overflow.biz:6969/announce",
    "udp://open.dstud.io:6969/announce",
    "udp://leet-tracker.moe:1337/announce",
    "udp://explodie.org:6969/announce",
    "udp://bittorrent-tracker.e-n-c-r-y-p-t.net:1337/announce",
    "udp://6ahddutb1ucc3cp.ru:6969/announce",
    "udp://94.23.207.177:6969/announce",
    "udp://37.59.48.81:6969/announce",
    "udp://54.36.179.216:6969/announce",
    "udp://193.42.111.57:9337/announce",
    "udp://43.250.54.137:6969/announce",
    "udp://91.216.110.53:451/announce",
    "udp://45.134.88.121:6969/announce",
    "udp://135.125.236.64:6969/announce",
    "udp://5.255.124.190:6969/announce",
    "udp://93.158.213.92:1337/announce",
    "udp://107.189.4.235:1337/announce",
    "udp://tracker.qu.ax:6969/announce",
    "udp://107.189.7.165:1337/announce",
    "udp://103.251.166.126:6969/announce",
    "udp://185.243.218.213:80/announce",
    "http://tracker.zhuqiy.com:80/announce",
    "udp://81.230.84.201:6969/announce",
    "udp://212.42.38.197:6969/announce",
    "http://193.31.26.113:6969/announce",
    "udp://176.99.7.59:6969/announce",
    "http://tr.nyacat.pw:80/announce",
]

def _parse_event(event: dict) -> dict | None:
    """Parse un événement Nostr YGG en dict torrent."""
    try:
        tags = event.get("tags", [])

        title = _get_tag(tags, "title")
        hash_x = _get_tag(tags, "x")
        size = int(_get_tag(tags, "size") or 0)
        category = _get_tag_prefix(tags, "u2p.cat:")

        # Si le tag u2p.seed est absent, on met 1 pour ne pas que Prowlarr rejette le torrent
        seeders = int(_get_tag_prefix(tags, "u2p.seed:") or 1)
        leechers = int(_get_tag_prefix(tags, "u2p.leech:") or 0)
        completed = int(_get_tag_prefix(tags, "u2p.completed:") or 0)

        # published_at = date réelle de sortie sur YGG, prioritaire sur created_at
        timestamp = int(_get_tag(tags, "published_at") or event.get("created_at", 0))

        if not title or not hash_x:
            return None

        # URL encode dn + trackers
        magnet = f"magnet:?xt=urn:btih:{hash_x}&dn={quote(title)}"
        for tr in DEFAULT_TRACKERS:
            magnet += f"&tr={quote(tr, safe='')}"

        return {
            "id": hash_x,
            "name": title,
            "size": size,
            "seeders": seeders,
            "leechers": leechers,
            "completed": completed,
            "timestamp": timestamp,
            "category": category,
            "download_url": magnet
        }

    except Exception as e:
        logger.warning(f"Erreur parsing event : {e}")
        return None


async def _search_async(query: str, category: str = None, limit: int = 50) -> list[dict]:
    """Recherche via WebSocket Nostr."""
    results = []

    filters = {
        "kinds": [YGG_KIND],
        "search": query,
        "limit": limit
    }
    if category:
        filters["#l"] = [f"u2p.cat:{category}"]

    try:
        async with websockets.connect(RELAY_URL) as ws:
            req = json.dumps(["REQ", "pygege-search", filters])
            await ws.send(req)
            logger.info(f"🔍 Recherche Nostr : {query}")

            async for message in ws:
                data = json.loads(message)

                if data[0] == "EOSE":
                    logger.info(f"✅ {len(results)} torrents trouvés")
                    break

                if data[0] == "EVENT":
                    torrent = _parse_event(data[2])
                    if torrent:
                        results.append(torrent)

    except Exception as e:
        logger.error(f"❌ Erreur WebSocket : {e}")

    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return results


CAT_PARENTS = {"2145", "2139", "2144", "2142", "2140", "2300", "2200", "2141", "2143", "2188"}

async def search(query: str, categories: list[str] = None, limit: int = 50) -> list[dict]:
    results = []

    l_filters = []
    if categories:
        for cat in categories:
            if cat in CAT_PARENTS:
                l_filters.append(f"u2p.pcat:{cat}")
            else:
                l_filters.append(f"u2p.cat:{cat}")

    filters = {"kinds": [YGG_KIND], "limit": limit}
    if query and query.strip():
        filters["search"] = query
    if l_filters:
        filters["#l"] = l_filters

    try:
        async with websockets.connect(RELAY_URL) as ws:
            req = json.dumps(["REQ", "pygege-search", filters])
            await ws.send(req)
            logger.info(f"🔍 Recherche Nostr : '{query}' cats={l_filters}")

            async for message in ws:
                data = json.loads(message)
                if data[0] == "EOSE":
                    logger.info(f"✅ {len(results)} torrents trouvés")
                    break
                if data[0] == "EVENT":
                    torrent = _parse_event(data[2])
                    if torrent:
                        results.append(torrent)

    except Exception as e:
        logger.error(f"❌ Erreur WebSocket : {e}")

    results.sort(key=lambda x: x["timestamp"], reverse=True)
    return results