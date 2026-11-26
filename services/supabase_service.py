import requests
from types import SimpleNamespace

class SupabaseService:
    def __init__(self, url, anon_key, service_role_key="", timeout=15):
        self.url = (url or "").rstrip("/")
        self.anon_key = anon_key or ""
        self.service_role_key = service_role_key or ""
        self.timeout = timeout
        self._auth_client = None

    @property
    def configured(self):
        return bool(self.url and self.anon_key)

    def _client(self):
        if not self.configured:
            raise RuntimeError("Supabase is not configured.")
        if self._auth_client is None:
            self._auth_client = create_client(self.url, self.anon_key)
        return self._auth_client

    def verify_user(self, access_token):
        if not access_token:
            return None
        try:
            response = self._client().auth.get_user(access_token)
            return response.user
        except Exception:
            return None

    def request(self, method, path, access_token=None, params=None, body=None, prefer=None):
        if not self.configured:
            raise RuntimeError("Supabase is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY.")
        token = access_token or self.anon_key
        headers = {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        response = requests.request(
            method,
            f"{self.url}/rest/v1/{path.lstrip('/')}",
            headers=headers,
            params=params,
            json=body,
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            try:
                detail = response.json().get("message") or response.json().get("hint")
            except Exception:
                detail = response.text[:300]
            raise RuntimeError(detail or f"Supabase request failed ({response.status_code}).")
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def list_library(self, user_token):
        return self.request(
            "GET", "anime_library",
            access_token=user_token,
            params={"select": "*", "order": "updated_at.desc"},
        ) or []

    def save_library_item(self, user_token, payload):
        return self.request(
            "POST", "anime_library",
            access_token=user_token,
            params={"on_conflict": "user_id,anime_id"},
            body=payload,
            prefer="resolution=merge-duplicates,return=representation",
        )

    def delete_library_item(self, user_token, anime_id):
        return self.request(
            "DELETE", "anime_library",
            access_token=user_token,
            params={"anime_id": f"eq.{anime_id}"},
            prefer="return=minimal",
        )

    def list_recent(self, user_token):
        return self.request(
            "GET", "recently_viewed",
            access_token=user_token,
            params={"select": "*", "order": "viewed_at.desc", "limit": "30"},
        ) or []

    def add_recent(self, user_token, payload):
        return self.request(
            "POST", "recently_viewed",
            access_token=user_token,
            params={"on_conflict": "user_id,anime_id"},
            body=payload,
            prefer="resolution=merge-duplicates,return=minimal",
        )

    def approved_downloads(self, anime_id):
        return self.request(
            "GET", "downloadable_assets",
            params={
                "select": "id,title,description,source_url,file_name,mime_type,rights_note",
                "anime_id": f"eq.{anime_id}",
                "is_active": "eq.true",
            },
        ) or []
