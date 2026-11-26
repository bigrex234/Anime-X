from functools import wraps

from flask import Flask, g, jsonify, render_template, request

from config import Config
from services.anilist_extras import AniListExtras
from services.anime_service import AnimeService
from services.normalizer import normalize_anilist_media
from services.providers.anilist import AniListProvider
from services.providers.jikan_compatible import JikanCompatibleProvider
from services.supabase_service import SupabaseService

COLLECTIONS = {"trending", "popular", "top-rated", "upcoming"}
SEASONS = {"WINTER", "SPRING", "SUMMER", "FALL"}
WATCH_STATUSES = {"watching", "completed", "on_hold", "dropped", "plan_to_watch"}
GENRES = [
    "Action", "Adventure", "Comedy", "Drama", "Fantasy", "Horror",
    "Mystery", "Romance", "Sci-Fi", "Slice of Life", "Sports", "Supernatural",
]
MAX_PAGE = 20
MAX_SEARCH_LENGTH = 100


def is_valid_int(value, minimum=0, maximum=None):
    """True for real ints only (bool is a subclass of int, so exclude it)."""
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    if value < minimum:
        return False
    return maximum is None or value <= maximum


def page_arg():
    return max(1, min(request.args.get("page", 1, type=int), MAX_PAGE))


def cached_json(payload, seconds=300, status=200):
    """JSON response that Vercel's edge / browsers may cache briefly."""
    response = jsonify(payload)
    response.status_code = status
    response.headers["Cache-Control"] = (
        f"public, max-age=60, s-maxage={seconds}, stale-while-revalidate={seconds * 2}"
    )
    return response


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    primary = AniListProvider(app.config["ANILIST_GRAPHQL_URL"], app.config["API_TIMEOUT"])
    fallback = JikanCompatibleProvider(
        app.config.get("JIKAN_COMPATIBLE_BASE_URL", ""),
        app.config["API_TIMEOUT"],
    )
    anime_service = AnimeService(primary=primary, fallback=fallback)
    supabase = SupabaseService(
        app.config["SUPABASE_URL"],
        app.config["SUPABASE_ANON_KEY"],
        app.config["SUPABASE_SERVICE_ROLE_KEY"],
        app.config["API_TIMEOUT"],
    )
    extras = AniListExtras(app.config["ANILIST_GRAPHQL_URL"], app.config["API_TIMEOUT"])

    app.extensions["anime_service"] = anime_service
    app.extensions["supabase_service"] = supabase
    app.extensions["anilist_extras"] = extras

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def bearer_token():
        value = request.headers.get("Authorization", "")
        if value.lower().startswith("bearer "):
            return value[7:].strip()
        return ""

    def require_user(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = bearer_token()
            user = None
            if token:
                try:
                    user = supabase.verify_user(token)
                except Exception:
                    app.logger.exception("Token verification failed")
            if not user:
                return jsonify({"error": "Sign in to use your AnimeX library."}), 401
            g.user = user
            g.token = token
            return fn(*args, **kwargs)
        return wrapper

    def server_error(message, log_message):
        app.logger.exception(log_message)
        return jsonify({"error": message}), 502

    # Injected into every template so each page doesn't repeat these args.
    @app.context_processor
    def inject_globals():
        return {
            "app_name": app.config["APP_NAME"],
            "supabase_url": app.config["SUPABASE_URL"],
            "supabase_anon_key": app.config["SUPABASE_ANON_KEY"],
        }

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    # JSON errors for the API, normal pages untouched
    @app.errorhandler(404)
    def not_found(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found."}), 404
        return err

    @app.errorhandler(405)
    def method_not_allowed(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Method not allowed."}), 405
        return err

    @app.errorhandler(500)
    def internal_error(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Something went wrong on our side."}), 500
        return err

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/login")
    def login_page():
        return render_template("auth.html")

    @app.get("/library")
    def library_page():
        return render_template("library.html")

    @app.get("/anime/<int:anime_id>")
    def anime_page(anime_id):
        return render_template("detail.html", anime_id=anime_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @app.get("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "app": app.config["APP_NAME"],
            "metadata_provider": "AniList",
            "supabase_configured": supabase.configured,
            "jikan_compatible_fallback_configured": bool(app.config.get("JIKAN_COMPATIBLE_BASE_URL")),
        })

    @app.get("/api/anime/<collection>")
    def collection(collection):
        if collection not in COLLECTIONS:
            return jsonify({"error": "Unknown anime collection."}), 404
        try:
            genre = (request.args.get("genre") or "").strip()
            data = anime_service.collection(collection, page=page_arg(), genre=genre or None)
            return cached_json(data)
        except Exception:
            return server_error("Anime data is temporarily unavailable.", "Anime collection failed")

    @app.get("/api/anime/search")
    def search():
        term = (request.args.get("q") or "").strip()
        if not term:
            return jsonify({"error": "Enter an anime title to search."}), 400
        if len(term) > MAX_SEARCH_LENGTH:
            return jsonify({"error": "Search query is too long."}), 400
        try:
            return jsonify(anime_service.search(term, page=page_arg()))
        except Exception:
            return server_error("Search is temporarily unavailable.", "Anime search failed")

    @app.get("/api/anime/details/<int:anime_id>")
    def anime_detail(anime_id):
        try:
            result = anime_service.detail(anime_id)
            if not result:
                return jsonify({"error": "Anime not found."}), 404
            return cached_json(result, seconds=600)
        except Exception:
            return server_error("Anime details are temporarily unavailable.", "Anime detail failed")

    @app.get("/api/anime/<int:anime_id>/airing")
    def anime_airing(anime_id):
        try:
            return cached_json(extras.airing(anime_id), seconds=120)
        except Exception:
            return server_error("Airing schedule is unavailable.", "Airing schedule failed")

    @app.get("/api/seasonal")
    def seasonal():
        year = request.args.get("year", type=int)
        season = (request.args.get("season") or "").upper() or None
        if season and season not in SEASONS:
            return jsonify({"error": "Invalid season."}), 400
        if year is not None and not 1940 <= year <= 2100:
            return jsonify({"error": "Invalid year."}), 400
        try:
            raw = extras.seasonal(year=year, season=season, page=page_arg())
            return cached_json({"results": [normalize_anilist_media(x) for x in raw]})
        except Exception:
            return server_error("Seasonal anime is unavailable.", "Seasonal anime failed")

    @app.get("/api/genres")
    def genres():
        return cached_json({"genres": GENRES}, seconds=86400)

    @app.get("/api/anime/<int:anime_id>/downloads")
    def approved_downloads(anime_id):
        try:
            return jsonify({"downloads": supabase.approved_downloads(anime_id)})
        except Exception:
            app.logger.exception("Approved download lookup failed")
            return jsonify({
                "downloads": [],
                "note": "No approved offline assets are currently configured.",
            })

    # ------------------------------------------------------------------
    # Authenticated API
    # ------------------------------------------------------------------
    @app.get("/api/me")
    @require_user
    def me():
        return jsonify({"id": str(g.user.id), "email": g.user.email})

    @app.route("/api/me/library", methods=["GET", "POST"])
    @require_user
    def my_library():
        try:
            if request.method == "GET":
                return jsonify({"items": supabase.list_library(g.token)})

            data = request.get_json(silent=True) or {}

            anime_id = data.get("anime_id")
            if not is_valid_int(anime_id, minimum=1):
                return jsonify({"error": "A valid anime_id is required."}), 400

            status = data.get("status", "plan_to_watch")
            if status not in WATCH_STATUSES:
                return jsonify({"error": "Invalid watch status."}), 400

            progress = data.get("progress", 0)
            if not is_valid_int(progress, minimum=0, maximum=10000):
                return jsonify({"error": "Progress must be a non-negative episode number."}), 400

            payload = {
                "user_id": str(g.user.id),
                "anime_id": anime_id,
                "title": str(data.get("title") or "Untitled")[:250],
                "image": str(data.get("image") or "")[:2000],
                "status": status,
                "progress": progress,
                "is_favorite": bool(data.get("is_favorite", False)),
            }
            result = supabase.save_library_item(g.token, payload)
            return jsonify({"item": result[0] if isinstance(result, list) and result else payload}), 201
        except Exception:
            return server_error("Could not complete the library request.", "Library operation failed")

    @app.delete("/api/me/library/<int:anime_id>")
    @require_user
    def delete_library_item(anime_id):
        try:
            supabase.delete_library_item(g.token, anime_id)
            return jsonify({"status": "deleted"})
        except Exception:
            return server_error("Could not remove that item.", "Library delete failed")

    @app.get("/api/me/recent")
    @require_user
    def my_recent():
        try:
            return jsonify({"items": supabase.list_recent(g.token)})
        except Exception:
            return server_error("Could not load recent items.", "Recent list failed")

    @app.post("/api/me/recent")
    @require_user
    def add_recent():
        data = request.get_json(silent=True) or {}
        anime_id = data.get("anime_id")
        if not is_valid_int(anime_id, minimum=1):
            return jsonify({"error": "A valid anime_id is required."}), 400
        try:
            supabase.add_recent(g.token, {
                "user_id": str(g.user.id),
                "anime_id": anime_id,
                "title": str(data.get("title") or "Untitled")[:250],
                "image": str(data.get("image") or "")[:2000],
            })
            return jsonify({"status": "saved"}), 201
        except Exception:
            return server_error("Could not save recent item.", "Recent item save failed")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"])
