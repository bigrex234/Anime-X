from services.normalizer import normalize_anilist_media, normalize_jikan_anime

def test_anilist_normalizer():
    item = {
        "id": 1,
        "title": {"english": "Example", "romaji": "Example"},
        "coverImage": {"large": "https://example.com/image.jpg"},
        "genres": ["Action"],
        "averageScore": 85,
    }
    result = normalize_anilist_media(item)
    assert result["id"] == 1
    assert result["title"] == "Example"
    assert result["score"] == 85

def test_jikan_normalizer():
    item = {
        "mal_id": 2,
        "title": "Example",
        "images": {"jpg": {"image_url": "https://example.com/image.jpg"}},
        "genres": [{"name": "Drama"}],
    }
    result = normalize_jikan_anime(item)
    assert result["id"] == 2
    assert result["genres"] == ["Drama"]
