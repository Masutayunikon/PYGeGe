<div align="center">

# PyGégé

_Un indexeur Torznab léger pour [ygg.gratis](https://ygg.gratis) — construit sur Nostr NIP-35._

![Version](https://img.shields.io/github/v/tag/Masutayunikon/PYGeGe?label=version&color=blue&logo=github)
![Image Size](https://img.shields.io/docker/image-size/masutayunikon/pygege/latest?color=%2348b620&label=image+size)

[Fonctionnalités](#fonctionnalités) • [Installation](#installation) • [Configuration Prowlarr](#configuration-prowlarr) • [Catégories](#catégories)

</div>

---

Se connecte au relai Nostr `wss://relay.ygg.gratis/`, récupère les métadonnées de torrents NIP-35 et les expose via une API Torznab compatible Prowlarr, Sonarr et Radarr.

## Fonctionnalités

- API Torznab conforme (`t=caps`, `t=search`, `t=tvsearch`, `t=movie`)
- Recherche plein texte avec filtrage par catégorie
- Liens magnet avec trackers pré-configurés
- Tri chronologique (plus récent en premier)
- Clé API auto-générée au premier lancement
- Image Docker multi-arch sur Docker Hub

## Installation

```yaml
services:
  pygege:
    image: masutayunikon/pygege:latest
    container_name: pygege
    volumes:
      - ./data:/app/data
    ports:
      - "8000:8000"
    restart: unless-stopped
```

```bash
docker compose up -d
```

Au premier lancement, une clé API est générée dans `./data/api_key.txt` :

```bash
cat ./data/api_key.txt
```

## Configuration Prowlarr

1. **Indexers** → **Add Indexer** → **Generic Torznab**
2. Remplir les champs :
   - **Name** : `PyGégé`
   - **URL** : `http://<ip>:8000`
   - **API Path** : `/api`
   - **API Key** : le contenu de `api_key.txt`
3. **Test** → **Save**

## Catégories

| Torznab | YGG | Description |
|---------|-----|-------------|
| 2000+ | 2145 | Films |
| 5000+ | 2145 | Séries TV |
| 3000+ | 2139 | Audio |
| 4000+ | 2144 | Logiciels |
| 7000+ | 2140 | Livres |
| 6000+ | 2188 | XXX |
| 8000+ | 2300 | Autres |

## Build depuis les sources

```bash
docker build -t pygege .
docker run -p 8000:8000 -v ./data:/app/data pygege
```

## Stack

- Python 3.12 / FastAPI / Uvicorn
- WebSocket Nostr (NIP-35, NIP-50)
- Relai : `wss://relay.ygg.gratis/`
