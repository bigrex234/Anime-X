import requests
from services.normalizer import normalize_anilist_media

MEDIA_FIELDS = """
id idMal
title { romaji english native }
description(asHtml: false)
coverImage { large extraLarge }
bannerImage
averageScore
episodes
status
season
seasonYear
genres
format
siteUrl
"""

COLLECTION_QUERY = f"""
query ($page: Int, $sort: [MediaSort], $genre: String, $status: MediaStatus) {{
  Page(page: $page, perPage: 18) {{
    media(type: ANIME, sort: $sort, genre: $genre, status: $status, isAdult: false) {{
      {MEDIA_FIELDS}
    }}
  }}
}}
"""

SEARCH_QUERY = f"""
query ($page: Int, $search: String) {{
  Page(page: $page, perPage: 18) {{
    media(type: ANIME, search: $search, sort: SEARCH_MATCH, isAdult: false) {{
      {MEDIA_FIELDS}
    }}
  }}
}}
"""

DETAIL_QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id idMal
    title { romaji english native }
    description(asHtml: false)
    coverImage { large extraLarge }
    bannerImage
    averageScore
    episodes
    status
    season
    seasonYear
    genres
    format
    duration
    startDate { year month day }
    endDate { year month day }
    studios(isMain: true) { nodes { name } }
    trailer { id site }
    siteUrl
    recommendations(perPage: 8, sort: RATING_DESC) {
      nodes {
        mediaRecommendation {
          id
          title { romaji english }
          coverImage { large }
          averageScore
          episodes
          seasonYear
          format
        }
      }
    }
  }
}
"""

class AniListProvider:
    name = "anilist"

    def __init__(self, endpoint, timeout=15):
        self.endpoint = endpoint
        self.timeout = timeout

    def _graphql(self, query, variables=None):
        response = requests.post(
            self.endpoint,
            json={"query": query, "variables": variables or {}},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(payload["errors"][0].get("message", "AniList API error"))
        return payload.get("data") or {}

    def collection(self, name, page=1, genre=None):
        sort_map = {
            "trending": ["TRENDING_DESC"],
            "popular": ["POPULARITY_DESC"],
            "top-rated": ["SCORE_DESC"],
            "upcoming": ["POPULARITY_DESC"],
        }
        variables = {
            "page": page,
            "sort": sort_map[name],
            "genre": genre,
            "status": "NOT_YET_RELEASED" if name == "upcoming" else None,
        }
        data = self._graphql(COLLECTION_QUERY, variables)
        media = (data.get("Page") or {}).get("media") or []
        return {"provider": self.name, "collection": name,
                "results": [normalize_anilist_media(x) for x in media]}

    def search(self, term, page=1):
        data = self._graphql(SEARCH_QUERY, {"page": page, "search": term})
        media = (data.get("Page") or {}).get("media") or []
        return {"provider": self.name, "results": [normalize_anilist_media(x) for x in media]}

    def detail(self, anime_id):
        data = self._graphql(DETAIL_QUERY, {"id": anime_id})
        media = data.get("Media")
        if not media:
            return None
        result = normalize_anilist_media(media, detailed=True)
        result["recommendations"] = []
        recs = (media.get("recommendations") or {}).get("nodes") or []
        for node in recs:
            recommended = node.get("mediaRecommendation")
            if recommended:
                result["recommendations"].append(normalize_anilist_media(recommended))
        result["start_date"] = media.get("startDate")
        result["end_date"] = media.get("endDate")
        return result
