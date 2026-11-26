from services.http_client import build_session
from services.normalizer import normalize_jikan_anime

class JikanCompatibleProvider:
    """Optional adapter for a Jikan-shaped REST API endpoint you operate or trust."""
    name = "jikan-compatible"

    def __init__(self, base_url="", timeout=15):
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = (3, timeout)
        self.session = build_session("AnimeX/2.0 (metadata fallback)")

    @property
    def is_configured(self):
        return bool(self.base_url)

    def _get(self, path, params=None):
        if not self.is_configured:
            raise RuntimeError("No Jikan-compatible API endpoint configured.")
        try:
            response = self.session.get(f"{self.base_url}{path}", params=params or {}, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            raise RuntimeError("Fallback metadata request failed.") from exc

    def collection(self, name, page=1, genre=None):
        paths = {
            "trending": ("/top/anime", {"filter": "airing"}),
            "popular": ("/top/anime", {"filter": "bypopularity"}),
            "top-rated": ("/top/anime", {"filter": "favorite"}),
            "upcoming": ("/seasons/upcoming", {}),
        }
        path, params = paths[name]
        params.update({"page": page, "sfw": "true"})
        if genre:
            params["q"] = genre
        payload = self._get(path, params)
        return {"provider": self.name, "collection": name,
                "results": [normalize_jikan_anime(x) for x in payload.get("data", [])]}

    def search(self, term, page=1):
        payload = self._get("/anime", {"q": term, "page": page, "sfw": "true"})
        return {"provider": self.name, "results": [normalize_jikan_anime(x) for x in payload.get("data", [])]}

    def detail(self, anime_id):
        payload = self._get(f"/anime/{anime_id}/full")
        item = payload.get("data")
        return normalize_jikan_anime(item, detailed=True) if item else None
