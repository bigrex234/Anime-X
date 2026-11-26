"""Small Supabase Auth + PostgREST client using the user's JWT and RLS."""
from urllib.parse import urlparse
import requests


class SupabaseError(RuntimeError):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code


class SupabaseService:
    def __init__(self, url, anon_key, service_role_key="", timeout=12):
        self.url = (url or "").rstrip("/")
        self.anon_key = anon_key or ""
        # Deliberately never use the service-role key for user-facing operations.
        self.timeout = (min(3, timeout), timeout)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "AnimeX/2.0"})

    @property
    def configured(self):
        return bool(self.url and self.anon_key)

    def _ensure_configured(self):
        if not self.configured:
            raise SupabaseError("Supabase is not configured.", 503)
        parsed = urlparse(self.url)
        if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
            raise SupabaseError("Supabase URL must use HTTPS.", 503)

    def verify_user(self, access_token):
        """Return authenticated user; invalid/expired tokens return None.

        Network and upstream failures raise SupabaseError so they are not
        incorrectly reported to clients as an ordinary bad password/token.
        """
        if not access_token:
            return None
        self._ensure_configured()
        try:
            response = self.session.get(
                f"{self.url}/auth/v1/user",
                headers={"apikey": self.anon_key, "Authorization": f"Bearer {access_token}"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise SupabaseError("Authentication service is temporarily unavailable.", 503) from exc
        if response.status_code in (400, 401, 403):
            return None
        if response.status_code >= 500:
            raise SupabaseError("Authentication service is temporarily unavailable.", 503)
        if response.status_code >= 400:
            raise SupabaseError("Could not verify the session.", 502)
        try:
            user = response.json()
        except ValueError as exc:
            raise SupabaseError("Authentication service returned an invalid response.", 502) from exc
        if not user.get("id"):
            return None
        return type("SupabaseUser", (), {"id": user["id"], "email": user.get("email")})()

    def request(self, method, path, access_token=None, params=None, body=None, prefer=None):
        self._ensure_configured()
        token = access_token or self.anon_key
        headers = {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        try:
            response = self.session.request(
                method, f"{self.url}/rest/v1/{path.lstrip('/')}",
                headers=headers, params=params, json=body, timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise SupabaseError("Database request timed out.", 504) from exc
        except requests.RequestException as exc:
            raise SupabaseError("Database service is temporarily unavailable.", 503) from exc
        if response.status_code in (401, 403):
            raise SupabaseError("Your session is no longer valid. Please sign in again.", 401)
        if response.status_code >= 500:
            raise SupabaseError("Database service is temporarily unavailable.", 503)
        if response.status_code >= 400:
            try:
                payload = response.json()
                code = payload.get("code", "")
                # Do not return raw SQL, schema, or provider details to the browser.
                message = "The database rejected this request. Check the AnimeX database schema and permissions."
                if code == "23505":
                    message = "That anime is already in your library."
            except (ValueError, AttributeError):
                message = "The database rejected this request."
            raise SupabaseError(message, 400 if response.status_code < 500 else 503)
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise SupabaseError("Database service returned an invalid response.", 502) from exc

    def list_library(self, user_token):
        return self.request("GET", "anime_library", access_token=user_token,
                            params={"select": "*", "order": "updated_at.desc", "limit": "500"}) or []

    def save_library_item(self, user_token, payload):
        return self.request("POST", "anime_library", access_token=user_token,
                            params={"on_conflict": "user_id,anime_id"}, body=payload,
                            prefer="resolution=merge-duplicates,return=representation")

    def delete_library_item(self, user_token, anime_id):
        return self.request("DELETE", "anime_library", access_token=user_token,
                            params={"anime_id": f"eq.{anime_id}"}, prefer="return=minimal")

    def list_recent(self, user_token):
        return self.request("GET", "recently_viewed", access_token=user_token,
                            params={"select": "*", "order": "viewed_at.desc", "limit": "30"}) or []

    def add_recent(self, user_token, payload):
        return self.request("POST", "recently_viewed", access_token=user_token,
                            params={"on_conflict": "user_id,anime_id"}, body=payload,
                            prefer="resolution=merge-duplicates,return=minimal")

    def approved_downloads(self, anime_id):
        return self.request("GET", "downloadable_assets", params={
            "select": "id,title,description,source_url,file_name,mime_type,rights_note",
            "anime_id": f"eq.{anime_id}", "is_active": "eq.true",
        }) or []
