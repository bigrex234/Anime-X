from functools import wraps
from flask import Flask, jsonify, render_template, request, redirect
from config import Config
from services.anime_service import AnimeService
from services.providers.anilist import AniListProvider
from services.providers.jikan_compatible import JikanCompatibleProvider
from services.supabase_service import SupabaseService
from services.anilist_extras import AniListExtras

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

    def bearer_token():
        value = request.headers.get("Authorization", "")
        if value.lower().startswith("bearer "):
            return value[7:].strip()
        return ""

    def require_user(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = bearer_token()
            user = supabase.verify_user(token)
            if not user:
                return jsonify({"error": "Sign in to use your AnimeX library."}), 401
            request.animex_user = user
            request.animex_token = token
            return fn(*args, **kwargs)
        return wrapper

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            app_name=app.config["APP_NAME"],
            supabase_url=app.config["SUPABASE_URL"],
            supabase_anon_key=app.config["SUPABASE_ANON_KEY"],
        )

    @app.get("/login")
    def login_page():
        return render_template(
            "auth.html", app_name=app.config["APP_NAME"],
            supabase_url=app.config["SUPABASE_URL"],
            supabase_anon_key=app.config["SUPABASE_ANON_KEY"],
        )

    @app.get("/library")
    def library_page():
        return render_template(
            "library.html", app_name=app.config["APP_NAME"],
            supabase_url=app.config["SUPABASE_URL"],
            supabase_anon_key=app.config["SUPABASE_ANON_KEY"],
        )

    @app.get("/anime/<int:anime_id>")
    def anime_page(anime_id):
        return render_template(
            "detail.html", app_name=app.config["APP_NAME"], anime_id=anime_id,
            supabase_url=app.config["SUPABASE_URL"],
            supabase_anon_key=app.config["SUPABASE_ANON_KEY"],
        )

    @app.get("/api/health")
    def health():
        return jsonify({
            "status": "ok", "app": app.config["APP_NAME"],
            "metadata_provider": "AniList",
            "supabase_configured": supabase.configured,
            "jikan_compatible_fallback_configured": bool(app.config.get("JIKAN_COMPATIBLE_BASE_URL")),
        })

    @app.get("/api/anime/<collection>")
    def collection(collection):
        allowed = {"trending", "popular", "top-rated", "upcoming"}
        if collection not in allowed:
            return jsonify({"error": "Unknown anime collection."}), 404
        try:
            page = max(1, min(request.args.get("page", 1, type=int), 20))
            genre = (request.args.get("genre") or "").strip()
            return jsonify(anime_service.collection(collection, page=page, genre=genre or None))
        except Exception:
            app.logger.exception("Anime collection failed")
            return jsonify({"error": "Anime data is temporarily unavailable."}), 502

    @app.get("/api/anime/search")
    def search():
        term = (request.args.get("q") or "").strip()
        if not term:
            return jsonify({"error": "Enter an anime title to search."}), 400
        if len(term) > 100:
            return jsonify({"error": "Search query is too long."}), 400
        try:
            return jsonify(anime_service.search(term, page=max(1, min(request.args.get("page", 1, type=int), 20))))
        except Exception:
            app.logger.exception("Anime search failed")
            return jsonify({"error": "Search is temporarily unavailable."}), 502

    @app.get("/api/anime/details/<int:anime_id>")
    def anime_detail(anime_id):
        try:
            result = anime_service.detail(anime_id)
            if not result:
                return jsonify({"error": "Anime not found."}), 404
            return jsonify(result)
        except Exception:
            app.logger.exception("Anime detail failed")
            return jsonify({"error": "Anime details are temporarily unavailable."}), 502

    @app.get("/api/anime/<int:anime_id>/airing")
    def anime_airing(anime_id):
        try:
            return jsonify(extras.airing(anime_id))
        except Exception:
            app.logger.exception("Airing schedule failed")
            return jsonify({"error": "Airing schedule is unavailable."}), 502

    @app.get("/api/seasonal")
    def seasonal():
        try:
            year = request.args.get("year", type=int)
            season = (request.args.get("season") or "").upper() or None
            if season and season not in {"WINTER", "SPRING", "SUMMER", "FALL"}:
                return jsonify({"error": "Invalid season."}), 400
            from services.normalizer import normalize_anilist_media
            raw = extras.seasonal(year=year, season=season, page=max(1, min(request.args.get("page", 1, type=int), 20)))
            return jsonify({"results": [normalize_anilist_media(x) for x in raw]})
        except Exception:
            app.logger.exception("Seasonal anime failed")
            return jsonify({"error": "Seasonal anime is unavailable."}), 502

    @app.get("/api/genres")
    def genres():
        return jsonify({"genres": ["Action", "Adventure", "Comedy", "Drama", "Fantasy", "Horror", "Mystery", "Romance", "Sci-Fi", "Slice of Life", "Sports", "Supernatural"]})

    @app.get("/api/me")
    @require_user
    def me():
        return jsonify({"id": str(request.animex_user.id), "email": request.animex_user.email})

    @app.route("/api/me/library", methods=["GET", "POST"])
    @require_user
    def my_library():
        user_id = str(request.animex_user.id)
        try:
            if request.method == "GET":
                return jsonify({"items": supabase.list_library(request.animex_token)})
            data = request.get_json(silent=True) or {}
            anime_id = data.get("anime_id")
            if not isinstance(anime_id, int) or anime_id <= 0:
                return jsonify({"error": "A valid anime_id is required."}), 400
            status = data.get("status", "plan_to_watch")
            allowed = {"watching", "completed", "on_hold", "dropped", "plan_to_watch"}
            if status not in allowed:
                return jsonify({"error": "Invalid watch status."}), 400
            progress = data.get("progress", 0)
            if not isinstance(progress, int) or progress < 0 or progress > 10000:
                return jsonify({"error": "Progress must be a non-negative episode number."}), 400
            payload = {
                "user_id": user_id,
                "anime_id": anime_id,
                "title": str(data.get("title") or "Untitled")[:250],
                "image": str(data.get("image") or "")[:2000],
                "status": status,
                "progress": progress,
                "is_favorite": bool(data.get("is_favorite", False)),
            }
            result = supabase.save_library_item(request.animex_token, payload)
            return jsonify({"item": result[0] if isinstance(result, list) and result else payload}), 201
        except Exception as exc:
            app.logger.exception("Library operation failed")
            return jsonify({"error": str(exc)}), 502

    @app.delete("/api/me/library/<int:anime_id>")
    @require_user
    def delete_library_item(anime_id):
        try:
            supabase.delete_library_item(request.animex_token, anime_id)
            return jsonify({"status": "deleted"})
        except Exception as exc:
            app.logger.exception("Library delete failed")
            return jsonify({"error": str(exc)}), 502

    @app.get("/api/me/recent")
    @require_user
    def my_recent():
        try:
            return jsonify({"items": supabase.list_recent(request.animex_token)})
        except Exception as exc:
            app.logger.exception("Recent list failed")
            return jsonify({"error": str(exc)}), 502

    @app.post("/api/me/recent")
    @require_user
    def add_recent():
        data = request.get_json(silent=True) or {}
        anime_id = data.get("anime_id")
        if not isinstance(anime_id, int) or anime_id <= 0:
            return jsonify({"error": "A valid anime_id is required."}), 400
        try:
            supabase.add_recent(request.animex_token, {
                "user_id": str(request.animex_user.id),
                "anime_id": anime_id,
                "title": str(data.get("title") or "Untitled")[:250],
                "image": str(data.get("image") or "")[:2000],
            })
            return jsonify({"status": "saved"}), 201
        except Exception as exc:
            app.logger.exception("Recent item save failed")
            return jsonify({"error": str(exc)}), 502

    @app.get("/api/anime/<int:anime_id>/downloads")
    def approved_downloads(anime_id):
        try:
            return jsonify({"downloads": supabase.approved_downloads(anime_id)})
        except Exception:
            app.logger.exception("Approved download lookup failed")
            return jsonify({"downloads": [], "note": "No approved offline assets are currently configured."})

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"])
