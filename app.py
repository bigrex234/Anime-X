"""AnimeX Flask API — secure, serverless-friendly application entry point."""
from functools import wraps
from urllib.parse import urlparse

from flask import Flask, g, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from services.anilist_extras import AniListExtras
from services.anime_service import AnimeService
from services.normalizer import normalize_anilist_media
from services.providers.anilist import AniListProvider
from services.providers.jikan_compatible import JikanCompatibleProvider
from services.supabase_service import SupabaseError, SupabaseService

COLLECTIONS = {"trending", "popular", "top-rated", "upcoming"}
SEASONS = {"WINTER", "SPRING", "SUMMER", "FALL"}
WATCH_STATUSES = {"watching", "completed", "on_hold", "dropped", "plan_to_watch"}
GENRES = [
    "Action", "Adventure", "Comedy", "Drama", "Fantasy", "Horror",
    "Mystery", "Romance", "Sci-Fi", "Slice of Life", "Sports", "Supernatural",
]
MAX_PAGE = 20
MAX_SEARCH_LENGTH = 100
MAX_PROGRESS = 10000


def is_valid_int(value, minimum=0, maximum=None):
    """Reject bools (bool subclasses int) and values outside safe bounds."""
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        return False
    return maximum is None or value <= maximum


def page_arg():
    raw = request.args.get("page", default="1")
    try:
        page = int(raw)
    except (TypeError, ValueError):
        page = 1
    return max(1, min(page, MAX_PAGE))


def cached_json(payload, seconds=300, status=200):
    """Cache only explicitly public, non-user-specific metadata responses."""
    response = jsonify(payload)
    response.status_code = status
    response.headers["Cache-Control"] = (
        f"public, max-age=60, s-maxage={seconds}, stale-while-revalidate={seconds * 2}"
    )
    return response


def clean_image_url(value):
    """Accept only ordinary HTTP(S) image URLs; never fetch these server-side."""
    if value in (None, ""):
        return ""
    if not isinstance(value, str) or len(value) > 2000:
        raise ValueError("Image URL is invalid.")
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"https", "http"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Image URL must be a valid HTTP or HTTPS URL.")
    return value.strip()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    app.json.sort_keys = False

    # Configure a shared Redis/Upstash URL in production for cross-instance limits.
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=[app.config.get("RATELIMIT_DEFAULT", "300 per hour")],
        storage_uri=app.config.get("RATELIMIT_STORAGE_URI", "memory://"),
        strategy="fixed-window",
        headers_enabled=True,
    )
    app.extensions["rate_limiter"] = limiter

    primary = AniListProvider(app.config["ANILIST_GRAPHQL_URL"], app.config["API_TIMEOUT"])
    fallback = JikanCompatibleProvider(
        app.config.get("JIKAN_COMPATIBLE_BASE_URL", ""), app.config["API_TIMEOUT"]
    )
    anime_service = AnimeService(primary=primary, fallback=fallback)
    supabase = SupabaseService(
        app.config.get("SUPABASE_URL", ""),
        app.config.get("SUPABASE_ANON_KEY", ""),
        app.config.get("SUPABASE_SERVICE_ROLE_KEY", ""),
        app.config["API_TIMEOUT"],
    )
    extras = AniListExtras(app.config["ANILIST_GRAPHQL_URL"], app.config["API_TIMEOUT"])
    app.extensions.update({
        "anime_service": anime_service,
        "supabase_service": supabase,
        "anilist_extras": extras,
    })

    def bearer_token():
        value = request.headers.get("Authorization", "")
        scheme, _, token = value.partition(" ")
        return token.strip() if scheme.lower() == "bearer" else ""

    def require_user(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = bearer_token()
            if not token:
                return jsonify({"error": "Sign in to use your AnimeX account."}), 401
            try:
                user = supabase.verify_user(token)
            except SupabaseError as exc:
                return jsonify({"error": str(exc)}), exc.status_code
            if not user:
                return jsonify({"error": "Your session is invalid or expired. Please sign in again."}), 401
            g.user = user
            g.token = token
            return fn(*args, **kwargs)
        return wrapper

    def upstream_error(public_message, log_message):
        app.logger.exception(log_message)
        return jsonify({"error": public_message}), 502

    @app.context_processor
    def inject_globals():
        return {
            "app_name": app.config["APP_NAME"],
            "supabase_url": app.config.get("SUPABASE_URL", ""),
            "supabase_anon_key": app.config.get("SUPABASE_ANON_KEY", ""),
        }

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if request.path.startswith("/api/"):
            # Preserve explicit public cache policy set by cached_json().
            if "Cache-Control" not in response.headers:
                response.headers["Cache-Control"] = "no-store"
        if request.is_secure or request.headers.get("X-Forwarded-Proto", "").lower() == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Endpoint not found."}), 404
        return error

    @app.errorhandler(405)
    def method_not_allowed(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Method not allowed."}), 405
        return error

    @app.errorhandler(413)
    def request_too_large(error):
        return jsonify({"error": "Request body is too large."}), 413

    @app.errorhandler(429)
    def too_many_requests(error):
        return jsonify({"error": "You're moving too fast. Please try again shortly."}), 429

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.exception("Unhandled AnimeX server error")
        if request.path.startswith("/api/"):
            return jsonify({"error": "Something went wrong on our side."}), 500
        return error

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
    # Public API — only public metadata endpoints receive shared caching.
    # ------------------------------------------------------------------
    @app.get("/api/health")
    @limiter.limit("30 per minute")
    def health():
        return jsonify({
            "status": "ok",
            "app": app.config["APP_NAME"],
            "version": "2.0.0",
            "metadata_provider": "AniList",
            "fallback_configured": bool(app.config.get("JIKAN_COMPATIBLE_BASE_URL")),
            "supabase_configured": supabase.configured,
        })

    @app.get("/api/anime/<collection>")
    @limiter.limit("60 per minute")
    def collection(collection):
        if collection not in COLLECTIONS:
            return jsonify({"error": "Unknown anime collection."}), 404
        genre = (request.args.get("genre") or "").strip()
        if genre and genre not in GENRES:
            return jsonify({"error": "Unknown genre filter."}), 400
        try:
            return cached_json(anime_service.collection(collection, page=page_arg(), genre=genre or None))
        except Exception:
            return upstream_error("Anime data is temporarily unavailable.", "Anime collection failed")

    @app.get("/api/anime/search")
    @limiter.limit("30 per minute")
    def search():
        term = (request.args.get("q") or "").strip()
        if not term:
            return jsonify({"error": "Enter an anime title to search."}), 400
        if len(term) > MAX_SEARCH_LENGTH:
            return jsonify({"error": "Search query is too long."}), 400
        try:
            return cached_json(anime_service.search(term, page=page_arg()), seconds=90)
        except Exception:
            return upstream_error("Search is temporarily unavailable.", "Anime search failed")

    @app.get("/api/anime/details/<int:anime_id>")
    @limiter.limit("90 per minute")
    def anime_detail(anime_id):
        try:
            result = anime_service.detail(anime_id)
            if not result:
                return jsonify({"error": "Anime not found."}), 404
            return cached_json(result, seconds=600)
        except Exception:
            return upstream_error("Anime details are temporarily unavailable.", "Anime detail failed")

    @app.get("/api/anime/<int:anime_id>/airing")
    @limiter.limit("60 per minute")
    def anime_airing(anime_id):
        try:
            return cached_json(extras.airing(anime_id), seconds=120)
        except Exception:
            return upstream_error("Airing schedule is unavailable.", "Airing schedule failed")

    @app.get("/api/seasonal")
    @limiter.limit("60 per minute")
    def seasonal():
        year = request.args.get("year", type=int)
        season = (request.args.get("season") or "").upper() or None
        if season and season not in SEASONS:
            return jsonify({"error": "Invalid season."}), 400
        if year is not None and not 1940 <= year <= 2100:
            return jsonify({"error": "Invalid year."}), 400
        try:
            raw = extras.seasonal(year=year, season=season, page=page_arg())
            return cached_json({"results": [normalize_anilist_media(x) for x in raw]}, seconds=300)
        except Exception:
            return upstream_error("Seasonal anime is unavailable.", "Seasonal anime failed")

    @app.get("/api/genres")
    @limiter.limit("60 per minute")
    def genres():
        return cached_json({"genres": GENRES}, seconds=86400)

    @app.get("/api/anime/<int:anime_id>/downloads")
    @limiter.limit("30 per minute")
    def approved_downloads(anime_id):
        try:
            return jsonify({"downloads": supabase.approved_downloads(anime_id)})
        except SupabaseError:
            app.logger.exception("Approved download lookup failed")
            return jsonify({"downloads": [], "note": "Approved offline assets are temporarily unavailable."}), 503

    # ------------------------------------------------------------------
    # Authenticated API — never shared-cache user data.
    # ------------------------------------------------------------------
    @app.get("/api/me")
    @limiter.limit("120 per minute")
    @require_user
    def me():
        return jsonify({"id": str(g.user.id), "email": g.user.email})

    @app.route("/api/me/library", methods=["GET", "POST"])
    @limiter.limit("120 per minute")
    @require_user
    def my_library():
        try:
            if request.method == "GET":
                return jsonify({"items": supabase.list_library(g.token)})
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return jsonify({"error": "A JSON object is required."}), 400
            anime_id = data.get("anime_id")
            if not is_valid_int(anime_id, minimum=1):
                return jsonify({"error": "A valid anime_id is required."}), 400
            status = data.get("status", "plan_to_watch")
            if not isinstance(status, str) or status not in WATCH_STATUSES:
                return jsonify({"error": "Invalid watch status."}), 400
            progress = data.get("progress", 0)
            if not is_valid_int(progress, minimum=0, maximum=MAX_PROGRESS):
                return jsonify({"error": "Progress must be a non-negative episode number."}), 400
            favorite = data.get("is_favorite", False)
            if not isinstance(favorite, bool):
                return jsonify({"error": "is_favorite must be true or false."}), 400
            title = data.get("title", "Untitled")
            if not isinstance(title, str) or not title.strip():
                title = "Untitled"
            try:
                image_url = clean_image_url(data.get("image", ""))
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
            payload = {
                "user_id": str(g.user.id), "anime_id": anime_id,
                "title": title.strip()[:250], "image": image_url,
                "status": status, "progress": progress, "is_favorite": favorite,
            }
            result = supabase.save_library_item(g.token, payload)
            saved = result[0] if isinstance(result, list) and result else payload
            return jsonify({"item": saved}), 201
        except SupabaseError as exc:
            return jsonify({"error": str(exc)}), exc.status_code
        except Exception:
            return upstream_error("Could not complete the library request.", "Library operation failed")

    @app.delete("/api/me/library/<int:anime_id>")
    @limiter.limit("60 per minute")
    @require_user
    def delete_library_item(anime_id):
        try:
            supabase.delete_library_item(g.token, anime_id)
            return jsonify({"status": "deleted"})
        except SupabaseError as exc:
            return jsonify({"error": str(exc)}), exc.status_code
        except Exception:
            return upstream_error("Could not remove that item.", "Library delete failed")

    @app.get("/api/me/recent")
    @limiter.limit("120 per minute")
    @require_user
    def my_recent():
        try:
            return jsonify({"items": supabase.list_recent(g.token)})
        except SupabaseError as exc:
            return jsonify({"error": str(exc)}), exc.status_code
        except Exception:
            return upstream_error("Could not load recent items.", "Recent list failed")

    @app.post("/api/me/recent")
    @limiter.limit("60 per minute")
    @require_user
    def add_recent():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "A JSON object is required."}), 400
        anime_id = data.get("anime_id")
        if not is_valid_int(anime_id, minimum=1):
            return jsonify({"error": "A valid anime_id is required."}), 400
        title = data.get("title", "Untitled")
        if not isinstance(title, str) or not title.strip():
            title = "Untitled"
        try:
            image_url = clean_image_url(data.get("image", ""))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        try:
            supabase.add_recent(g.token, {
                "user_id": str(g.user.id), "anime_id": anime_id,
                "title": title.strip()[:250], "image": image_url,
            })
            return jsonify({"status": "saved"}), 201
        except SupabaseError as exc:
            return jsonify({"error": str(exc)}), exc.status_code
        except Exception:
            return upstream_error("Could not save recent item.", "Recent item save failed")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"])
