import requests

class AniListExtras:
    def __init__(self, endpoint, timeout=15):
        self.endpoint = endpoint
        self.timeout = timeout

    def _query(self, query, variables):
        response = requests.post(
            self.endpoint,
            json={"query": query, "variables": variables},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("errors"):
            raise RuntimeError(data["errors"][0].get("message", "AniList API error"))
        return data.get("data") or {}

    def airing(self, anime_id):
        query = """
        query ($id: Int) {
          Media(id: $id, type: ANIME) {
            id title { english romaji }
            airingSchedule(notYetAired: false, page: 1, perPage: 20) {
              nodes { airingAt timeUntilAiring episode }
            }
          }
        }
        """
        data = self._query(query, {"id": anime_id}).get("Media") or {}
        return {
            "anime_id": anime_id,
            "title": (data.get("title") or {}).get("english") or (data.get("title") or {}).get("romaji"),
            "episodes": (data.get("airingSchedule") or {}).get("nodes") or [],
        }

    def seasonal(self, year=None, season=None, page=1):
        from datetime import datetime
        now = datetime.utcnow()
        year = year or now.year
        season = season or ("WINTER" if now.month in (1, 2, 3) else "SPRING" if now.month in (4, 5, 6) else "SUMMER" if now.month in (7, 8, 9) else "FALL")
        query = """
        query ($page: Int, $year: Int, $season: MediaSeason) {
          Page(page: $page, perPage: 24) {
            media(type: ANIME, seasonYear: $year, season: $season, sort: POPULARITY_DESC, isAdult: false) {
              id idMal title { english romaji } coverImage { large }
              averageScore episodes status seasonYear season format genres siteUrl
            }
          }
        }
        """
        data = self._query(query, {"page": page, "year": int(year), "season": season})
        return (data.get("Page") or {}).get("media") or []
