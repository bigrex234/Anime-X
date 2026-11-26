class AnimeService:
    """Provider orchestration. AniList is primary; optional compatible fallback."""

    def __init__(self, primary, fallback=None):
        self.primary = primary
        self.fallback = fallback

    def _run(self, method, *args, **kwargs):
        try:
            return getattr(self.primary, method)(*args, **kwargs)
        except Exception:
            if self.fallback and self.fallback.is_configured:
                return getattr(self.fallback, method)(*args, **kwargs)
            raise

    def collection(self, name, page=1, genre=None):
        return self._run("collection", name, page=page, genre=genre)

    def search(self, term, page=1):
        return self._run("search", term=term, page=page)

    def detail(self, anime_id):
        return self._run("detail", anime_id=anime_id)
