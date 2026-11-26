def normalize_anilist_media(item, detailed=False):
    title = item.get("title") or {}
    cover = item.get("coverImage") or {}
    result = {
        "id": item.get("id"),
        "mal_id": item.get("idMal"),
        "title": title.get("english") or title.get("romaji") or title.get("native") or "Untitled",
        "title_romaji": title.get("romaji"),
        "title_native": title.get("native"),
        "synopsis": item.get("description"),
        "image": cover.get("extraLarge") or cover.get("large"),
        "banner": item.get("bannerImage"),
        "score": item.get("averageScore"),
        "episodes": item.get("episodes"),
        "status": item.get("status"),
        "season": item.get("season"),
        "season_year": item.get("seasonYear"),
        "genres": item.get("genres") or [],
        "format": item.get("format"),
        "source_url": item.get("siteUrl"),
    }
    if detailed:
        studios = (item.get("studios") or {}).get("nodes", [])
        result.update({
            "duration": item.get("duration"),
            "studios": [x.get("name") for x in studios],
            "trailer": item.get("trailer"),
        })
    return result

def normalize_jikan_anime(item, detailed=False):
    images = item.get("images") or {}
    jpg = images.get("jpg") or {}
    result = {
        "id": item.get("mal_id"),
        "mal_id": item.get("mal_id"),
        "title": item.get("title_english") or item.get("title") or "Untitled",
        "title_romaji": item.get("title"),
        "title_native": None,
        "synopsis": item.get("synopsis"),
        "image": jpg.get("large_image_url") or jpg.get("image_url"),
        "banner": None,
        "score": round(item["score"] * 10) if item.get("score") else None,
        "episodes": item.get("episodes"),
        "status": item.get("status"),
        "season": item.get("season"),
        "season_year": item.get("year"),
        "genres": [g.get("name") for g in item.get("genres", [])],
        "format": item.get("type"),
        "source_url": item.get("url"),
    }
    if detailed:
        result.update({
            "duration": item.get("duration"),
            "studios": [x.get("name") for x in item.get("studios", [])],
            "trailer": item.get("trailer"),
        })
    return result
