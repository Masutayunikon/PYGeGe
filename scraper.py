# scraper.py
import asyncio
import json
import logging
import websockets

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


def _parse_event(event: dict) -> dict | None:
    """Parse un événement Nostr YGG en dict torrent."""
    try:
        tags = event.get("tags", [])

        title = _get_tag(tags, "title")
        hash_x = _get_tag(tags, "x")
        size = int(_get_tag(tags, "size") or 0)
        category = _get_tag_prefix(tags, "u2p.cat:")
        seeders = int((_get_tag_prefix(tags, "u2p.seed:") or 0))

        if not title or not hash_x:
            return None

        magnet = f"magnet:?xt=urn:btih:{hash_x}&dn={title}"

        return {
            "id": event.get("id"),
            "name": title,
            "size": size,
            "seeders": seeders,
            "leechers": 0,
            "timestamp": event.get("created_at", 0),
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

    return results


async def search(query: str, category: str = None, limit: int = 50) -> list[dict]:
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

    return results
